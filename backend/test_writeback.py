import json
import secrets
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from fastapi.testclient import TestClient
from backend import test_accounts as accounts
from backend.app import create_app
from backend.roles import set_role
from backend.writeback_lab import provision,validate_lab
from backend.writeback import hashes,Confirm,Approval,check_workbook

class WritebackTests(unittest.TestCase):
    new_client=accounts.AccountsTests.new_client
    post=accounts.AccountsTests.post
    token=accounts.AccountsTests.token
    signup=accounts.AccountsTests.signup
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();source=Path(self.temp.name)
        self.data={'_version':1,'tracks':[{'大地图':'测试地图','小地图':'测试赛道','五区':{'理论':[],'高手':[{'cars':[{'name':'恶魔','stars':6}],'time':25.0}],'普通':[{'cars':[{'name':'恶魔','stars':6}]}],'自动':[]},'四区':{'理论':[],'高手':[],'普通':[],'自动':[]}}]}
        (source/'gauntlet_data.json').write_text(json.dumps(self.data,ensure_ascii=False),encoding='utf-8')
        shutil.copyfile(Path(__file__).parents[1]/'cars.json',source/'cars.json')
        self.lab=provision(source);self.path=self.lab/'accounts';self.source=self.lab/'data'
        self.app=create_app(self.path,preview_source=self.source,writeback_lab=self.lab)
        self.client=self.new_client();self.actor=self.signup('owner@example.com');set_role(self.path,'owner@example.com','superadmin')
        self.client.cookies.clear();me=self.client.get('/api/auth/me').json();self.client.headers['X-CSRF-Token']=me['csrf']
        result=self.post('login',{'email':'owner@example.com','password':accounts.PASSWORD}).json()
        self.client.headers.update({'X-CSRF-Token':result['csrf'],'X-Account-ID':result['user']['id']})
        self.before=hashes(self.source)
    def tearDown(self):
        self.client.close();validate_lab(self.lab);shutil.rmtree(self.lab);self.temp.cleanup()
    def accepted(self,stars=5,time='26.25'):
        sid=secrets.token_hex(16)
        p={'big':'测试地图','small':'测试赛道','zone':'五区','tier':'高手','car':'恶魔','stars':stars,'route':'','time':time,'notes':'isolated test','video_url':'','unlisted':False}
        with self.app.state.store.connect() as db:
            db.execute("INSERT INTO submissions(id,owner_id,batch_id,revision,status,payload,target_key,accepted_payload,baseline,created_at,updated_at) VALUES (?,?,?,2,'accepted',?,?,?,?,1,1)",(sid,self.actor['id'],secrets.token_hex(16),json.dumps(p),None,json.dumps(p),'{}'))
        return {'id':sid,'revision':2}
    def prepare(self,picks=None):
        picks=picks or [self.accepted()]
        r=self.client.post('/api/admin/previews',json={'request_key':secrets.token_hex(16),'items':picks});self.assertEqual(r.status_code,200,r.text)
        payload={'preview_id':r.json()['id'],'items':picks,'request_key':secrets.token_hex(16)}
        r=self.client.post('/api/admin/writeback',json=payload);self.assertEqual(r.status_code,200,r.text)
        self.assertEqual(hashes(self.source),self.before)
        return r.json(),payload
    def confirmation(self,m):
        return {'digest':m['digest'],'effects_confirmed':True,'items':[{'submission_id':i['submission_id'],'confirmed':True,'slower_confirmed':True,'slower_reason':'isolated slower test'} for i in m['result']['items'] if i['kind']!='unchanged']}
    def execute(self,m):return self.client.post('/api/admin/writeback/'+m['id']+'/execute',json=self.confirmation(m))
    def test_apply_sync_rollback_and_history(self):
        m,p=self.prepare();self.assertEqual(m['result']['summary']['ordinary_mirrors'],1)
        r=self.execute(m);self.assertEqual(r.status_code,200,r.text);self.assertEqual(hashes(self.source),m['after'])
        data=json.loads((self.source/'gauntlet_data.json').read_text())
        self.assertEqual(self.client.get('/gauntlet_data.json').json(),data)
        for name in ('gauntlet_data.xlsx','gauntlet_data_shared.xlsx'):check_workbook(self.source/name,data)
        self.assertEqual(self.execute(m).status_code,200)
        self.assertEqual(self.client.get('/api/admin/accepted-submissions').json()['total'],0)
        sid=p['items'][0]['id']
        r=self.client.post(f'/api/admin/submissions/{sid}/review',json={'revision':2,'action':'reopen','reason':'test'})
        self.assertEqual(r.status_code,409)
        r=self.client.post('/api/admin/writeback/'+m['id']+'/rollback',json={'reason':'验收回滚'});self.assertEqual(r.status_code,200,r.text)
        self.assertEqual(hashes(self.source),self.before)
        self.assertEqual(self.client.get('/api/admin/accepted-submissions').json()['total'],0)
        self.assertEqual(self.client.get('/api/admin/writeback/'+m['id']).json()['state'],'rolled_back')
    def test_confirmation_and_slower_second_gate(self):
        m,_=self.prepare([self.accepted(6,'26')]);c=self.confirmation(m)
        c['items'][0]['confirmed']=False
        self.assertEqual(self.client.post('/api/admin/writeback/'+m['id']+'/execute',json=c).status_code,409)
        c['items'][0]['confirmed']=True;c['items'][0]['slower_confirmed']=False
        self.assertEqual(self.client.post('/api/admin/writeback/'+m['id']+'/execute',json=c).status_code,409)
        c['items'][0]['slower_confirmed']=True;c['items'][0]['slower_reason']=' '
        self.assertEqual(self.client.post('/api/admin/writeback/'+m['id']+'/execute',json=c).status_code,409)
        self.assertEqual(hashes(self.source),self.before)
        self.assertEqual(self.execute(m).status_code,200)
    def test_source_or_workbook_edits_block_and_rollback_preserves(self):
        m,_=self.prepare();book=self.source/'gauntlet_data_shared.xlsx';book.write_bytes(book.read_bytes()+b'edit')
        self.assertEqual(self.execute(m).status_code,409);self.assertTrue(book.read_bytes().endswith(b'edit'))
        book.write_bytes((self.lab/'batches'/m['id']/'before'/book.name).read_bytes())
        self.assertEqual(self.execute(m).status_code,200)
        book.write_bytes(book.read_bytes()+b'new edit')
        self.assertEqual(self.client.post('/api/admin/writeback/'+m['id']+'/rollback',json={'reason':'test'}).status_code,409)
        self.assertTrue(book.read_bytes().endswith(b'new edit'))
    def test_partial_failure_restores_all_files(self):
        m,_=self.prepare();writer=self.app.state.writeback;original=writer.replace;calls=[]
        def replace(folder,name):
            calls.append(name)
            if len(calls)==2:raise OSError('disk error')
            return original(folder,name)
        with patch.object(writer,'replace',side_effect=replace):r=self.execute(m)
        self.assertEqual(r.status_code,409);self.assertEqual(hashes(self.source),self.before)
        self.assertEqual(writer.detail(m['id'])['state'],'failed_restored')
    def test_crash_recovery_after_restart(self):
        m,_=self.prepare();writer=self.app.state.writeback;original=writer.replace;calls=[]
        def crash(folder,name):
            calls.append(name)
            if len(calls)==2:raise KeyboardInterrupt()
            return original(folder,name)
        with patch.object(writer,'replace',side_effect=crash):
            with self.assertRaises(KeyboardInterrupt):writer.execute(self.actor['id'],m['id'],Confirm(**self.confirmation(m)))
        self.assertEqual(writer.detail(m['id'])['state'],'applying')
        from backend.writeback import LabWriter
        restarted=LabWriter(self.lab,self.app.state.store,self.source)
        with restarted.lock():r=restarted.recover_locked(self.actor['id'],m['id'],'重启恢复')
        self.assertEqual(r['state'],'failed_restored');self.assertEqual(hashes(self.source),self.before)
    def test_backup_tamper_and_postreview_stale(self):
        m,_=self.prepare();p=self.lab/'batches'/m['id']/'after/gauntlet_data.json';p.write_bytes(b'{}')
        self.assertEqual(self.execute(m).status_code,409)
        self.assertEqual(hashes(self.source),self.before)
    def test_review_drift_and_request_idempotence(self):
        m,p=self.prepare();r=self.client.post('/api/admin/writeback',json=p);self.assertEqual(r.json()['id'],m['id'])
        with self.app.state.store.connect() as db:db.execute('UPDATE submissions SET revision=revision+1')
        self.assertEqual(self.execute(m).status_code,409)
    def test_permissions_csrf_and_isolation(self):
        m,_=self.prepare()
        self.assertEqual(self.client.post('/api/admin/writeback/'+m['id']+'/execute',json=self.confirmation(m),headers={'X-CSRF-Token':'bad'}).status_code,403)
        with self.app.state.store.connect() as db:db.execute('DELETE FROM super_admins')
        self.assertEqual(self.client.get('/api/admin/writeback').status_code,403)
        with self.assertRaises(ValueError):create_app(Path(self.temp.name)/'accounts',preview_source=self.source,writeback_lab=self.lab)
        with self.assertRaises(ValueError):validate_lab(Path(__file__).parents[1])
    def test_workbook_edits_before_prepare_block(self):
        self.source.joinpath('gauntlet_data.xlsx').write_bytes(b'edited workbook')
        pick=self.accepted();r=self.client.post('/api/admin/previews',json={'request_key':secrets.token_hex(16),'items':[pick]})
        r=self.client.post('/api/admin/writeback',json={'preview_id':r.json()['id'],'items':[pick],'request_key':secrets.token_hex(16)})
        self.assertEqual(r.status_code,409)
        self.assertEqual(self.source.joinpath('gauntlet_data.xlsx').read_bytes(),b'edited workbook')

    def test_subset_recalculates_mirrors_and_lock_conflict(self):
        picks=[self.accepted(5),self.accepted(6,'26')]
        r=self.client.post('/api/admin/previews',json={'request_key':secrets.token_hex(16),'items':picks})
        payload={'preview_id':r.json()['id'],'items':[picks[1]],'request_key':secrets.token_hex(16)}
        r=self.client.post('/api/admin/writeback',json=payload);self.assertEqual(r.status_code,200,r.text)
        m=r.json();self.assertEqual(m['result']['summary']['ordinary_mirrors'],0)
        self.assertEqual(m['result']['summary']['slower'],1)
        with self.app.state.writeback.lock():self.assertEqual(self.execute(m).status_code,409)
        self.assertEqual(hashes(self.source),self.before)

    def test_stale_after_rollback_and_reapplication_blocked(self):
        m,p=self.prepare();self.assertEqual(self.execute(m).status_code,200)
        self.client.post('/api/admin/writeback/'+m['id']+'/rollback',json={'reason':'test'})
        r=self.client.get('/api/admin/previews/'+p['preview_id'])
        self.assertEqual(r.json()['state'],'stale')
        self.assertEqual(self.execute(m).status_code,409)

    def test_recovery_failure_blocks_new_actions_and_can_retry(self):
        m,_=self.prepare();writer=self.app.state.writeback;original=writer.replace;calls=[]
        def fail_after_first(folder,name):
            calls.append(name)
            if len(calls)>1:raise OSError('file locked')
            return original(folder,name)
        with patch.object(writer,'replace',side_effect=fail_after_first):
            with self.assertRaises(OSError):writer.execute(self.actor['id'],m['id'],Confirm(**self.confirmation(m)))
        self.assertEqual(writer.detail(m['id'])['state'],'recovery_required')
        self.assertEqual(self.execute(m).status_code,409)
        with writer.lock():writer.recover_locked(self.actor['id'],m['id'],'解锁后恢复')
        self.assertEqual(hashes(self.source),self.before)

    def test_rollback_crash_resumes_and_backup_is_immutable(self):
        m,_=self.prepare();self.assertEqual(self.execute(m).status_code,200)
        writer=self.app.state.writeback;original=writer.replace;calls=[]
        def crash(folder,name):
            calls.append(name)
            if len(calls)==2:raise KeyboardInterrupt()
            return original(folder,name)
        with patch.object(writer,'replace',side_effect=crash):
            with self.assertRaises(KeyboardInterrupt):writer.rollback(self.actor['id'],m['id'],'测试回滚中断')
        self.assertEqual(writer.detail(m['id'])['state'],'rolling_back')
        with writer.lock():r=writer.recover_locked(self.actor['id'],m['id'],'恢复回滚')
        self.assertEqual(r['state'],'rolled_back');self.assertEqual(hashes(self.source),self.before)
        self.assertEqual(hashes(self.lab/'batches'/m['id']/'before'),self.before)

if __name__=='__main__':unittest.main()
