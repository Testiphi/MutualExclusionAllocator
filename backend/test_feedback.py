import json
import secrets
import unittest
from backend import test_contributions as fixtures
from backend.app import create_app
from backend.roles import set_role


class FeedbackTests(unittest.TestCase):
    new_client = fixtures.ContributionTests.new_client
    login = fixtures.ContributionTests.login
    post = fixtures.ContributionTests.post
    token = fixtures.ContributionTests.token
    signup = fixtures.ContributionTests.signup
    tearDown = fixtures.ContributionTests.tearDown

    def setUp(self):
        fixtures.ContributionTests.setUp(self)
        self.client.close(); self.player.close()
        self.app = create_app(self.path, score_version_lab=self.lab, contributions=True, feedback=True)
        self.client = self.new_client(); self.login(self.client, 'owner@example.com')
        self.player = self.new_client(); self.login(self.player, 'player@example.com')

    def payload(self, **updates):
        return {'request_key': secrets.token_hex(16), 'category':'bug', 'title':'手机页面问题',
                'description':'点击按钮之后没有显示预期内容', 'steps':'打开页面后点击返回',
                'expected':'回到主页', 'actual':'没有变化', 'source_page':'/leaderboard', **updates}

    def create(self, client=None, **updates):
        response = (client or self.player).post('/api/feedback', json=self.payload(**updates))
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def handle(self, ticket, status, revision, **updates):
        return self.client.post('/api/admin/feedback/'+ticket+'/handle', json={
            'request_key':secrets.token_hex(16), 'revision':revision, 'status':status,
            'message':'已检查，请按说明继续操作', **updates})

    def test_private_full_workflow_and_no_score_changes(self):
        with self.app.state.store.connect() as db:
            original = {name:[tuple(r) for r in db.execute('SELECT * FROM '+name)]
                        for name in ('submissions','contributions','score_current','profiles')}
        ticket = self.create(); tid=ticket['id']
        self.assertEqual(self.client.get('/api/admin/feedback/summary').json()['pending'],1)
        detail=self.player.get('/api/feedback/'+tid).json()
        self.assertEqual(detail['status'],'pending'); self.assertEqual(detail['app_version'],'local-feedback-v1')
        self.assertNotIn('owner_email',detail)
        self.assertEqual(self.handle(tid,'processing',1).status_code,200)
        self.assertEqual(self.handle(tid,'needs_info',2).status_code,200)
        reply={'request_key':secrets.token_hex(16),'revision':3,'message':'补充：刷新后仍能复现'}
        r=self.player.post('/api/feedback/'+tid+'/reply',json=reply)
        self.assertEqual(r.status_code,200,r.text); self.assertEqual(r.json()['status'],'pending')
        self.assertEqual(self.handle(tid,'resolved',4).status_code,200)
        reply.update(request_key=secrets.token_hex(16),revision=5,message='仍存在问题')
        self.assertEqual(self.player.post('/api/feedback/'+tid+'/reply',json=reply).json()['status'],'pending')
        self.assertEqual(self.handle(tid,'closed',6).status_code,200)
        reply.update(request_key=secrets.token_hex(16),revision=7)
        self.assertEqual(self.player.post('/api/feedback/'+tid+'/reply',json=reply).status_code,409)
        detail=self.player.get('/api/feedback/'+tid).json()
        self.assertEqual(len(detail['events']),7)
        self.assertEqual(detail['description'],'点击按钮之后没有显示预期内容')
        self.assertEqual(self.handle(tid,'pending',7).status_code,200)
        with self.app.state.store.connect() as db:
            self.assertEqual(original,{name:[tuple(r) for r in db.execute('SELECT * FROM '+name)] for name in original})

    def test_idempotency_conflict_limits_and_empty_input(self):
        body=self.payload(); first=self.player.post('/api/feedback',json=body)
        self.assertEqual(first.status_code,200)
        self.assertEqual(self.player.post('/api/feedback',json=body).json(),first.json())
        self.assertEqual(self.player.post('/api/feedback',json={**body,'title':'different'}).status_code,409)
        tid=first.json()['id']; reply={'revision':1,'message':'补充','request_key':secrets.token_hex(16)}
        a=self.player.post('/api/feedback/'+tid+'/reply',json=reply)
        self.assertEqual(a.status_code,200)
        self.assertEqual(self.player.post('/api/feedback/'+tid+'/reply',json=reply).json(),a.json())
        self.assertEqual(self.handle(tid,'processing',1).status_code,409)
        for changes in ({'title':' '},{'description':' '},{'source_page':'/?token=secret'},
                        {'source_page':'https://evil.example/'},{'app_version':'forged'},{'category':'unknown'}):
            self.assertEqual(self.player.post('/api/feedback',json=self.payload(**changes)).status_code,422)
        for _ in range(9): self.create()
        self.assertEqual(self.player.post('/api/feedback',json=self.payload()).status_code,429)
        self.assertEqual(self.player.post('/api/feedback',json=body).json(),first.json())

    def test_authorization_csrf_and_user_isolation(self):
        tid=self.create()['id']
        other=self.new_client()
        try:
            self.signup('other@example.com',other)
            self.assertEqual(other.get('/api/feedback').json()['total'],0)
            self.assertEqual(other.get('/api/feedback/'+tid).status_code,404)
            self.assertEqual(other.post('/api/feedback/'+tid+'/reply',json={'request_key':secrets.token_hex(16),'revision':1,'message':'x'}).status_code,404)
            self.assertEqual(other.get('/api/admin/feedback').status_code,403)
            set_role(self.path,'other@example.com','admin'); self.login(other,'other@example.com')
            self.assertEqual(other.get('/api/admin/feedback/'+tid).status_code,403)
            self.assertEqual(other.get('/api/admin/feedback/summary').status_code,403)
        finally: other.close()
        self.assertEqual(self.player.get('/api/feedback',headers={'X-Account-ID':self.owner['id']}).status_code,401)
        self.assertEqual(self.player.post('/api/feedback',json=self.payload(),headers={'X-CSRF-Token':'bad'}).status_code,403)
        self.assertEqual(self.player.post('/api/feedback',json=self.payload(),headers={'Origin':'https://evil.example'}).status_code,403)
        response=self.client.post('/api/admin/accounts/'+self.player_user['id']+'/control',json={'revision':0,'action':'disable','reason':'test'})
        self.assertEqual(response.status_code,200)
        self.assertEqual(self.player.get('/api/feedback/'+tid).status_code,401)

    def test_nicknames_search_anonymity_and_fallback(self):
        r=self.player.put('/api/contributions/preferences',json={'revision':0,'nickname':'山路%玩家','anonymous':True})
        self.assertEqual(r.status_code,200)
        result=self.client.get('/api/admin/accounts',params={'q':'山路%'}).json()
        self.assertEqual(result['total'],1)
        self.assertEqual(result['items'][0]['nickname'],'山路%玩家')
        self.assertEqual(result['items'][0]['leaderboard_anonymous'],1)
        self.assertEqual(self.client.get('/api/admin/accounts',params={'q':'player@example.com'}).json()['total'],1)
        self.assertEqual(self.player.get('/api/admin/accounts').status_code,403)
        self.assertEqual(self.client.get('/api/admin/accounts',params={'q':'owner@example.com'}).json()['items'][0]['nickname'],'')
        self.assertEqual(self.client.get('/api/contributions/leaderboard').json()['items'],[])

    def test_filters_unverified_and_restart_preserve_feedback(self):
        tid=self.create(title='<script>alert(1)</script>')['id']
        self.assertEqual(self.client.get('/api/admin/feedback',params={'status':'pending','q':'<script>'}).json()['total'],1)
        self.assertEqual(self.player.get('/api/feedback',params={'status':'resolved'}).json()['total'],0)
        self.assertEqual(self.player.get('/api/feedback',params={'offset':-1}).status_code,422)
        with self.app.state.store.connect() as db: db.execute('UPDATE users SET verified=0 WHERE id=?',(self.player_user['id'],))
        self.assertEqual(self.player.get('/api/feedback/'+tid).status_code,403)
        restarted=create_app(self.path,score_version_lab=self.lab,contributions=True,feedback=True)
        with restarted.state.store.connect() as db:
            self.assertEqual(db.execute('SELECT title FROM feedback_tickets WHERE id=?',(tid,)).fetchone()[0],'<script>alert(1)</script>')
        with self.assertRaises(ValueError):create_app(self.path,score_version_lab=self.lab,contributions=True)
        with self.assertRaises(ValueError):create_app(self.path,feedback=True)
        with self.assertRaises(ValueError):create_app(self.path,feedback=True,production=True)


if __name__ == '__main__': unittest.main()
