import base64
import hashlib
import io
import json
from pathlib import Path
import secrets
import shutil
import tempfile
import unittest
from fastapi.testclient import TestClient
from PIL import Image
from backend.app import create_app, Store
from backend.roles import set_role
from backend import test_accounts as accounts

ORIGIN=accounts.ORIGIN
PASSWORD=accounts.PASSWORD

class SubmissionsTests(unittest.TestCase):
    new_client=accounts.AccountsTests.new_client
    post=accounts.AccountsTests.post
    token=accounts.AccountsTests.token
    signup=accounts.AccountsTests.signup
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.path=Path(self.temp.name)
        self.ref=self.path/'reference';self.ref.mkdir()
        root=Path(__file__).resolve().parents[1]
        for name in ('cars.json','gauntlet_data.json'):shutil.copy2(root/name,self.ref/name)
        self.original={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in self.ref.iterdir()}
        self.app=create_app(self.path/'db',reference_dir=self.ref)
        # Test helper reads local outbox under self.path.
        self.path=self.path/'db'
        self.client=self.new_client();self.player=self.signup('player@example.com')
        self.admin=self.new_client();self.signup('admin@example.com',self.admin)
        set_role(self.path,'admin@example.com','admin');self.login(self.admin,'admin@example.com')
        self.other=self.new_client();self.signup('other@example.com',self.other)
        data=json.loads((self.ref/'gauntlet_data.json').read_text(encoding='utf-8'))
        for track in data['tracks']:
            hit=next((e for e in track['五区']['高手'] if e.get('time') and not e.get('sc') and e['cars'][0].get('stars')),None)
            if hit:
                self.entry={'big':track['大地图'],'small':track['小地图'],'zone':'五区','tier':'高手','car':hit['cars'][0]['name'],'stars':hit['cars'][0]['stars'],'route':'','time':str(hit['time']),'notes':'测试成绩证据说明','video_url':'','unlisted':False}
                break
    def tearDown(self):
        self.client.close();self.admin.close();self.other.close();self.temp.cleanup()
    def login(self,c,email):
        c.cookies.clear();me=c.get('/api/auth/me').json();c.headers['X-CSRF-Token']=me['csrf']
        result=self.post('login',{'email':email,'password':PASSWORD},c)
        self.assertEqual(result.status_code,200,result.text)
        c.headers.update({'X-CSRF-Token':result.json()['csrf'],'X-Account-ID':result.json()['user']['id']})
    def create(self,entry=None):
        result=self.client.post('/api/submissions',json={'request_key':secrets.token_hex(16),'entries':[entry or self.entry]})
        self.assertEqual(result.status_code,200,result.text);return result.json()['ids'][0]
    def detail(self,sid,client=None):return (client or self.client).get('/api/submissions/'+sid)
    def submit(self,sid):
        detail=self.detail(sid).json();return self.client.post(f'/api/submissions/{sid}/submit',json={'revision':detail['revision']})
    def preview(self,sid,entry=None):
        detail=self.detail(sid,self.admin).json()
        return self.admin.post(f'/api/admin/submissions/{sid}/preview',json={'revision':detail['revision'],'entry':entry or self.entry})
    def decision(self,sid,action='accept',entry=None,reason='',**extra):
        detail=self.detail(sid,self.admin).json()
        body={'revision':detail['revision'],'action':action,'reason':reason}
        if action=='accept':
            result=self.preview(sid,entry);self.assertEqual(result.status_code,200,result.text)
            body.update(entry=result.json()['candidate'],basis=result.json()['basis'])
        body.update(extra)
        return self.admin.post(f'/api/admin/submissions/{sid}/review',json=body)
    def test_create_batch_idempotence_draft_privacy_and_payload_limits(self):
        body={'request_key':'test-request-key-0001','entries':[self.entry,self.entry]}
        first=self.client.post('/api/submissions',json=body);second=self.client.post('/api/submissions',json=body)
        self.assertEqual(first.json(),second.json());self.assertEqual(len(first.json()['ids']),2)
        sid=first.json()['ids'][0]
        self.assertEqual(self.detail(sid,self.other).status_code,404)
        self.assertEqual(self.detail(sid,self.admin).status_code,404)
        self.assertEqual(self.admin.get('/api/submissions?scope=review').json()['total'],0)
        self.assertEqual(self.other.get('/api/submissions?scope=review').status_code,403)
        self.assertEqual(self.client.post('/api/submissions',json={**body,'entries':[dict(self.entry,time='1')]}).status_code,409)
        self.assertEqual(self.client.post('/api/submissions',json={**body,'entries':[self.entry]*21}).status_code,422)
    def test_submit_return_edit_resubmit_accept_preserves_original_and_no_file_writes(self):
        sid=self.create();self.assertEqual(self.submit(sid).status_code,200)
        self.assertEqual(self.decision(sid,'needs_info',reason='请说明计时依据').status_code,200)
        detail=self.detail(sid).json();corrected=dict(self.entry,notes='已补充新的计时依据与视频说明')
        edited=self.client.put('/api/submissions/'+sid,json={'revision':detail['revision'],'entry':corrected})
        self.assertEqual(edited.status_code,200);self.assertEqual(self.submit(sid).status_code,200)
        candidate=dict(corrected,time=str(float(corrected['time'])-0.01))
        self.assertEqual(self.decision(sid,entry=candidate,reason='按视频核对修正').status_code,200)
        final=self.detail(sid).json()
        self.assertEqual(final['status'],'accepted');self.assertEqual(final['payload']['time'],self.entry['time'])
        self.assertEqual(final['accepted_payload']['time'],candidate['time'])
        self.assertEqual([e['action'] for e in final['events']],['created','submitted','needs_info','edited','submitted','accept'])
        self.assertEqual(final['events'][0]['snapshot']['raw'],self.entry)
        self.assertEqual({p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in self.ref.iterdir()},self.original)
        self.assertEqual(self.submit(sid).status_code,409)
    def test_slower_requires_both_reason_and_explicit_ack(self):
        sid=self.create();self.submit(sid);slower=dict(self.entry,time=str(float(self.entry['time'])+1))
        self.assertEqual(self.preview(sid,slower).json()['comparison']['kind'],'slower')
        self.assertEqual(self.decision(sid,entry=slower,reason='修正旧误差').status_code,422)
        self.assertEqual(self.decision(sid,entry=slower,slower_confirmed=True).status_code,422)
        self.assertEqual(self.decision(sid,entry=slower,reason='修正旧误差',slower_confirmed=True).status_code,200)
    def test_stale_revision_and_changed_baseline_block_acceptance(self):
        sid=self.create();self.submit(sid);preview=self.preview(sid).json()
        stale={'revision':1,'action':'ignore','reason':'重复'}
        self.assertEqual(self.admin.post(f'/api/admin/submissions/{sid}/review',json=stale).status_code,409)
        for name in ('gauntlet_data.json','cars.json'):
            with (self.ref/name).open('a',encoding='utf-8') as f:f.write('\n')
            result=self.admin.post(f'/api/admin/submissions/{sid}/review',json={'revision':2,'action':'accept','entry':preview['candidate'],'basis':preview['basis']})
            self.assertEqual(result.status_code,409)
            preview=self.preview(sid).json()
        self.assertEqual(self.decision(sid).status_code,200)
    def test_duplicates_reopen_and_ignore_never_delete_official_data(self):
        a=self.create();b=self.create();self.submit(a);self.submit(b)
        self.assertEqual(self.decision(a).status_code,200)
        self.assertEqual(self.decision(b).status_code,409)
        self.assertEqual(self.decision(a,'reopen',reason='改采另一份证据').status_code,200)
        self.assertEqual(self.decision(a,'ignore',reason='重复投稿，采纳另一份证据').status_code,200)
        self.assertEqual(self.decision(b).status_code,200)
        self.assertEqual({p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in self.ref.iterdir()},self.original)
    def test_score_validation_minutes_precision_pool_stars_and_routes(self):
        for patch in ({'time':'nan'},{'time':'1e2'},{'time':'26.1234'},{'time':'1:65'},{'time':'0'},{'stars':None},{'route':'未登记跑法'},{'car':'未知车'},{'small':'不存在的图'}):
            sid=self.create(dict(self.entry,**patch));self.assertEqual(self.submit(sid).status_code,422,patch)
        sid=self.create(dict(self.entry,time='1:02.345'));self.assertEqual(self.submit(sid).status_code,200)
        self.assertEqual(self.detail(sid).json()['payload']['time'],'62.345')
        self.assertEqual(self.client.post('/api/submissions',json={'request_key':secrets.token_hex(16),'entries':[dict(self.entry,video_url='javascript:alert(1)')]}).status_code,422)
    def test_unlisted_requests_can_be_returned_but_not_accepted_unresolved(self):
        sid=self.create({'unlisted':True,'notes':'新车辆尚未收录，请管理员核对车辆资料与适用星级规则'})
        self.assertEqual(self.submit(sid).status_code,200)
        candidate=self.detail(sid).json()['payload']
        self.assertEqual(self.preview(sid,candidate).json()['comparison']['kind'],'rule_needed')
        self.assertEqual(self.decision(sid,entry=candidate,reason='希望新增').status_code,422)
        self.assertEqual(self.decision(sid,'needs_info',reason='请提供车辆真名').status_code,200)
    def test_theory_requires_source_and_pool_rule_reuse(self):
        sid=self.create(dict(self.entry,tier='理论',stars=None,notes=''))
        self.assertEqual(self.submit(sid).status_code,422)
        sid=self.create(dict(self.entry,tier='理论',stars=None,notes='资料来源：个人逐帧核对'))
        self.assertEqual(self.submit(sid).status_code,200)
        sid=self.create(dict(self.entry,car='恶魔',zone='四区',stars=6))
        self.assertEqual(self.submit(sid).status_code,422)
    def test_image_authorization_reencoding_history_and_size_validation(self):
        sid=self.create();buffer=io.BytesIO();Image.new('RGB',(12,12),'red').save(buffer,format='PNG')
        body={'revision':1,'data':base64.b64encode(buffer.getvalue()).decode()}
        self.assertEqual(self.other.post(f'/api/submissions/{sid}/images',json=body).status_code,404)
        self.assertEqual(self.client.post(f'/api/submissions/{sid}/images',json={'revision':1,'data':'not valid'}).status_code,422)
        upload=self.client.post(f'/api/submissions/{sid}/images',json=body);self.assertEqual(upload.status_code,200,upload.text)
        iid=upload.json()['id'];url=f'/api/submissions/{sid}/images/{iid}'
        self.assertEqual(self.other.get(url).status_code,404)
        self.assertEqual(self.admin.get(url).status_code,404)
        image=self.client.get(url);self.assertEqual(image.headers['content-type'],'image/jpeg');self.assertTrue(image.content.startswith(b'\xff\xd8'))
        self.submit(sid);self.assertEqual(self.admin.get(url).status_code,200)
        self.assertEqual(self.client.request('DELETE',url,json={'revision':3}).status_code,409)
        self.decision(sid,'needs_info',reason='请更换清晰截图')
        revision=self.detail(sid).json()['revision']
        self.assertEqual(self.client.request('DELETE',url,json={'revision':revision}).status_code,200)
        detail=self.detail(sid).json();self.assertEqual(detail['images'],[])
        self.assertIn(iid,detail['events'][1]['snapshot']['images'])
        self.assertEqual(self.client.get(url).status_code,200)
    def test_permissions_csrf_account_binding_and_demotion(self):
        sid=self.create();self.submit(sid)
        self.assertEqual(self.client.post(f'/api/admin/submissions/{sid}/review',json={'revision':2,'action':'ignore','reason':'x'}).status_code,403)
        self.assertEqual(self.other.put('/api/submissions/'+sid,json={'revision':2,'entry':self.entry}).status_code,404)
        self.assertEqual(self.client.get('/api/submissions',headers={'X-Account-ID':'other'}).status_code,401)
        self.assertEqual(self.admin.post(f'/api/admin/submissions/{sid}/review',json={'revision':2,'action':'ignore','reason':'x'},headers={'X-CSRF-Token':'wrong'}).status_code,403)
        set_role(self.path,'admin@example.com','player')
        self.assertEqual(self.admin.get('/api/submissions?scope=review').status_code,401)
    def test_scores_visible_zero_nullable_and_no_self_scoring(self):
        sid=self.create();self.submit(sid)
        for invalid in [-1,6,True,'5',2.5]:
            self.assertEqual(self.decision(sid,review_score=invalid).status_code,422)
        self.assertEqual(self.decision(sid,'ignore',reason='数据完整但已有同值，不重复收录',review_score=5).status_code,200)
        detail=self.detail(sid).json()
        self.assertEqual(detail['review_score'],5)
        self.assertEqual(detail['status'],'ignored')
        self.assertEqual(detail['events'][-1]['snapshot']['review_score'],5)
        self.decision(sid,'reopen',reason='重新核实')
        self.assertIsNone(self.detail(sid).json()['review_score'])
        self.assertEqual(self.decision(sid,'needs_info',reason='证据缺失',review_score=0).status_code,200)
        self.assertEqual(self.detail(sid).json()['review_score'],0)
        self.submit(sid)
        self.assertIsNone(self.detail(sid).json()['review_score'])
        self.assertEqual(self.decision(sid).status_code,200)
        self.assertIsNone(self.detail(sid).json()['review_score'])
        self.assertEqual(self.client.get('/api/submissions').json()['items'][0]['review_score'],None)
        with self.app.state.store.connect() as db:
            self.assertEqual(db.execute('SELECT role FROM users WHERE id=?',(self.player['id'],)).fetchone()[0],'player')

    def test_four_tier_reclassification_preserves_raw_time_and_routes(self):
        for tier in ['理论','普通','自动']:
            sid=self.create();self.submit(sid)
            candidate=dict(self.entry,tier=tier)
            preview=self.preview(sid,candidate).json()
            if tier in ['普通','自动']:
                self.assertTrue(preview['comparison']['kind'].startswith('availability'))
                self.assertEqual(preview['comparison']['new'],'✓')
                self.assertIsNone(preview['comparison']['delta'])
            response=self.decision(sid,entry=candidate,reason='管理员调整归档',review_score=4)
            self.assertEqual(response.status_code,200,response.text)
            detail=self.detail(sid).json()
            self.assertEqual(detail['payload']['tier'],'高手')
            self.assertEqual(detail['accepted_payload']['tier'],tier)
            self.assertEqual(detail['accepted_payload']['time'],self.entry['time'])
        sid=self.create(dict(self.entry,tier='普通',route='滑栏杆'))
        self.assertEqual(self.submit(sid).status_code,422)
        self.assertEqual({p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in self.ref.iterdir()},self.original)

    def test_two_admin_windows_cannot_accept_same_target_concurrently(self):
        a=self.create();b=self.create();self.submit(a);self.submit(b)
        import threading
        from concurrent.futures import ThreadPoolExecutor
        barrier=threading.Barrier(2)
        previews={sid:self.preview(sid).json() for sid in [a,b]}
        def decide(sid):
            with TestClient(self.app,base_url=ORIGIN) as client:
                client.cookies.update(self.admin.cookies);client.headers.update(self.admin.headers)
                preview=previews[sid];barrier.wait()
                return client.post(f'/api/admin/submissions/{sid}/review',json={'revision':2,'action':'accept','entry':preview['candidate'],'basis':preview['basis'],'review_score':5}).status_code
        with ThreadPoolExecutor(max_workers=2) as pool: statuses=list(pool.map(decide,[a,b]))
        self.assertEqual(sorted(statuses),[200,409])
        with self.app.state.store.connect() as db:
            self.assertEqual(db.execute("SELECT count(*) FROM submissions WHERE status='accepted'").fetchone()[0],1)

    def test_migration_from_v2_preserves_existing_submission(self):
        sid=self.create();self.submit(sid)
        with self.app.state.store.connect() as db:
            db.execute('ALTER TABLE submissions DROP COLUMN review_score')
            db.execute('DELETE FROM schema_version WHERE version=3')
        migrated=Store(self.path)
        with migrated.connect() as db:
            row=db.execute('SELECT status,revision,review_score FROM submissions WHERE id=?',(sid,)).fetchone()
            self.assertEqual((row['status'],row['revision'],row['review_score']),('pending',2,None))
            self.assertEqual(db.execute('SELECT max(version) FROM schema_version').fetchone()[0],3)

    def test_migration_from_v1_preserves_users_and_profile(self):
        self.client.put('/api/me/profile',json={'revision':0,'cars':[],'stars':{}})
        with self.app.state.store.connect() as db:
            count=db.execute('SELECT count(*) FROM users').fetchone()[0]
            for table in ['submission_events','submission_images','submission_requests','submissions','role_events']:
                db.execute('DROP TABLE '+table)
            db.execute('DELETE FROM schema_version WHERE version>=2')
        migrated=Store(self.path)
        with migrated.connect() as db:
            self.assertEqual(db.execute('SELECT max(version) FROM schema_version').fetchone()[0],3)
            self.assertEqual(db.execute('SELECT count(*) FROM users').fetchone()[0],count)
            self.assertEqual(db.execute('SELECT revision FROM profiles').fetchone()[0],1)
            self.assertEqual(db.execute('PRAGMA foreign_key_check').fetchall(),[])

if __name__=='__main__':unittest.main()
