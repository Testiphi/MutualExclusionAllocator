import hashlib
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
from backend.score_repository import provision,validate_lab,Versions,FILES
from backend.score_versions import Confirm
from backend.previews import flatten, key
from backend.submissions import identity

class ScoreVersionTests(unittest.TestCase):
    new_client=accounts.AccountsTests.new_client
    post=accounts.AccountsTests.post
    token=accounts.AccountsTests.token
    signup=accounts.AccountsTests.signup
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.seed=Path(self.temp.name)
        self.data={'_version':1,'tracks':[{'大地图':'测试地图','小地图':'测试赛道','五区':{'理论':[],'高手':[{'cars':[{'name':'恶魔','stars':6}],'time':25.0}],'普通':[{'cars':[{'name':'恶魔','stars':6}]}],'自动':[]},'四区':{'理论':[],'高手':[],'普通':[],'自动':[]}}]}
        self.data['tracks'].append({
            '大地图':'古老斗技场','小地图':'十字路口',
            '五区':{'理论':[],'高手':[],'普通':[],'自动':[]},
            '四区':{
                '理论':[{'cars':[{'name':'爱音'}],'time':23.1,'sc':True,'sc_type':'跳图'}],
                '高手':[{'cars':[{'name':'爱音','stars':4}],'time':23.9,'sc':True,'sc_type':'跳图'},
                      {'cars':[{'name':'爱音','stars':3}],'time':27.2}],
                '普通':[{'cars':[{'name':'爱音','stars':3}]}],'自动':[]}})
        (self.seed/'gauntlet_data.json').write_text(json.dumps(self.data,ensure_ascii=False),encoding='utf-8')
        shutil.copyfile(Path(__file__).parents[1]/'cars.json',self.seed/'cars.json')
        self.original={n:hashlib.sha256((self.seed/n).read_bytes()).hexdigest() for n in FILES}
        self.lab=provision(self.seed);self.path=self.lab/'accounts'
        self.app=create_app(self.path,score_version_lab=self.lab);self.writer=self.app.state.score_versions
        self.client=self.new_client();self.actor=self.signup('owner@example.com');set_role(self.path,'owner@example.com','superadmin')
        self.client.cookies.clear();self.client.headers['X-CSRF-Token']=self.client.get('/api/auth/me').json()['csrf']
        r=self.post('login',{'email':'owner@example.com','password':accounts.PASSWORD}).json()
        self.client.headers.update({'X-CSRF-Token':r['csrf'],'X-Account-ID':r['user']['id']})
        self.base=self.writer.current()[0]['id'];self.reauth()
    def tearDown(self):
        self.client.close();validate_lab(self.lab);shutil.rmtree(self.lab);self.temp.cleanup()
    def reauth(self):
        r=self.client.post('/api/admin/score-versions/reauth',json={'password':accounts.PASSWORD});self.assertEqual(r.status_code,200,r.text)
    def accepted(self,stars=5,time='26.25',tier='高手'):
        sid=secrets.token_hex(16);p={'big':'测试地图','small':'测试赛道','zone':'五区','tier':tier,'car':'恶魔','stars':stars,'route':'','time':time,'notes':'test','video_url':'','unlisted':False}
        with self.app.state.store.connect() as db:
            db.execute("INSERT INTO submissions(id,owner_id,batch_id,revision,status,payload,target_key,accepted_payload,baseline,created_at,updated_at) VALUES (?,?,?,2,'accepted',?,?,?,?,1,1)",(sid,self.actor['id'],secrets.token_hex(16),json.dumps(p),None,json.dumps(p),'{}'))
        return {'id':sid,'revision':2}
    def plan(self,picks=None):
        body={'request_key':secrets.token_hex(16),'items':picks or [self.accepted()]}
        r=self.client.post('/api/admin/score-versions',json=body);self.assertEqual(r.status_code,200,r.text)
        self.assertEqual(self.writer.current()[0]['id'],r.json()['base']);return r.json(),body
    def confirmation(self,m):
        return {'digest':m['digest'],'effects_confirmed':True,'items':[{'submission_id':i['submission_id'],'confirmed':True,'slower_confirmed':True,'slower_reason':'测试明确接受更慢'} for i in m['result']['items'] if i['kind']!='unchanged']}
    def execute(self,m):return self.client.post('/api/admin/score-versions/'+m['id']+'/execute',json=self.confirmation(m))
    def rollback(self,m):return self.client.post('/api/admin/score-versions/'+m['id']+'/rollback',json={'reason':'测试回滚'})
    def session_hash(self):
        from backend.app import digest,COOKIE
        return digest(self.client.cookies.get(COOKIE))
    def test_apply_restart_and_rollback_preserve_accounts_and_code(self):
        m,_=self.plan();self.assertEqual(m['result']['summary']['ordinary_mirrors'],1)
        self.assertEqual(self.execute(m).status_code,200)
        info,contents=self.writer.current();self.assertEqual(info['id'],m['target'])
        self.assertEqual(self.client.get('/gauntlet_data.json').json(),json.loads(contents['gauntlet_data.json']))
        self.assertEqual(self.client.get('/api/scores/snapshot').json()['version'],m['target'])
        detail=self.client.get('/api/submissions/'+m['result']['items'][0]['submission_id']).json()
        self.assertEqual(detail['basis']['data'],info['files']['gauntlet_data.json'])
        self.assertEqual(detail['application']['state'],'applied')
        restarted=create_app(self.path,score_version_lab=self.lab)
        self.assertEqual(restarted.state.score_versions.current()[0]['id'],m['target'])
        # Later account data must survive score rollback.
        other=self.new_client();self.signup('later@example.com',other);other.close()
        with self.app.state.store.connect() as db:
            before=[tuple(r) for r in db.execute('SELECT * FROM users ORDER BY id')]
        r=self.rollback(m);self.assertEqual(r.status_code,200,r.text)
        restored,raw=self.writer.current();self.assertNotEqual(restored['id'],m['base'])
        self.assertEqual(restored['parent'],m['target']);self.assertEqual(json.loads(raw['gauntlet_data.json']),self.data)
        with self.app.state.store.connect() as db:self.assertEqual(before,[tuple(r) for r in db.execute('SELECT * FROM users ORDER BY id')])
        self.assertEqual(self.client.get('/api/admin/accepted-submissions').json()['total'],0)
        self.assertEqual(self.execute(m).status_code,409)
        for n,h in self.original.items():self.assertEqual(hashlib.sha256((self.seed/n).read_bytes()).hexdigest(),h)
    def test_item_effect_and_slower_confirmations(self):
        m,_=self.plan([self.accepted(6,'26')]);body=self.confirmation(m);url='/api/admin/score-versions/'+m['id']+'/execute'
        for change in ({'confirmed':False},{'slower_confirmed':False},{'slower_reason':' '}):
            body=self.confirmation(m);body['items'][0].update(change);self.assertEqual(self.client.post(url,json=body).status_code,409)
        body=self.confirmation(m);body['effects_confirmed']=False;self.assertEqual(self.client.post(url,json=body).status_code,409)
        self.assertEqual(self.writer.current()[0]['id'],self.base);self.assertEqual(self.execute(m).status_code,200)
    def test_reauthentication_permissions_and_csrf(self):
        m,_=self.plan()
        with self.app.state.store.connect() as db:db.execute('UPDATE score_reauth SET expires=0')
        self.assertEqual(self.execute(m).status_code,403)
        self.assertEqual(self.client.post('/api/admin/score-versions/reauth',json={'password':'wrong'}).status_code,401)
        self.reauth();self.assertEqual(self.client.post('/api/admin/score-versions/'+m['id']+'/execute',json=self.confirmation(m),headers={'X-CSRF-Token':'bad'}).status_code,403)
        with self.app.state.store.connect() as db:db.execute('DELETE FROM super_admins')
        self.assertEqual(self.execute(m).status_code,403)
        self.assertEqual(self.client.get('/api/admin/score-versions').status_code,403)
    def test_idempotence_and_later_version_blocks_old_rollback(self):
        m,body=self.plan();again=self.client.post('/api/admin/score-versions',json=body).json();self.assertEqual(again['id'],m['id'])
        self.assertEqual(self.execute(m).status_code,200);self.assertEqual(self.execute(m).status_code,200)
        m2,_=self.plan([self.accepted(4)]);self.assertEqual(self.execute(m2).status_code,200)
        self.assertEqual(self.rollback(m).status_code,409)
        self.assertEqual(self.writer.current()[0]['id'],m2['target'])
    def test_review_drift_and_data_version_stale(self):
        m,_=self.plan()
        with self.app.state.store.connect() as db:db.execute('UPDATE submissions SET revision=revision+1')
        self.assertEqual(self.execute(m).status_code,409)
        self.assertTrue(self.writer.detail(m['id'])['stale_reasons'])
        p,_=self.plan([self.accepted(4)]);q,_=self.plan([self.accepted(3)])
        self.assertEqual(self.execute(p).status_code,200);self.assertEqual(self.execute(q).status_code,409)
    def test_partial_selection_has_no_unselected_mirror(self):
        self.accepted(5);m,_=self.plan([self.accepted(6,'26')])
        self.assertEqual(m['result']['summary']['ordinary_mirrors'],0)
        self.assertEqual(len(m['result']['actual_changes']),1)

    def test_cn_expert_special_submission_writes_exactly_one_key_and_receipt(self):
        entry={'big':'古老斗技场','small':'十字路口','zone':'四区','tier':'高手',
               'car':'爱音','stars':3,'route':'跳图','time':'24.30','notes':'隔离测试'}
        player=self.new_client();self.addCleanup(player.close);self.signup('expert@example.com',player)
        r=player.post('/api/submissions',json={'request_key':secrets.token_hex(16),'entries':[entry]})
        self.assertEqual(r.status_code,200,r.text);sid=r.json()['ids'][0]
        r=player.post(f'/api/submissions/{sid}/submit',json={'revision':1})
        self.assertEqual(r.status_code,200,r.text)
        p=self.client.post(f'/api/admin/submissions/{sid}/preview',json={'revision':2,'entry':entry})
        self.assertEqual(p.status_code,200,p.text);p=p.json()
        self.assertIsNone(p['tier_change'])
        r=self.client.post(f'/api/admin/submissions/{sid}/review',json={
            'revision':2,'action':'accept','entry':p['candidate'],'basis':p['basis']})
        self.assertEqual(r.status_code,200,r.text)
        detail=self.client.get(f'/api/submissions/{sid}').json()
        self.assertEqual(detail['payload'],p['candidate'])
        self.assertEqual(detail['accepted_payload'],p['candidate'])
        self.assertEqual(json.loads(detail['target_key']),['古老斗技场','十字路口','四区','高手','爱音',3,'跳图'])
        self.assertEqual(detail['target_key'],identity(p['candidate']))
        m,_=self.plan([{'id':sid,'revision':3}])
        expected=('古老斗技场','十字路口','四区','高手','爱音',3,True,'跳图')
        self.assertEqual(m['result']['summary']['ordinary_mirrors'],0)
        self.assertEqual([key(c) for c in m['result']['changes']['changes']],[expected])
        self.assertEqual([key(c['target']) for c in m['result']['actual_changes']],[expected])
        self.assertEqual(key(m['result']['items'][0]['target']),expected)
        r=self.execute(m);self.assertEqual(r.status_code,200,r.text)
        snap=self.client.get('/api/scores/snapshot').json()
        self.assertEqual(snap['version'],m['target'])
        before=flatten(self.data);after=flatten(snap['data'])
        self.assertEqual(after.pop(expected),{'cars':[{'name':'爱音','stars':3}],'time':24.3,'sc':True,'sc_type':'跳图'})
        self.assertEqual(after,before)
        with self.app.state.store.connect() as db:
            receipt=db.execute('SELECT * FROM write_receipts WHERE submission_id=?',(sid,)).fetchone()
        self.assertEqual((receipt['batch_id'],receipt['state']),(m['id'],'applied'))
        saved=self.writer.detail(receipt['batch_id'])
        self.assertEqual((saved['base'],saved['target']),(self.base,snap['version']))
        self.assertEqual(key(saved['result']['items'][0]['target']),expected)
        self.assertEqual(saved['result']['items'][0]['accepted_payload'].get('server','cn'),'cn')
        self.assertFalse(saved['result']['items'][0]['accepted_payload'].get('oc',False))

    def test_legacy_starred_theory_cannot_prepare_score_write(self):
        pick=self.accepted(tier='理论')
        r=self.client.post('/api/admin/score-versions',json={'request_key':secrets.token_hex(16),'items':[pick]})
        self.assertEqual(r.status_code,409);self.assertIn('重新审核',r.json()['detail'])
        self.assertEqual(self.writer.current()[0]['id'],self.base)
        with self.app.state.store.connect() as db:
            self.assertIsNone(db.execute('SELECT * FROM write_receipts WHERE submission_id=?',(pick['id'],)).fetchone())
    def test_crash_before_commit_aborts_without_changing_pointer(self):
        m,_=self.plan();writer=self.writer
        def crash(phase):
            if phase=='apply_before_commit':raise KeyboardInterrupt()
        with patch.object(writer,'checkpoint',side_effect=crash):
            with self.assertRaises(KeyboardInterrupt):writer.execute(self.actor['id'],self.session_hash(),m['id'],Confirm(**self.confirmation(m)))
        self.assertEqual(writer.current()[0]['id'],self.base)
        r=self.client.post('/api/admin/score-versions/'+m['id']+'/recover',json={'reason':'恢复测试'})
        self.assertEqual(r.json()['state'],'aborted')
        self.assertEqual(self.client.get('/api/admin/accepted-submissions').json()['total'],1)
    def test_crash_after_commit_is_applied_on_restart(self):
        m,_=self.plan()
        def crash(phase):
            if phase=='apply_after_commit':raise KeyboardInterrupt()
        with patch.object(self.writer,'checkpoint',side_effect=crash):
            with self.assertRaises(KeyboardInterrupt):self.writer.execute(self.actor['id'],self.session_hash(),m['id'],Confirm(**self.confirmation(m)))
        fresh=create_app(self.path,score_version_lab=self.lab).state.score_versions
        self.assertEqual(fresh.detail(m['id'])['state'],'applied');self.assertEqual(fresh.current()[0]['id'],m['target'])
        self.assertEqual(self.execute(m).status_code,200)
    def test_rollback_crash_recovery_creates_new_version(self):
        m,_=self.plan();self.execute(m)
        with patch.object(self.writer,'checkpoint',side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):self.writer.rollback(self.actor['id'],self.session_hash(),m['id'],'模拟中断')
        self.assertEqual(self.writer.current()[0]['id'],m['target'])
        r=self.client.post('/api/admin/score-versions/'+m['id']+'/recover',json={'reason':'继续回滚'})
        self.assertEqual(r.status_code,200,r.text);self.assertEqual(r.json()['state'],'rolled_back')
        self.assertEqual(json.loads(self.writer.current()[1]['gauntlet_data.json']),self.data)
    def test_backup_failure_and_tampered_version_block(self):
        m,_=self.plan()
        with patch('backend.score_versions.copy_database',side_effect=OSError('disk full')):self.assertEqual(self.execute(m).status_code,409)
        self.assertEqual(self.writer.detail(m['id'])['state'],'prepared')
        p=self.writer.versions.root/m['target']/'gauntlet_data.json';p.write_text('{}')
        self.assertEqual(self.execute(m).status_code,409);self.assertEqual(self.writer.current()[0]['id'],self.base)
    def test_no_production_or_existing_database_access(self):
        with self.assertRaises(ValueError):create_app(self.path,origin='https://racepick.cn',production=True,score_version_lab=self.lab)
        with self.assertRaises(ValueError):create_app(self.seed/'other',score_version_lab=self.lab)
        with self.assertRaises(ValueError):validate_lab(Path(__file__).parents[1])
        with TestClient(create_app(self.seed/'normal')) as client:
            for path in ('/score-versions','/api/admin/score-versions','/api/scores/snapshot','/score_versions.js'):self.assertEqual(client.get(path,headers={'Host':'127.0.0.1:8000'}).status_code,404,path)
    def test_lock_prevents_parallel_apply(self):
        m,_=self.plan()
        with self.writer.versions.lock():self.assertEqual(self.execute(m).status_code,409)
        self.assertEqual(self.writer.current()[0]['id'],self.base)

    def test_new_application_instance_does_not_seed_from_code_json(self):
        m,_=self.plan();self.execute(m)
        code=self.seed/'another-app-release';code.mkdir()
        (code/'gauntlet_data.json').write_text('{"obsolete":true}')
        (code/'cars.json').write_text('{"obsolete":true}')
        with patch('backend.app.ROOT',code):
            app=create_app(self.path,score_version_lab=self.lab)
            with TestClient(app,base_url=accounts.ORIGIN) as client:
                data=client.get('/api/scores/snapshot').json()
                self.assertEqual(data['version'],m['target'])
                self.assertEqual(data['data'],self.client.get('/gauntlet_data.json').json())

    def test_session_revoked_during_backup_blocks_commit(self):
        m,_=self.plan();backup=self.writer.backup
        def revoke(*args):
            result=backup(*args)
            with self.app.state.store.connect() as db:db.execute('DELETE FROM sessions WHERE user_id=?',(self.actor['id'],))
            return result
        with patch.object(self.writer,'backup',side_effect=revoke):self.assertEqual(self.execute(m).status_code,403)
        self.assertEqual(self.writer.current()[0]['id'],self.base)

    def test_recovery_refuses_backup_corruption_then_can_resume(self):
        m,_=self.plan();self.execute(m)
        with patch.object(self.writer,'checkpoint',side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):self.writer.rollback(self.actor['id'],self.session_hash(),m['id'],'模拟中断')
        current=self.writer.detail(m['id']);folder=self.lab/'backups'/current['rollback']['backup']['folder']
        target=folder/'gauntlet_data.json';original=target.read_bytes();target.write_bytes(b'corrupt')
        url='/api/admin/score-versions/'+m['id']+'/recover'
        self.assertEqual(self.client.post(url,json={'reason':'尝试恢复'}).status_code,409)
        self.assertEqual(self.writer.detail(m['id'])['state'],'recovery_required')
        self.assertEqual(self.writer.current()[0]['id'],m['target'])
        target.write_bytes(original)
        self.assertEqual(self.client.post(url,json={'reason':'备份恢复后重试'}).json()['state'],'rolled_back')

if __name__=='__main__':unittest.main()
