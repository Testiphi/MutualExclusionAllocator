import json
import secrets
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from fastapi.testclient import TestClient
from backend.app import create_app, Store
from backend.roles import set_role
from backend.score_repository import provision, validate_lab
from backend import test_accounts as accounts
PASSWORD = accounts.PASSWORD
from backend.contributions import migrate, month, ranked

Q = {'completeness': 3, 'evidence': 4, 'value': 2, 'reason': '独立证据完整，可核验的新样本'}


class ContributionTests(unittest.TestCase):
    new_client = accounts.AccountsTests.new_client
    post = accounts.AccountsTests.post
    token = accounts.AccountsTests.token
    signup = accounts.AccountsTests.signup

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); seed = Path(self.tmp.name)
        data = {'_version': 1, 'tracks': [{'大地图': '测试地图', '小地图': '测试赛道',
            '五区': {'理论': [], '高手': [{'cars': [{'name': '恶魔', 'stars': 6}], 'time': 25}], '普通': [{'cars': [{'name': '恶魔', 'stars': 6}]}], '自动': []},
            '四区': {'理论': [], '高手': [], '普通': [], '自动': []}}]}
        (seed/'gauntlet_data.json').write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')
        shutil.copyfile(Path(__file__).parents[1]/'cars.json', seed/'cars.json')
        self.lab = provision(seed); self.path = self.lab/'accounts'
        self.app = create_app(self.path, score_version_lab=self.lab, contributions=True)
        self.client = self.new_client(); self.owner = self.signup('owner@example.com')
        set_role(self.path, 'owner@example.com', 'superadmin'); self.login(self.client, 'owner@example.com')
        self.player = self.new_client(); self.player_user = self.signup('player@example.com', self.player)
        self.writer = self.app.state.score_versions
        r = self.client.post('/api/admin/score-versions/reauth', json={'password': PASSWORD}); self.assertEqual(r.status_code, 200)

    def tearDown(self):
        self.client.close(); self.player.close(); validate_lab(self.lab); shutil.rmtree(self.lab); self.tmp.cleanup()

    def login(self, client, email):
        client.cookies.clear()
        client.headers['X-CSRF-Token'] = client.get('/api/auth/me').json()['csrf']
        r = self.post('login', {'email': email, 'password': PASSWORD}, client); self.assertEqual(r.status_code, 200)
        client.headers.update({'X-CSRF-Token': r.json()['csrf'], 'X-Account-ID': r.json()['user']['id']})

    def submission(self, stars=5, value='26', client=None):
        client = client or self.player
        payload = {'big': '测试地图', 'small': '测试赛道', 'zone': '五区', 'tier': '高手', 'car': '恶魔', 'stars': stars, 'time': value, 'notes': '独立测试', 'route': ''}
        r = client.post('/api/submissions', json={'request_key': secrets.token_hex(16), 'entries': [payload]})
        self.assertEqual(r.status_code, 200, r.text); sid = r.json()['ids'][0]
        r = client.post('/api/submissions/'+sid+'/submit', json={'revision': 1}); self.assertEqual(r.status_code, 200, r.text)
        return sid

    def detail(self, sid):
        return self.client.get('/api/submissions/'+sid).json()

    def review(self, sid, action='accept', quality=Q, client=None):
        client = client or self.client; detail = self.detail(sid)
        body = {'revision': detail['revision'], 'action': action, 'reason': '独立核验', 'quality': quality}
        if action == 'accept':
            r = client.post('/api/admin/submissions/'+sid+'/preview', json={'revision': detail['revision'], 'entry': detail['payload']})
            self.assertEqual(r.status_code, 200, r.text); body.update(entry=r.json()['candidate'], basis=r.json()['basis'], slower_confirmed=True)
        return client.post('/api/admin/submissions/'+sid+'/review', json=body)

    def plan(self, sid):
        r = self.client.post('/api/admin/score-versions', json={'request_key': secrets.token_hex(16), 'items': [{'id': sid, 'revision': self.detail(sid)['revision']}]})
        self.assertEqual(r.status_code, 200, r.text); return r.json()

    def execute(self, m):
        return self.client.post('/api/admin/score-versions/'+m['id']+'/execute', json={'digest': m['digest'], 'effects_confirmed': True,
            'items': [{'submission_id': i['submission_id'], 'confirmed': True, 'slower_confirmed': True, 'slower_reason': '核验正确'} for i in m['result']['items'] if i['kind'] != 'unchanged']})

    def board(self, period='all'):
        return self.client.get('/api/contributions/leaderboard', params={'period': period}).json()['items']

    def total(self):
        rows = self.board(); return rows[0]['total'] if rows else 0

    def test_full_review_publish_rollback_republish_and_duplicates(self):
        sid = self.submission(); self.assertEqual(self.review(sid).status_code, 200); self.assertEqual(self.total(), 9)
        m = self.plan(sid); self.assertEqual(self.execute(m).status_code, 200); self.assertEqual(self.total(), 19)
        self.assertEqual(self.execute(m).status_code, 200); self.assertEqual(self.total(), 19)
        self.assertEqual(self.board()[0]['effective_count'], 1)  # ordinary mirror is not a contribution
        r = self.client.post('/api/admin/score-versions/'+m['id']+'/rollback', json={'reason': '测试回滚'})
        self.assertEqual(r.status_code, 200, r.text); self.assertEqual(self.total(), 9)
        sid2 = self.submission(); self.assertEqual(self.review(sid2).status_code, 200)
        self.assertEqual(self.execute(self.plan(sid2)).status_code, 200); self.assertEqual(self.total(), 19)
        self.assertEqual(self.board()[0]['effective_count'], 1)

    def test_ignored_scores_and_reopen_suspend(self):
        sid = self.submission(); self.assertEqual(self.review(sid, 'ignore').status_code, 200); self.assertEqual(self.total(), 9)
        self.assertEqual(self.review(sid, 'reopen', None).status_code, 200); self.assertEqual(self.total(), 0)
        self.assertEqual(self.review(sid, 'ignore', {**Q, 'evidence': 3}).status_code, 200); self.assertEqual(self.total(), 8)

    def test_late_rating_after_publication_revision_conflict(self):
        sid = self.submission(); self.assertEqual(self.review(sid, quality=None).status_code, 200)
        self.assertEqual(self.execute(self.plan(sid)).status_code, 200); self.assertEqual(self.total(), 10)
        body = {'revision': self.detail(sid)['revision'], 'quality': Q}
        r = self.client.post('/api/admin/contributions/'+sid+'/rating', json=body); self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(self.total(), 19)
        self.assertEqual(self.client.post('/api/admin/contributions/'+sid+'/rating', json=body).status_code, 409)
        self.assertEqual(self.detail(sid)['application']['state'], 'applied')

    def test_privacy_nickname_anonymous_and_disabled(self):
        sid = self.submission(); self.review(sid, 'ignore')
        self.assertEqual(self.board()[0]['nickname'], '匿名贡献者')
        r = self.player.put('/api/contributions/preferences', json={'revision': 0, 'nickname': '山路补图员', 'anonymous': False}); self.assertEqual(r.status_code, 200)
        self.assertEqual(self.board()[0]['nickname'], '山路补图员')
        public = json.dumps(self.board()); self.assertNotIn('@', public); self.assertNotIn(self.player_user['id'], public); self.assertNotIn('snapshot', public)
        self.assertEqual(self.player.put('/api/contributions/preferences', json={'revision': 0, 'nickname': '旧设置', 'anonymous': True}).status_code, 409)
        self.assertEqual(self.player.put('/api/contributions/preferences', json={'revision': 1, 'nickname': 'x@example.com', 'anonymous': False}).status_code, 422)
        r = self.client.post('/api/admin/accounts/'+self.player_user['id']+'/control', json={'revision': 0, 'action': 'disable', 'reason': '测试停用'})
        self.assertEqual(r.status_code, 200); self.assertEqual(self.board(), [])
        self.assertEqual(self.player.get('/api/contributions/me').status_code, 401)
        r = self.client.post('/api/admin/accounts/'+self.player_user['id']+'/control', json={'revision': 1, 'action': 'restore', 'reason': '恢复'})
        self.assertEqual(r.status_code, 200); self.assertEqual(self.total(), 9)

    def test_self_review_permissions_and_validation(self):
        own = self.submission(client=self.client)
        self.assertEqual(self.review(own, 'ignore').status_code, 403)
        sid = self.submission()
        self.assertEqual(self.review(sid, 'ignore', {**Q, 'evidence': 5}).status_code, 422)
        self.assertEqual(self.review(sid, 'ignore', {**Q, 'evidence': True}).status_code, 422)
        self.assertEqual(self.review(sid, 'ignore', {**Q, 'reason': ' '}).status_code, 422)
        self.assertEqual(self.review(sid, 'ignore', {**Q, 'value': 0}).status_code, 422)
        self.assertEqual(self.review(sid, 'ignore').status_code, 200)
        self.assertEqual(self.player.post('/api/admin/contributions/'+sid+'/rating', json={'revision': 3, 'quality': Q}).status_code, 403)
        self.assertEqual(self.player.get('/api/contributions/me', headers={'X-Account-ID': self.owner['id']}).status_code, 401)
        self.assertEqual(self.client.post('/api/admin/contributions/'+sid+'/rating', json={'revision': 3, 'quality': Q}, headers={'X-CSRF-Token': 'bad'}).status_code, 403)

    def test_months_adjust_original_month(self):
        sid = self.submission()
        with patch('backend.contributions.month', return_value='2026-10'):
            self.review(sid)
        with patch('backend.contributions.month', return_value='2026-11'):
            self.assertEqual(self.execute(self.plan(sid)).status_code, 200)
            self.client.post('/api/admin/contributions/'+sid+'/rating', json={'revision': self.detail(sid)['revision'], 'quality': {**Q, 'evidence': 3}})
        self.assertEqual(self.board('2026-10')[0]['total'], 8)
        self.assertEqual(self.board('2026-11')[0]['total'], 10)
        self.assertEqual(self.total(), 18)
        self.assertEqual(month(1793462400), '2026-11')  # UTC Oct 31 16:00, Beijing Nov 1

    def test_failure_rolls_back_bonus_with_publication(self):
        sid = self.submission(); self.review(sid); m = self.plan(sid)
        def fail(name):
            if name == 'apply_before_commit': raise OSError('test interruption')
        with patch.object(self.writer, 'checkpoint', side_effect=fail):
            self.assertEqual(self.execute(m).status_code, 409)
        self.assertEqual(self.total(), 9)
        self.assertIsNone(self.detail(sid)['application'])

    def test_historical_exclusion_and_explicit_enable(self):
        # Create a fresh independent app without contributions, then activate.
        other = provision(self.lab/'scores/versions'/self.writer.current()[0]['id'])
        try:
            old = create_app(other/'accounts', score_version_lab=other)
            with old.state.store.connect() as db:
                db.execute('INSERT INTO users VALUES(?,?,?,?,?,?)', ('old', 'old@example.test', 'unused', 1, 'player', 1))
                db.execute("INSERT INTO submissions(id,owner_id,batch_id,revision,status,payload,created_at,updated_at) VALUES('historical','old','b',1,'draft','{}',1,1)")
            enabled = create_app(other/'accounts', score_version_lab=other, contributions=True)
            with enabled.state.store.connect() as db:
                self.assertEqual(db.execute('SELECT count(*) FROM contribution_sources').fetchone()[0], 0)
                self.assertEqual(db.execute('SELECT count(*) FROM submissions').fetchone()[0], 1)
            with self.assertRaises(ValueError): create_app(other/'accounts', score_version_lab=other)
            with self.assertRaises(ValueError): create_app(other/'accounts', contributions=True)
            with self.assertRaises(ValueError): create_app(other/'accounts', contributions=True, production=True)
        finally: validate_lab(other); shutil.rmtree(other)

    def test_ties_cutoff_and_public_identity(self):
        with self.app.state.store.connect() as db:
            for i in range(53):
                uid = 'tie'+str(i)
                db.execute('INSERT INTO users VALUES(?,?,?,?,?,?)', (uid, uid+'@example.test', 'unused', 1, 'player', 1))
                points = 10 if i < 49 else 5 if i < 52 else 1
                db.execute('INSERT INTO contributions(user_id,target_key,quality_points,quality_month) VALUES(?,?,?,?)', (uid, 'key', points, month()))
        board = self.board(); self.assertEqual(len(board), 52)
        self.assertEqual(board[48]['rank'], 1); self.assertEqual(board[49]['rank'], 50)

    def test_historical_publish_never_enrolls_and_partial_batch_only_rewards_changes(self):
        historical = self.submission(5)
        with self.app.state.store.connect() as db:
            db.execute('DELETE FROM contribution_sources WHERE submission_id=?', (historical,))
        self.assertEqual(self.review(historical, quality=None).status_code, 200)
        self.assertEqual(self.execute(self.plan(historical)).status_code, 200)
        self.assertEqual(self.total(), 0)
        unchanged = self.submission(5); changed = self.submission(4, '27')
        self.assertEqual(self.review(unchanged).status_code, 200)
        self.assertEqual(self.review(changed).status_code, 200)
        r = self.client.post('/api/admin/score-versions', json={'request_key': secrets.token_hex(16),
            'items': [{'id': s, 'revision': self.detail(s)['revision']} for s in (unchanged, changed)]})
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(self.execute(r.json()).status_code, 200)
        self.assertEqual(self.total(), 28)
        self.assertEqual(self.board()[0]['adopted_count'], 1)

    def test_changed_rating_invalidates_prepared_batch_and_target_cannot_move(self):
        sid = self.submission(); self.review(sid); m = self.plan(sid)
        body = {'revision': self.detail(sid)['revision'], 'quality': {**Q, 'evidence': 3}}
        self.assertEqual(self.client.post('/api/admin/contributions/'+sid+'/rating', json=body).status_code, 200)
        self.assertEqual(self.execute(m).status_code, 409); self.assertEqual(self.total(), 8)
        self.assertEqual(self.review(sid, 'reopen', None).status_code, 200)
        detail = self.detail(sid); entry = {**detail['payload'], 'stars': 4}
        preview = self.client.post('/api/admin/submissions/'+sid+'/preview', json={'revision': detail['revision'], 'entry': entry}).json()
        r = self.client.post('/api/admin/submissions/'+sid+'/review', json={'revision': detail['revision'], 'action': 'accept',
            'entry': preview['candidate'], 'basis': preview['basis'], 'reason': '变更目标', 'quality': Q})
        self.assertEqual(r.status_code, 409); self.assertEqual(self.detail(sid)['status'], 'pending')

    def test_shared_opinion_and_later_rating_preserve_original_review(self):
        sid = self.submission()
        self.assertEqual(self.review(sid, quality={**Q, 'reason': '独立核验'}).status_code, 200)
        detail = self.detail(sid)
        self.assertEqual(detail['decision_reason'], '独立核验')
        self.assertEqual(json.loads(detail['contribution_info']['contribution']['quality'])['reason'], '独立核验')
        candidate = detail['accepted_payload']
        changed = self.client.post('/api/admin/contributions/'+sid+'/rating', json={
            'revision': detail['revision'], 'quality': {**Q, 'evidence': 3, 'reason': '补充复核后调整评分'}})
        self.assertEqual(changed.status_code, 200, changed.text)
        after = self.detail(sid)
        self.assertEqual(after['decision_reason'], '独立核验')
        self.assertEqual(after['accepted_payload'], candidate)
        self.assertEqual(json.loads(after['contribution_info']['contribution']['quality'])['reason'], '补充复核后调整评分')
        self.assertTrue(any(e['action']=='accept' and e['snapshot']['reason']=='独立核验' for e in after['events']))

    def test_more_information_without_quality_and_long_legacy_feedback_are_preserved(self):
        sid = self.submission()
        self.assertEqual(self.review(sid, 'needs_info', None).status_code, 200)
        detail = self.detail(sid)
        self.assertEqual(detail['status'], 'needs_info')
        self.assertIsNone(detail['contribution_info']['contribution'])
        self.assertEqual(self.board(), [])
        other = self.submission(stars=4)
        long_reason = '旧审核意见' * 300
        response = self.client.post('/api/admin/submissions/'+other+'/review', json={
            'revision': self.detail(other)['revision'], 'action': 'ignore', 'reason': long_reason, 'quality': None})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(self.detail(other)['decision_reason'], long_reason)

    def test_zero_quality_and_restart_preserve_ledger(self):
        sid = self.submission()
        zero = {'completeness': 0, 'evidence': 0, 'value': 0, 'reason': '没有独立证据'}
        self.assertEqual(self.review(sid, 'ignore', zero).status_code, 200); self.assertEqual(self.board(), [])
        restarted = create_app(self.path, score_version_lab=self.lab, contributions=True)
        with restarted.state.store.connect() as db:
            self.assertEqual(db.execute('SELECT count(*) FROM contribution_sources').fetchone()[0], 1)
            self.assertEqual(db.execute('SELECT quality_points FROM contributions').fetchone()[0], 0)
            self.assertEqual(db.execute('SELECT count(*) FROM contribution_events').fetchone()[0], 1)


if __name__ == '__main__': unittest.main()
