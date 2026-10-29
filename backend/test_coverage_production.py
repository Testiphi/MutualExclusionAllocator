import json
from pathlib import Path
import unittest
from unittest.mock import patch
from backend import test_notification_production as fixtures
from backend.coverage_production import preflight,migrate
from backend.coverage import migrate as migrate_tables
from backend.production import make_app
from backend.score_production import backup,drill
from production_release_tools import check_score_compatibility

class CoverageProductionTests(unittest.TestCase):
    tearDown=fixtures.NotificationProductionTests.tearDown
    migrate_scores=fixtures.NotificationProductionTests.migrate_scores
    login=fixtures.NotificationProductionTests.login
    def setUp(self):fixtures.NotificationProductionTests.setUp(self)
    def test_explicit_idempotent_preserving_migration_and_coherent_restore(self):
        before=preflight(self.config);raw=self.store.path.read_bytes();self.assertEqual(before['coverage_schema'],0)
        from backend.app import create_app
        with self.assertRaisesRegex(ValueError,'正式库禁止'):create_app(self.path,coverage=True)
        self.assertEqual(raw,self.store.path.read_bytes())
        with self.assertRaises(ValueError):migrate(self.config,'0'*32)
        self.assertEqual(raw,self.store.path.read_bytes())
        with patch('backend.production.service_lock',side_effect=ValueError('active service')):
            with self.assertRaises(ValueError):migrate(self.config,self.version)
        result=migrate(self.config,self.version);self.assertTrue(result['existing_rows_preserved']);self.assertEqual(result['coverage_schema'],1);self.assertFalse(any(result['coverage_counts'].values()))
        self.assertEqual(before['counts'],result['counts']);self.assertEqual(before['score_version'],result['score_version'])
        raw=self.store.path.read_bytes();self.assertTrue(migrate(self.config,self.version)['already_migrated']);self.assertEqual(raw,self.store.path.read_bytes())
        restored=drill(self.config,backup(self.config));self.assertEqual(restored['coverage_schema'],1);self.assertFalse(restored['active_database_replaced']);self.assertTrue(make_app(self.config,'unused').state.coverage)
        restored_app=make_app({**self.config,'data_dir':restored['drill_directory']},'unused');self.assertTrue(restored_app.state.coverage)
    def test_rollback_on_failure_and_reject_incompatible_old_application(self):
        def fail(db):migrate_tables(db);raise ValueError('fixture failure')
        with patch('backend.coverage_production.migrate_tables',side_effect=fail):
            with self.assertRaises(ValueError):migrate(self.config,self.version)
        self.assertEqual(preflight(self.config)['coverage_schema'],0)
        migrate(self.config,self.version);target=self.path/'old-app';(target/'production').mkdir(parents=True);(target/'production/score-capability.json').write_text(json.dumps({'score_schema':1}),encoding='utf-8')
        with self.assertRaisesRegex(ValueError,'成绩表'):check_score_compatibility(target,{'files':{}},self.path)
