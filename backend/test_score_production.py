import json
import secrets
import sqlite3
import tempfile
import unittest
from contextlib import closing,nullcontext
from pathlib import Path
from unittest.mock import patch
from fastapi.testclient import TestClient
from backend.app import HASHER,Store
from backend.production import initialize,make_app
from backend.score_production import source_snapshot,preflight,migrate,toggle,backup,drill,verify_backup

ROOT=Path(__file__).resolve().parents[1]
class ScoreProductionTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.path=Path(self.temp.name)/'data'
        self.config={'origin':'https://racepick.cn','data_dir':str(self.path),'owner_email':'owner@example.com','mail_daily_limit':100}
        initialize(self.config);self.store=Store(self.path);self.uid=secrets.token_hex(16)
        with self.store.connect() as db:
            db.execute('INSERT INTO users VALUES(?,?,?,?,?,?)',(self.uid,'owner@example.com',HASHER.hash('test-password-12345'),1,'admin',1))
            db.execute('INSERT INTO super_admins VALUES(1,?,1)',(self.uid,))
        _,self.hashes=source_snapshot(ROOT)
        self.lock=patch('backend.production.service_lock',lambda path:nullcontext());self.lock.start();self.client=None
    def tearDown(self):
        if self.client:self.client.close()
        self.lock.stop();self.temp.cleanup()
    def migrate(self):return migrate(self.config,ROOT,self.hashes['gauntlet_data.json'],self.hashes['cars.json'])
    def login(self):
        self.app=make_app(self.config,'not-used')
        self.client=TestClient(self.app,base_url='https://racepick.cn',client=('127.0.0.1',12345))
        self.client.headers.update({'Origin':'https://racepick.cn','X-Real-IP':'192.0.2.1','X-Forwarded-Proto':'https'})
        self.client.headers['X-CSRF-Token']=self.client.get('/api/auth/me').json()['csrf']
        result=self.client.post('/api/auth/login',json={'email':'owner@example.com','password':'test-password-12345'})
        self.assertEqual(result.status_code,200,result.text)
        self.client.headers.update({'X-CSRF-Token':result.json()['csrf'],'X-Account-ID':self.uid})
    def accepted(self):
        sid=secrets.token_hex(16);p={'big':'古老斗技场','small':'偏僻小道','zone':'五区','tier':'高手','car':'恶魔','stars':1,'route':'','time':'30.123','notes':'test','video_url':'','unlisted':False}
        with self.store.connect() as db:db.execute("INSERT INTO submissions(id,owner_id,batch_id,revision,status,payload,accepted_payload,baseline,created_at,updated_at) VALUES (?,?,?,2,'accepted',?,?,?,1,1)",(sid,self.uid,secrets.token_hex(16),json.dumps(p),json.dumps(p),'{}'))
        return {'id':sid,'revision':2}
    def test_preflight_is_readonly_migration_preserves_users_and_disabled(self):
        raw=(self.path/'accounts.sqlite3').read_bytes()
        result=preflight(self.config,ROOT);self.assertEqual(result['counts']['users'],1)
        self.assertEqual(raw,(self.path/'accounts.sqlite3').read_bytes());self.assertFalse((self.path/'score-state').exists())
        first=self.migrate();self.assertTrue(first['existing_rows_preserved']);self.assertFalse(first['write_enabled'])
        again=self.migrate();self.assertEqual(first['version'],again['version'])
        self.login();self.assertFalse(self.client.get('/api/health').json()['score_writes'])
        self.assertTrue(self.client.get('/api/auth/me').json()['score_versions'])
        self.assertNotIn('确认测试操作',self.client.get('/score-versions').text)
        pick=self.accepted();r=self.client.post('/api/admin/score-versions',json={'request_key':secrets.token_hex(16),'items':[pick]})
        self.assertEqual(r.status_code,403);self.assertEqual(self.client.get('/api/scores/snapshot').json()['version'],first['version'])
    def test_hash_mismatch_makes_no_score_directory(self):
        with self.assertRaises(ValueError):migrate(self.config,ROOT,'0'*64,self.hashes['cars.json'])
        self.assertFalse((self.path/'score-state').exists())
    def test_enable_publish_coherent_backup_drill_and_disable(self):
        self.migrate();toggle(self.config,True);self.login()
        r=self.client.post('/api/admin/score-versions',json={'request_key':secrets.token_hex(16),'items':[self.accepted()]});self.assertEqual(r.status_code,200,r.text);m=r.json()
        self.client.post('/api/admin/score-versions/reauth',json={'password':'test-password-12345'})
        r=self.client.post('/api/admin/score-versions/'+m['id']+'/execute',json={'digest':m['digest'],'effects_confirmed':True,'items':[{'submission_id':m['result']['items'][0]['submission_id'],'confirmed':True}]})
        self.assertEqual(r.status_code,200,r.text)
        snapshot=backup(self.config);info=verify_backup(snapshot);self.assertEqual(info['current'],m['target'])
        restored=drill(self.config,snapshot);self.assertFalse(restored['active_database_replaced']);self.assertEqual(restored['version'],m['target'])
        restored_config={**self.config,'data_dir':restored['drill_directory']};restored_app=make_app(restored_config,'unused')
        self.assertEqual(restored_app.state.score_versions.current()[0]['id'],m['target'])
        self.assertEqual(restored['counts']['users'],1)
        toggle(self.config,False)
        self.assertFalse(self.client.get('/api/health').json()['score_writes'])
        self.assertEqual(self.client.post('/api/admin/score-versions/'+m['id']+'/rollback',json={'reason':'disabled'}).status_code,403)
    def test_versioned_database_cannot_use_old_sqlite_restore(self):
        from backend.production import backup as legacy_backup,restore
        old=legacy_backup(self.config);self.migrate()
        with self.assertRaises(ValueError):restore(self.config,old)
    def test_missing_binding_never_falls_back_to_bundled_scores(self):
        self.migrate()
        with self.store.connect() as db:db.execute('UPDATE score_control SET binding=?',('wrong',))
        with self.assertRaises(ValueError):make_app(self.config,'unused')

    def test_revert_readonly_migration_preserves_accounts(self):
        from backend.score_production import revert_migration
        self.migrate()
        with self.store.connect() as db:before=[tuple(r) for r in db.execute('SELECT * FROM users')]
        result=revert_migration(self.config,ROOT);self.assertTrue(result['account_rows_preserved'])
        self.assertFalse((self.path/'score-state').exists());self.assertTrue(Path(result['retained_scores']).is_dir())
        with self.store.connect() as db:self.assertEqual(before,[tuple(r) for r in db.execute('SELECT * FROM users')])
        self.assertFalse(hasattr(make_app(self.config,'unused').state,'score_versions'))
    def test_revert_migration_refuses_enabled_state(self):
        from backend.score_production import revert_migration
        self.migrate();toggle(self.config,True)
        with self.assertRaises(ValueError):revert_migration(self.config,ROOT)
        self.assertTrue((self.path/'score-state').exists())

    def test_interrupted_migration_resumes_without_replacing_accounts(self):
        from backend.score_versions import ScoreWriter
        original=ScoreWriter.initialize_tables
        def crash(db,initial):
            original(db,initial)
            raise RuntimeError('simulated migration failure')
        with patch.object(ScoreWriter,'initialize_tables',side_effect=crash):
            with self.assertRaises(RuntimeError):self.migrate()
        with self.assertRaises(ValueError):make_app(self.config,'unused')
        with self.store.connect() as db:self.assertEqual(db.execute('SELECT count(*) FROM users').fetchone()[0],1)
        result=self.migrate();self.assertTrue(result['existing_rows_preserved']);self.assertFalse(result['write_enabled'])

if __name__=='__main__':unittest.main()
