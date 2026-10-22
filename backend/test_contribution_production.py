import json
import sqlite3
from contextlib import closing
from pathlib import Path
from unittest.mock import patch
import unittest
from backend import test_score_production as fixtures
from backend.contribution_production import preflight, migrate, state
from backend.production import make_app
from backend.score_production import backup, drill, toggle
from backend.score_repository import Versions


class ContributionProductionTests(unittest.TestCase):
    setUp = fixtures.ScoreProductionTests.setUp
    tearDown = fixtures.ScoreProductionTests.tearDown
    migrate_scores = fixtures.ScoreProductionTests.migrate
    login = fixtures.ScoreProductionTests.login
    accepted = fixtures.ScoreProductionTests.accepted

    def test_readonly_preflight_and_migration_preserves_existing_rows(self):
        self.migrate_scores(); old = self.accepted(); toggle(self.config, True)
        raw = self.store.path.read_bytes()
        before = preflight(self.config)
        self.assertEqual(before['contribution_schema'], 0)
        self.assertEqual(self.store.path.read_bytes(), raw)
        with self.assertRaises(ValueError): migrate(self.config, '0'*32)
        self.assertEqual(self.store.path.read_bytes(), raw)
        result = migrate(self.config, before['score_version'])
        self.assertTrue(result['existing_rows_preserved']); self.assertTrue(result['score_writes'])
        self.assertEqual(result['historical_submissions_enrolled'], 0)
        self.assertTrue(Path(result['backup']).is_file())
        self.assertEqual(result['counts'], before['counts'])
        self.assertEqual(result['active_files'], before['active_files'])
        self.assertEqual(result['contribution_schema'], 1)
        self.assertFalse(any(result['contribution_counts'].values()))
        again = migrate(self.config, before['score_version'])
        self.assertTrue(again['already_migrated']); self.assertEqual(again['enabled_at'], result['enabled_at'])
        self.login()
        health = self.client.get('/api/health').json()
        self.assertEqual(health['contribution_schema'], 1)
        self.assertEqual(health['score_version'], before['score_version'])
        self.assertTrue(health['contributions'])
        self.assertFalse(self.client.get('/api/submissions/'+old['id']).json()['contribution_info']['eligible'])
        page = self.client.get('/leaderboard')
        self.assertEqual(page.status_code, 200); self.assertNotIn('独立本地验收环境', page.text)
        for asset in ('leaderboard.js','leaderboard.css'):
            self.assertEqual(self.client.get('/'+asset).status_code, 200)
        self.assertEqual(self.client.get('/api/contributions/leaderboard').json()['items'], [])

    def test_pre_migration_app_is_not_silently_migrated(self):
        self.migrate_scores(); self.login()
        self.assertFalse(self.client.get('/api/health').json()['contributions'])
        self.assertEqual(self.client.get('/leaderboard').status_code, 404)
        with self.store.connect() as db:
            self.assertEqual(state(db)['contribution_schema'], 0)

    def test_migration_rolls_back_ddl_on_preservation_failure(self):
        before = self.migrate_scores()
        from backend.score_production import existing_fingerprints
        calls = [0]
        def fingerprints(db, names):
            calls[0] += 1
            result = existing_fingerprints(db, names)
            return result if calls[0] == 1 else {'mismatch':'injected'}
        with patch('backend.score_production.existing_fingerprints', side_effect=fingerprints):
            with self.assertRaises(ValueError): migrate(self.config, before['version'])
        self.assertEqual(preflight(self.config)['contribution_schema'], 0)
        self.assertEqual(preflight(self.config)['score_version'], before['version'])

    def test_pending_batches_and_partial_tables_are_refused(self):
        version = self.migrate_scores()['version']
        with self.store.connect() as db:
            db.execute("INSERT INTO score_batches VALUES('pending','actor','request','hash','applying','{}')")
        with self.assertRaises(ValueError): migrate(self.config, version)
        with self.store.connect() as db:
            db.execute("DELETE FROM score_batches WHERE id='pending'")
            db.execute('CREATE TABLE contribution_events(id INTEGER)')
        with self.assertRaises(ValueError): preflight(self.config)
        with self.assertRaises(ValueError): make_app(self.config, 'unused')

    def test_production_scoring_coherent_backup_and_restoration(self):
        version = self.migrate_scores()['version']; migrate(self.config, version); toggle(self.config, True)
        self.login()
        # Enrol through the real production endpoint; existing owner is not permitted to self-review.
        payload = {'big':'古老斗技场','small':'偏僻小道','zone':'五区','tier':'高手',
                   'car':'恶魔','stars':1,'route':'','time':'30.123','notes':'test','video_url':'','unlisted':False}
        r = self.client.post('/api/submissions', json={'request_key':'production-fixture-0001','entries':[payload]})
        self.assertEqual(r.status_code, 200, r.text); sid = r.json()['ids'][0]
        self.assertEqual(self.client.post('/api/submissions/'+sid+'/submit',json={'revision':1}).status_code, 200)
        quality = {'completeness':3,'evidence':4,'value':2,'reason':'production fixture'}
        r = self.client.post('/api/admin/submissions/'+sid+'/review',json={'revision':2,'action':'ignore','reason':'test','quality':quality})
        self.assertEqual(r.status_code, 403)
        # Separate verified reviewer in the disposable database.
        with self.store.connect() as db:
            db.execute("INSERT INTO users SELECT 'reviewer','reviewer@example.test',password_hash,1,'admin',created_at FROM users WHERE id=?",(self.uid,))
            db.execute("UPDATE sessions SET user_id='reviewer' WHERE user_id=?",(self.uid,))
        self.client.headers['X-Account-ID'] = 'reviewer'
        detail = self.client.get('/api/submissions/'+sid).json()
        preview = self.client.post('/api/admin/submissions/'+sid+'/preview',json={'revision':detail['revision'],'entry':payload}).json()
        r = self.client.post('/api/admin/submissions/'+sid+'/review',json={'revision':detail['revision'],'action':'accept','entry':preview['candidate'],'basis':preview['basis'],'quality':quality})
        self.assertEqual(r.status_code, 200, r.text)
        self.client.close(); self.client = None; self.login()
        self.assertEqual(self.client.get('/api/contributions/leaderboard').json()['items'][0]['total'],9)
        r = self.client.post('/api/admin/score-versions',json={'request_key':'production-plan-0001','items':[{'id':sid,'revision':3}]})
        self.assertEqual(r.status_code,200,r.text); plan=r.json()
        self.client.post('/api/admin/score-versions/reauth',json={'password':'test-password-12345'})
        r = self.client.post('/api/admin/score-versions/'+plan['id']+'/execute',json={'digest':plan['digest'],'effects_confirmed':True,'items':[{'submission_id':sid,'confirmed':True}]})
        self.assertEqual(r.status_code,200,r.text)
        self.assertEqual(self.client.get('/api/contributions/leaderboard').json()['items'][0]['total'],19)
        saved = backup(self.config); restored = drill(self.config, saved)
        self.assertFalse(restored['active_database_replaced'])
        self.assertEqual(restored['contribution_schema'],1)
        self.assertEqual(restored['contribution_counts']['contributions'],1)
        with closing(sqlite3.connect(Path(restored['drill_directory'])/'accounts.sqlite3')) as db:
            self.assertEqual(db.execute('SELECT quality_points,bonus FROM contributions').fetchone(),(9,10))
        r = self.client.post('/api/admin/score-versions/'+plan['id']+'/rollback',json={'reason':'fixture rollback'})
        self.assertEqual(r.status_code,200,r.text)
        self.assertEqual(self.client.get('/api/contributions/leaderboard').json()['items'][0]['total'],9)


if __name__ == '__main__': unittest.main()
