"""Disposable fixture databases only; no production host, service or credentials."""
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import secrets
import unittest
from unittest.mock import patch
from backend import test_notification_production as fixtures
from backend.coverage_production import migrate as migrate_coverage
from backend.global_score_production import preflight,migrate,state
from backend.production import make_app
from backend.score_production import backup,drill
from production_release_tools import check_score_compatibility

class GlobalScoreProductionTests(unittest.TestCase):
    tearDown=fixtures.NotificationProductionTests.tearDown
    migrate_scores=fixtures.NotificationProductionTests.migrate_scores
    login=fixtures.NotificationProductionTests.login
    def setUp(self):
        fixtures.NotificationProductionTests.setUp(self);migrate_coverage(self.config,self.version)
        self.source=Path(__file__).parents[1];self.dataset=json.loads((self.source/'global-data-manifest.json').read_text(encoding='utf-8'))['_meta']['dataset_version']
    def test_explicit_migration_readonly_preflight_no_reseed_and_complete_restore(self):
        before=self.store.path.read_bytes();self.assertEqual(preflight(self.config)['global_score_schema'],0);self.assertEqual(before,self.store.path.read_bytes())
        with self.assertRaises(ValueError):make_app(self.config,'unused')
        with self.assertRaises(ValueError):migrate(self.config,self.source,'0'*64,self.version)
        self.assertEqual(before,self.store.path.read_bytes())
        result=migrate(self.config,self.source,self.dataset,self.version);self.assertEqual(result['global_score_schema'],1);self.assertFalse(result['global_writes_enabled']);self.assertTrue(result['existing_rows_preserved'])
        before=self.store.path.read_bytes();self.assertTrue(migrate(self.config,self.source,self.dataset,self.version)['already_migrated']);self.assertEqual(before,self.store.path.read_bytes())
        app=make_app(self.config,'unused')
        with self.store.connect() as db:self.assertFalse(app.state.global_score_versions.enabled(db))
        with self.store.connect() as db:
            db.execute('INSERT INTO coverage_choices VALUES(?,?,?)',(self.uid,'a'*24,123));db.execute('INSERT INTO coverage_global_choices VALUES(?,?,?)',(self.uid,'b'*24,456))
            db.execute('INSERT INTO coverage_events(user_id,action,snapshot,created_at) VALUES(?,?,?,?)',(self.uid,'choose',json.dumps({'server':'global','map_id':'b'*24}),456))
        restored=drill(self.config,backup(self.config));self.assertEqual(restored['global_score_schema'],1);self.assertEqual(restored['global_score_version'],result['global_score_version']);self.assertFalse(restored['active_database_replaced']);self.assertEqual(restored['coverage_counts']['coverage_global_choices'],1)
        restored_app=make_app({**self.config,'data_dir':restored['drill_directory']},'unused');self.assertEqual(restored_app.state.global_score_versions.current(),app.state.global_score_versions.current())
        target=self.path/'old-global-app';(target/'production').mkdir(parents=True);(target/'production/score-capability.json').write_text('{"coverage_schema":2}',encoding='utf-8')
        with self.assertRaisesRegex(ValueError,'国际成绩'):check_score_compatibility(target,{'files':{}},self.path)
    def test_existing_row_drift_rolls_back_tables_and_retained_seed_can_resume(self):
        from backend.score_production import existing_fingerprints
        calls=[0]
        def drift(db,names):
            calls[0]+=1
            return existing_fingerprints(db,names) if calls[0]==1 else {'drift':'fixture'}
        with patch('backend.score_production.existing_fingerprints',side_effect=drift):
            with self.assertRaises(ValueError):migrate(self.config,self.source,self.dataset,self.version)
        self.assertEqual(preflight(self.config)['global_score_schema'],0)
        self.assertTrue((self.path/'global-score-state/global-scores.json').exists())
        self.assertEqual(migrate(self.config,self.source,self.dataset,self.version)['global_score_schema'],1)
    def test_applied_global_version_and_batch_backup_restore_without_touching_cn(self):
        migrate(self.config,self.source,self.dataset,self.version)
        from backend.score_production import toggle
        toggle(self.config,True)
        with self.store.connect() as db:db.execute('UPDATE global_score_control SET enabled=1')
        self.login();writer=self.app.state.global_score_versions
        _,raw=writer.current();data=json.loads(raw['gauntlet_data.global.json']);track=next(t for t in data['tracks'] if t['五区']['理论'])
        old=next(e for e in track['五区']['理论'] if not e.get('sc') and not e['cars'][0].get('oc'))
        payload={'server':'global','oc':False,'big':track['大地图'],'small':track['小地图'],'zone':'五区','tier':'理论','car':old['cars'][0]['name'],'stars':None,'route':'','time':str(round(old['time']-.001,3)),'notes':'fixture only','video_url':'','unlisted':False}
        sid=secrets.token_hex(16)
        with self.store.connect() as db:db.execute("INSERT INTO submissions(id,owner_id,batch_id,revision,status,payload,accepted_payload,baseline,created_at,updated_at) VALUES(?,?,?,2,'accepted',?,?,?,1,1)",(sid,self.uid,secrets.token_hex(16),json.dumps(payload),json.dumps(payload),'{}'))
        planned=self.client.post('/api/admin/score-versions?server=global',json={'request_key':secrets.token_hex(16),'items':[{'id':sid,'revision':2}]});self.assertEqual(planned.status_code,200,planned.text);m=planned.json()
        self.client.post('/api/admin/score-versions/reauth?server=global',json={'password':'test-password-12345'})
        applied=self.client.post('/api/admin/score-versions/'+m['id']+'/execute?server=global',json={'digest':m['digest'],'effects_confirmed':True,'items':[{'submission_id':sid,'confirmed':True}]});self.assertEqual(applied.status_code,200,applied.text)
        restored=drill(self.config,backup(self.config));self.assertEqual(restored['version'],self.version);self.assertEqual(restored['global_score_version'],m['target'])
        restored_app=make_app({**self.config,'data_dir':restored['drill_directory']},'unused');self.assertEqual(restored_app.state.global_score_versions.current(),writer.current())
        response=self.client.post('/api/admin/score-versions/'+m['id']+'/rollback?server=global',json={'reason':'fixture rollback'});self.assertEqual(response.status_code,200,response.text)
        self.assertEqual(writer.current()[1],raw);self.assertEqual(self.app.state.score_versions.current()[0]['id'],self.version)

if __name__=='__main__':unittest.main()
