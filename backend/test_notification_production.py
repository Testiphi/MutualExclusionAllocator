"""Temporary database rehearsal; Windows service lock is mocked by existing fixture."""
from contextlib import closing
import sqlite3
from pathlib import Path
import unittest
from unittest.mock import patch
from backend import test_feedback_production as fixtures
from backend.feedback_production import migrate as migrate_feedback
from backend.notification_production import preflight, migrate
from backend.score_production import backup, drill
from backend.production import make_app


class NotificationProductionTests(unittest.TestCase):
    tearDown = fixtures.FeedbackProductionTests.tearDown
    migrate_scores = fixtures.FeedbackProductionTests.migrate_scores
    login = fixtures.FeedbackProductionTests.login

    def setUp(self):
        fixtures.FeedbackProductionTests.setUp(self)
        migrate_feedback(self.config, self.version)

    def test_preflight_old_content_baseline_and_coherent_restore(self):
        self.login()
        r=self.client.post('/api/feedback',json={'request_key':'notification-fixture-01','category':'bug',
            'title':'Existing content','description':'Preserve original feedback','source_page':'/'})
        self.assertEqual(r.status_code,200,r.text)
        raw=self.store.path.read_bytes();self.assertEqual(preflight(self.config)['notification_schema'],0)
        self.assertEqual(self.store.path.read_bytes(),raw)
        with self.assertRaises(ValueError):migrate(self.config,'0'*32)
        self.assertEqual(self.store.path.read_bytes(),raw)
        result=migrate(self.config,self.version)
        self.assertTrue(result['existing_rows_preserved'])
        self.assertFalse(any(result['notification_counts'].values()))
        self.assertEqual(result['feedback_counts']['feedback_tickets'],1)
        self.client.close();self.login()
        self.assertTrue(self.client.get('/api/health').json()['notifications'])
        self.assertEqual(self.client.get('/api/notifications').json()['counts']['feedback_admin'],0)
        # A new event is stored and recovered together with the original database.
        r=self.client.post('/api/feedback',json={'request_key':'notification-fixture-02','category':'bug',
            'title':'New content','description':'Self notification is excluded','source_page':'/'})
        self.assertEqual(r.status_code,200,r.text)
        self.assertEqual(self.client.get('/api/notifications').json()['counts']['feedback_admin'],0)
        restored=drill(self.config,backup(self.config))
        self.assertFalse(restored['active_database_replaced'])
        self.assertEqual(restored['notification_counts']['notification_events'],1)
        with self.store.connect() as db, closing(sqlite3.connect(Path(restored['drill_directory'])/'accounts.sqlite3')) as copy:
            for table in ('notification_schema','notification_events','notification_reads','feedback_tickets','users'):
                self.assertEqual([tuple(r) for r in db.execute('SELECT * FROM '+table)],copy.execute('SELECT * FROM '+table).fetchall())
        self.assertTrue(make_app({**self.config,'data_dir':restored['drill_directory']},'unused').state.notifications)
        raw=self.store.path.read_bytes();self.assertTrue(migrate(self.config,self.version)['already_migrated'])
        self.assertEqual(raw,self.store.path.read_bytes())

    def test_no_startup_migration_partial_state_and_transaction_rollback(self):
        self.assertFalse(make_app(self.config,'unused').state.notifications)
        from backend.score_production import existing_fingerprints
        calls=[0]
        def drift(db,names):
            calls[0]+=1
            return existing_fingerprints(db,names) if calls[0]==1 else {'unexpected':'drift'}
        with patch('backend.score_production.existing_fingerprints',side_effect=drift):
            with self.assertRaises(ValueError):migrate(self.config,self.version)
        self.assertEqual(preflight(self.config)['notification_schema'],0)
        with self.store.connect() as db:db.execute('CREATE TABLE notification_events(id INTEGER)')
        with self.assertRaises(ValueError):preflight(self.config)
        with self.assertRaises(ValueError):make_app(self.config,'unused')


if __name__=='__main__':unittest.main()
