"""New temporary production-shaped state only; Linux service lock mocked by fixture."""
from contextlib import closing
import json
from pathlib import Path
import secrets
import sqlite3
import unittest
from backend import test_score_production as fixtures
from backend.production import make_app
from backend.score_production import backup, drill, verify_backup
from backend.usage_production import initialize, preflight, prune
from production_release_tools import check_score_compatibility


class UsageProductionTests(unittest.TestCase):
    tearDown=fixtures.ScoreProductionTests.tearDown
    migrate=fixtures.ScoreProductionTests.migrate
    login=fixtures.ScoreProductionTests.login

    def setUp(self):
        fixtures.ScoreProductionTests.setUp(self)
        self.version=self.migrate()['version']

    def test_explicit_initialization_readonly_preflight_and_coherent_restore(self):
        raw=self.store.path.read_bytes();self.assertEqual(preflight(self.config)['usage_schema'],0)
        self.assertEqual(self.store.path.read_bytes(),raw)
        self.assertFalse(make_app(self.config,'unused').state.usage)
        with self.assertRaises(ValueError):initialize(self.config,'0'*32)
        self.assertFalse((self.path/'usage.sqlite3').exists())
        result=initialize(self.config,self.version)
        self.assertTrue(result['existing_accounts_preserved']);self.assertEqual(self.store.path.read_bytes(),raw)
        self.login();self.assertTrue(self.app.state.usage)
        self.assertTrue(self.client.get('/api/health').json()['usage'])
        body={'visitor_id':secrets.token_hex(16),'session_id':secrets.token_hex(16)}
        token=self.client.post('/api/usage/session',json=body).json()['token']
        self.client.headers['X-Usage-Token']=token
        self.assertEqual(self.client.post('/api/usage/events',json={'events':[{'id':secrets.token_hex(16),'kind':'active','page':'home','server':'global'}]}).status_code,200)
        saved=backup(self.config);manifest=verify_backup(saved)
        self.assertEqual(manifest['usage_schema'],1);self.assertIn('usage.sqlite3',manifest['files'])
        restored=drill(self.config,saved)
        self.assertEqual(restored['usage_schema'],1);self.assertFalse(restored['active_database_replaced'])
        restored_app=make_app({**self.config,'data_dir':restored['drill_directory']},'unused')
        self.assertTrue(restored_app.state.usage)
        with self.app.state.usage.connect() as original,restored_app.state.usage.connect() as copy:
            for table in ('usage_schema','usage_events','usage_daily','usage_people','usage_minutes'):
                self.assertEqual([tuple(r) for r in original.execute('SELECT * FROM '+table)],[tuple(r) for r in copy.execute('SELECT * FROM '+table)])
        before=(self.path/'usage.sqlite3').read_bytes();self.assertTrue(initialize(self.config,self.version)['already_initialized'])
        self.assertEqual((self.path/'usage.sqlite3').read_bytes(),before)

    def test_legacy_backup_and_downgrade_gate_and_prune_preview(self):
        old=backup(self.config);self.assertEqual(drill(self.config,old)['usage_schema'],0)
        initialize(self.config,self.version)
        raw=(self.path/'usage.sqlite3').read_bytes();result=prune(self.config)
        self.assertFalse(result['executed']);self.assertEqual((self.path/'usage.sqlite3').read_bytes(),raw)
        target=self.path/'old-app';(target/'production').mkdir(parents=True)
        (target/'production/score-capability.json').write_text(json.dumps({'score_schema':1}),encoding='utf-8')
        with self.assertRaisesRegex(ValueError,'统计库'):
            check_score_compatibility(target,{'files':{}},self.path)

    def test_unfinished_batches_and_partial_usage_database_stop_initialization(self):
        with self.store.connect() as db:db.execute("INSERT INTO score_batches VALUES('pending','actor','request','hash','applying','{}')")
        with self.assertRaises(ValueError):initialize(self.config,self.version)
        self.assertFalse((self.path/'usage.sqlite3').exists())
        with self.store.connect() as db:db.execute("DELETE FROM score_batches WHERE id='pending'")
        with closing(sqlite3.connect(self.path/'usage.sqlite3')) as db:db.execute('CREATE TABLE usage_schema(version INTEGER)')
        with self.assertRaises(ValueError):preflight(self.config)
        with self.assertRaises(ValueError):make_app(self.config,'unused')


if __name__=='__main__':unittest.main()
