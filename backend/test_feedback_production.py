import json
import sqlite3
from contextlib import closing
from pathlib import Path
from unittest.mock import patch
import unittest
from backend import test_score_production as fixtures
from backend.contribution_production import migrate as contribution_migrate
from backend.feedback_production import preflight, migrate
from backend.production import make_app
from backend.score_production import backup, drill, toggle


class FeedbackProductionTests(unittest.TestCase):
    tearDown = fixtures.ScoreProductionTests.tearDown
    migrate_scores = fixtures.ScoreProductionTests.migrate
    login = fixtures.ScoreProductionTests.login

    def setUp(self):
        fixtures.ScoreProductionTests.setUp(self)
        self.version = self.migrate_scores()['version']
        contribution_migrate(self.config, self.version)
        with self.store.connect() as db:
            db.execute('INSERT INTO contribution_preferences VALUES(?,?,0,1)', (self.uid, '原有昵称'))
            db.execute("INSERT INTO contributions(user_id,target_key,quality_points,quality_month) VALUES(?,'retained',9,'2026-10')", (self.uid,))

    def test_readonly_preflight_preservation_and_idempotent_migration(self):
        toggle(self.config, True)
        raw = self.store.path.read_bytes()
        before = preflight(self.config)
        self.assertEqual(before['feedback_schema'], 0)
        self.assertEqual(raw, self.store.path.read_bytes())
        with self.assertRaises(ValueError): migrate(self.config, '0'*32)
        self.assertEqual(raw, self.store.path.read_bytes())
        after = migrate(self.config, self.version)
        self.assertTrue(after['existing_rows_preserved']); self.assertEqual(after['test_feedback_imported'], 0)
        self.assertEqual(after['feedback_schema'], 1); self.assertFalse(any(after['feedback_counts'].values()))
        self.assertTrue(Path(after['backup']).is_file())
        for field in ('score_version','score_writes','counts','active_files','contribution_counts','enabled_at'):
            self.assertEqual(before[field], after[field], field)
        raw = self.store.path.read_bytes()
        again = migrate(self.config, self.version)
        self.assertTrue(again['already_migrated']); self.assertEqual(raw, self.store.path.read_bytes())
        with self.store.connect() as db:
            self.assertEqual(db.execute('SELECT nickname FROM contribution_preferences').fetchone()[0], '原有昵称')
            self.assertEqual(db.execute('SELECT quality_points FROM contributions').fetchone()[0], 9)

    def test_no_automatic_production_migration(self):
        self.login()
        self.assertFalse(self.client.get('/api/health').json()['feedback'])
        self.assertEqual(self.client.get('/feedback').status_code, 404)
        self.assertEqual(preflight(self.config)['feedback_schema'], 0)

    def test_partial_tables_and_unfinished_batches_block_migration(self):
        with self.store.connect() as db:
            db.execute("INSERT INTO score_batches VALUES('pending','actor','request','hash','applying','{}')")
        with self.assertRaises(ValueError): migrate(self.config, self.version)
        with self.store.connect() as db:
            db.execute("DELETE FROM score_batches WHERE id='pending'")
            db.execute('CREATE TABLE feedback_events(id INTEGER)')
        with self.assertRaises(ValueError): preflight(self.config)
        with self.assertRaises(ValueError): make_app(self.config, 'unused')

    def test_migration_rolls_back_when_existing_rows_drift(self):
        from backend.score_production import existing_fingerprints
        calls = [0]
        def injected(db, names):
            calls[0] += 1
            return existing_fingerprints(db, names) if calls[0] == 1 else {'changed':'test'}
        with patch('backend.score_production.existing_fingerprints', side_effect=injected):
            with self.assertRaises(ValueError): migrate(self.config, self.version)
        self.assertEqual(preflight(self.config)['feedback_schema'], 0)

    def test_production_http_feedback_and_coherent_restoration(self):
        migrate(self.config, self.version); self.login()
        health = self.client.get('/api/health').json()
        self.assertEqual(health['feedback_schema'], 1); self.assertTrue(health['feedback'])
        self.assertEqual(health['score_version'], self.version)
        for route in ('/feedback','/admin-feedback','/feedback.js','/ui.css'):
            self.assertEqual(self.client.get(route).status_code, 200, route)
        context = self.client.get('/api/feedback/context').json()
        self.assertNotEqual(context['app_version'], 'local-feedback-v1')
        body = {'request_key':'production-feedback-0001','category':'bug','title':'temporary fixture',
                'description':'Temporary private feedback','source_page':'/leaderboard'}
        result = self.client.post('/api/feedback', json=body)
        self.assertEqual(result.status_code, 200, result.text); tid = result.json()['id']
        self.assertEqual(self.client.post('/api/feedback', json=body).json(), result.json())
        result = self.client.post('/api/admin/feedback/'+tid+'/handle', json={
            'request_key':'production-feedback-reply','revision':1,'message':'Reviewed fixture', 'status':'resolved'})
        self.assertEqual(result.status_code, 200, result.text)
        detail = self.client.get('/api/feedback/'+tid).json()
        self.assertEqual(len(detail['events']), 2)
        saved = backup(self.config); restored = drill(self.config, saved)
        self.assertFalse(restored['active_database_replaced']); self.assertEqual(restored['feedback_schema'], 1)
        self.assertEqual(restored['feedback_counts']['feedback_tickets'], 1)
        with self.store.connect() as db, closing(sqlite3.connect(Path(restored['drill_directory'])/'accounts.sqlite3')) as copy:
            for table in ('feedback_schema','feedback_tickets','feedback_events','feedback_requests','contribution_preferences','contributions'):
                self.assertEqual([tuple(r) for r in db.execute('SELECT * FROM '+table)], copy.execute('SELECT * FROM '+table).fetchall(), table)
        restored_app = make_app({**self.config,'data_dir':restored['drill_directory']}, 'unused')
        self.assertTrue(restored_app.state.feedback)


if __name__ == '__main__': unittest.main()
