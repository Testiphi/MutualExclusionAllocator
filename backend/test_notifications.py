"""Isolated fixtures only: independent readers, permissions, and stale cursor races."""
import secrets
import unittest
from backend import test_feedback as fixtures
from backend.app import create_app
from backend.roles import set_role
from backend.notifications import state, migrate


class NotificationTests(unittest.TestCase):
    new_client = fixtures.FeedbackTests.new_client
    login = fixtures.FeedbackTests.login
    post = fixtures.FeedbackTests.post
    token = fixtures.FeedbackTests.token
    signup = fixtures.FeedbackTests.signup
    payload = fixtures.FeedbackTests.payload
    handle = fixtures.FeedbackTests.handle
    create = fixtures.FeedbackTests.create
    tearDown = fixtures.FeedbackTests.tearDown

    def setUp(self):
        fixtures.FeedbackTests.setUp(self)
        self.client.close(); self.player.close()
        self.app = create_app(self.path, score_version_lab=self.lab, contributions=True, feedback=True, notifications=True)
        self.client = self.new_client(); self.login(self.client, 'owner@example.com')
        self.player = self.new_client(); self.login(self.player, 'player@example.com')

    def summary(self, client=None):
        r = (client or self.client).get('/api/notifications')
        self.assertEqual(r.status_code, 200, r.text)
        return r.json()

    def read(self, client, detail, channel):
        return client.post('/api/notifications/read', json={
            'channel': channel, 'item_id': detail['id'], 'event_id': detail['notification_cursors'][channel]})

    def submission(self):
        payload = {'big':'测试地图','small':'测试赛道','zone':'五区','tier':'高手','car':'恶魔','stars':5,'time':'26','notes':'独立测试'}
        r = self.player.post('/api/submissions', json={'request_key':secrets.token_hex(16),'entries':[payload]})
        self.assertEqual(r.status_code, 200, r.text)
        return r.json()['ids'][0]

    def submit(self, sid):
        revision = self.player.get('/api/submissions/'+sid).json()['revision']
        r = self.player.post('/api/submissions/'+sid+'/submit', json={'revision':revision})
        self.assertEqual(r.status_code, 200, r.text)

    def decision(self, sid, action='needs_info'):
        revision = self.client.get('/api/submissions/'+sid).json()['revision']
        r = self.client.post('/api/admin/submissions/'+sid+'/review', json={
            'revision':revision, 'action':action, 'reason':'请补充独立证据'})
        self.assertEqual(r.status_code, 200, r.text)

    def test_feedback_read_is_not_resolution_and_replies_realert(self):
        tid = self.create()['id']
        self.assertEqual(self.summary()['counts']['feedback_admin'], 1)
        self.assertEqual(self.summary(self.player)['counts']['feedback'], 0)
        item = self.client.get('/api/admin/feedback/'+tid).json()
        self.assertEqual(self.summary()['counts']['feedback_admin'], 1)  # GET is read-only
        self.assertTrue(self.client.get('/api/admin/feedback').json()['items'][0]['unread'])
        self.assertEqual(self.read(self.client, item, 'feedback_admin').status_code, 200)
        self.assertEqual(self.summary()['counts']['feedback_admin'], 0)
        self.assertEqual(self.summary()['feedback_pending'], 1)
        self.assertEqual(self.client.get('/api/admin/feedback/summary').json()['pending'], 1)
        self.assertEqual(self.handle(tid,'needs_info',1).status_code, 200)
        self.assertEqual(self.summary(self.player)['counts']['feedback'], 1)
        reply = self.player.get('/api/feedback/'+tid).json()
        self.assertEqual(self.read(self.player,reply,'feedback').status_code,200)
        self.assertEqual(self.player.post('/api/feedback/'+tid+'/reply',json={
            'request_key':secrets.token_hex(16),'revision':2,'message':'补充说明'}).status_code,200)
        self.assertEqual(self.summary()['counts']['feedback_admin'],1)
        self.assertEqual(self.summary(self.player)['counts']['feedback'],0)

    def test_stale_detail_only_acknowledges_rendered_event_and_idempotency(self):
        tid = self.create()['id']
        old = self.client.get('/api/admin/feedback/'+tid).json()
        body = {'request_key':secrets.token_hex(16),'revision':1,'message':'新补充'}
        first=self.player.post('/api/feedback/'+tid+'/reply',json=body)
        self.assertEqual(first.status_code,200)
        self.assertEqual(self.player.post('/api/feedback/'+tid+'/reply',json=body).json(), first.json())
        self.assertEqual(self.read(self.client, old, 'feedback_admin').status_code,200)
        self.assertEqual(self.summary()['counts']['feedback_admin'],1)
        latest=self.client.get('/api/admin/feedback/'+tid).json()
        self.assertEqual(self.read(self.client,latest,'feedback_admin').status_code,200)
        self.assertEqual(self.read(self.client,old,'feedback_admin').status_code,200)
        self.assertEqual(self.summary()['counts']['feedback_admin'],0)
        with self.app.state.store.connect() as db:
            self.assertEqual(db.execute("SELECT count(*) FROM notification_events WHERE channel='feedback_admin'").fetchone()[0],2)

    def test_administrators_read_independently_and_resubmission_realerts(self):
        admin=self.new_client()
        try:
            self.signup('second@example.com',admin);set_role(self.path,'second@example.com','admin');self.login(admin,'second@example.com')
            sid=self.submission()
            self.assertEqual(self.summary()['counts']['review'],0)  # draft is private
            self.submit(sid)
            self.assertEqual(self.summary()['counts']['review'],1)
            self.assertEqual(self.summary(admin)['counts']['review'],1)
            detail=self.client.get('/api/submissions/'+sid).json()
            self.assertEqual(self.read(self.client,detail,'review').status_code,200)
            self.assertEqual(self.summary()['counts']['review'],0)
            self.assertEqual(self.summary(admin)['counts']['review'],1)
            self.decision(sid)
            self.assertEqual(self.summary(admin)['counts']['review'],0)  # no longer actionable
            self.assertEqual(self.summary(self.player)['counts']['submissions'],1)
            detail=self.player.get('/api/submissions/'+sid).json()
            self.assertEqual(self.read(self.player,detail,'submissions').status_code,200)
            self.submit(sid)
            self.assertEqual(self.summary()['counts']['review'],1)
            self.assertEqual(self.summary(admin)['counts']['review'],1)
            self.assertNotIn('feedback_admin',self.summary(admin)['counts'])
        finally:admin.close()

    def test_privacy_session_binding_and_post_csrf(self):
        tid=self.create()['id'];detail=self.client.get('/api/admin/feedback/'+tid).json()
        body={'channel':'feedback_admin','item_id':tid,'event_id':detail['notification_cursors']['feedback_admin']}
        self.assertEqual(self.player.post('/api/notifications/read',json=body).status_code,403)
        self.assertEqual(self.player.post('/api/notifications/read',json={**body,'channel':'feedback'}).status_code,404)
        old=self.client.headers['X-Account-ID'];self.client.headers['X-Account-ID']='different'
        self.assertEqual(self.client.get('/api/notifications').status_code,401)
        self.client.headers['X-Account-ID']=old
        token=self.client.headers.pop('X-CSRF-Token')
        self.assertEqual(self.client.post('/api/notifications/read',json=body).status_code,403)
        self.client.headers['X-CSRF-Token']=token
        self.assertEqual(self.client.post('/api/notifications/read',json={**body,'event_id':True}).status_code,422)
        self.assertEqual(self.summary(self.player)['items']['feedback'],[])

    def test_restart_keeps_reads_and_migration_preserves_old_content(self):
        tid=self.create()['id'];detail=self.client.get('/api/admin/feedback/'+tid).json()
        self.assertEqual(self.read(self.client,detail,'feedback_admin').status_code,200)
        with self.app.state.store.connect() as db:
            before=state(db);migrate(db);self.assertEqual(state(db),before)
        restarted=create_app(self.path,score_version_lab=self.lab,contributions=True,feedback=True,notifications=True)
        self.assertTrue(restarted.state.notifications)
        self.assertEqual(self.summary()['counts']['feedback_admin'],0)
        with self.assertRaises(ValueError):create_app(self.path,score_version_lab=self.lab,contributions=True,feedback=True)

    def test_rating_change_realerts_owner_and_second_session_shares_read_state(self):
        sid=self.submission();self.submit(sid);self.decision(sid,'ignore')
        old=self.player.get('/api/submissions/'+sid).json()
        self.assertEqual(self.read(self.player,old,'submissions').status_code,200)
        r=self.client.post('/api/admin/contributions/'+sid+'/rating',json={'revision':old['revision'],
            'quality':{'completeness':3,'evidence':3,'value':2,'reason':'补充核验后调整评分'}})
        self.assertEqual(r.status_code,200,r.text)
        self.assertEqual(self.summary(self.player)['counts']['submissions'],1)
        latest=self.player.get('/api/submissions/'+sid).json()
        self.assertEqual(self.read(self.player,old,'submissions').status_code,200)
        self.assertEqual(self.summary(self.player)['counts']['submissions'],1)
        another=self.new_client()
        try:
            self.login(another,'player@example.com')
            self.assertEqual(self.summary(another)['counts']['submissions'],1)
            self.assertEqual(self.read(another,latest,'submissions').status_code,200)
            self.assertEqual(self.summary(self.player)['counts']['submissions'],0)
        finally:another.close()


if __name__=='__main__': unittest.main()
