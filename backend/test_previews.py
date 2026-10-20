import hashlib
import json
from pathlib import Path
import secrets
import shutil
import tempfile
import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from backend import test_accounts as accounts
from backend.app import create_app, Store
from backend.roles import set_role
from backend.previews import build_preview

ORIGIN=accounts.ORIGIN

class PreviewTests(unittest.TestCase):
    new_client=accounts.AccountsTests.new_client
    post=accounts.AccountsTests.post
    token=accounts.AccountsTests.token
    signup=accounts.AccountsTests.signup
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();base=Path(self.temp.name);self.source=base/'formal';self.source.mkdir();self.path=base/'db'
        self.data={'_version':1,'custom':{'preserve':'unknown'},'tracks':[{'大地图':'测试地图','小地图':'测试赛道','五区':{'理论':[{'cars':[{'name':'恶魔'}],'time':20.0}],'高手':[{'cars':[{'name':'恶魔','stars':6}],'time':25.0,'custom':'keep'}],'普通':[{'cars':[{'name':'恶魔','stars':6}]}],'自动':[]},'四区':{'理论':[],'高手':[],'普通':[],'自动':[]}}]}
        (self.source/'gauntlet_data.json').write_text(json.dumps(self.data,ensure_ascii=False),encoding='utf-8')
        shutil.copy2(Path(__file__).parents[1]/'cars.json',self.source/'cars.json')
        (self.source/'gauntlet_data.xlsx').write_bytes(b'protected workbook edits')
        (self.source/'gauntlet_data_shared.xlsx').write_bytes(b'protected shared workbook')
        self.app=create_app(self.path,reference_dir=self.source,preview_source=self.source)
        self.client=self.new_client();self.actor=self.signup('admin@example.com');set_role(self.path,'admin@example.com','admin')
        self.client.cookies.clear();me=self.client.get('/api/auth/me').json();self.client.headers['X-CSRF-Token']=me['csrf']
        result=self.post('login',{'email':'admin@example.com','password':accounts.PASSWORD}).json();self.client.headers.update({'X-CSRF-Token':result['csrf'],'X-Account-ID':result['user']['id']})
    def tearDown(self):self.client.close();self.temp.cleanup()
    def accepted(self,**overrides):
        payload={'big':'测试地图','small':'测试赛道','zone':'五区','tier':'高手','car':'恶魔','stars':5,'route':'','time':'26.25','notes':'test','video_url':'','unlisted':False}|overrides
        sid=secrets.token_hex(16)
        with self.app.state.store.connect() as db:
            db.execute("INSERT INTO submissions(id,owner_id,batch_id,revision,status,payload,target_key,accepted_payload,baseline,created_at,updated_at,review_score) VALUES (?,?,?,2,'accepted',?,?,?,?,1,1,0)",(sid,self.actor['id'],secrets.token_hex(16),json.dumps(payload),None,json.dumps(payload),json.dumps({'data':'old','cars':'old'})))
        return {'id':sid,'revision':2}
    def make(self,picks,key=None):
        response=self.client.post('/api/admin/previews',json={'request_key':key or secrets.token_hex(16),'items':picks})
        self.assertEqual(response.status_code,200,response.text)
        bid=response.json()['id'];return bid,self.client.get('/api/admin/previews/'+bid).json()
    def files(self):return {p.name:(hashlib.sha256(p.read_bytes()).hexdigest(),p.stat().st_mtime_ns) for p in self.source.iterdir()}
    def test_new_expert_mirror_source_unchanged_and_exports_unapproved(self):
        before=self.files();pick=self.accepted()
        with patch('data_tools.atomic_write',side_effect=AssertionError('write prohibited')),patch('apply_changes.atomic_write',side_effect=AssertionError('write prohibited')):
            bid,result=self.make([pick])
        self.assertEqual(self.files(),before);self.assertEqual(result['state'],'ready')
        self.assertEqual(result['summary']['new'],1);self.assertEqual(result['summary']['ordinary_mirrors'],1)
        self.assertEqual(len(result['actual_changes']),2);self.assertTrue(result['items'][0]['review_basis_changed'])
        report=self.client.get(f'/api/admin/previews/{bid}/download?kind=changes')
        self.assertEqual(report.status_code,200);self.assertEqual(hashlib.sha256(report.content).hexdigest(),result['changes_sha256'])
        changes=report.json();self.assertFalse(changes['write_authorized']);self.assertTrue(all(c['accepted'] is False for c in changes['changes']))
        preview=self.client.get(f'/api/admin/previews/{bid}/download?kind=preview')
        self.assertEqual(hashlib.sha256(preview.content).hexdigest(),result['preview_sha256'])
        data=preview.json();self.assertEqual(data['custom'],self.data['custom']);self.assertEqual(data['tracks'][0]['五区']['高手'][0]['custom'],'keep')
        self.assertEqual(self.client.post(f'/api/admin/previews/{bid}/apply',json={}).status_code,404)
        with self.app.state.store.connect() as db:self.assertEqual(db.execute('SELECT status,revision FROM submissions WHERE id=?',(pick['id'],)).fetchone()['status'],'accepted')
    def test_slower_faster_and_unchanged_do_not_conflate(self):
        _,slow=self.make([self.accepted(stars=6,time='25.5')]);self.assertEqual(slow['summary']['slower'],1);self.assertEqual(slow['summary']['updated'],1);self.assertEqual(slow['summary']['ordinary_mirrors'],0)
        _,fast=self.make([self.accepted(stars=6,time='24.5')]);self.assertEqual(fast['summary']['faster'],1)
        _,same=self.make([self.accepted(stars=6,time='25.000')]);self.assertEqual(same['summary']['unchanged'],1);self.assertEqual(same['changes']['changes'],[]);self.assertEqual(same['actual_changes'],[])
    def test_theory_and_sc_additions_never_create_normal_mirrors(self):
        _,result=self.make([self.accepted(tier='理论',stars=None,time='19'),self.accepted(stars=5,route='滑栏杆')])
        self.assertEqual(result['state'],'ready');self.assertEqual(result['summary']['ordinary_mirrors'],0)
        self.assertEqual(len(result['actual_changes']),2)
    def test_explicit_normal_and_derived_mirror_are_counted_once(self):
        _,result=self.make([self.accepted(),self.accepted(tier='普通')])
        self.assertEqual(result['state'],'ready');self.assertEqual(len(result['actual_changes']),2)
        self.assertEqual(result['summary']['ordinary_mirrors'],0)
        normal=next(e for e in result['actual_changes'] if e['target']['tier']=='普通')
        self.assertEqual(normal['new'],'✓');self.assertEqual(len(normal['mirror_contributors']),1)
        self.assertNotIn('time',normal['after_entry'])
    def test_placeholder_and_auto_availability(self):
        self.data['tracks'][0]['五区']['理论'].append({'cars':[{'name':'恶魔','stars':5}]})
        (self.source/'gauntlet_data.json').write_text(json.dumps(self.data),encoding='utf-8')
        _,result=self.make([self.accepted(tier='理论'),self.accepted(tier='自动')])
        self.assertEqual(result['summary']['placeholder'],1);self.assertEqual(result['summary']['new'],1)
        auto=next(e for e in result['actual_changes'] if e['target']['tier']=='自动')
        self.assertEqual(auto['new'],'✓');self.assertNotIn('time',auto['after_entry'])
    def test_bad_rules_and_duplicate_targets_block_whole_preview(self):
        bid,result=self.make([self.accepted(zone='四区',stars=6)])
        self.assertEqual(result['state'],'blocked');self.assertEqual(result['summary']['conflicts'],1)
        self.assertEqual(self.client.get(f'/api/admin/previews/{bid}/download?kind=preview').status_code,409)
        _,duplicates=self.make([self.accepted(),self.accepted(time='26.1')])
        self.assertEqual(duplicates['state'],'blocked');self.assertEqual(duplicates['summary']['conflicts'],2);self.assertEqual(duplicates['summary']['new'],0)
    def test_source_or_approval_change_invalidates_saved_preview(self):
        pick=self.accepted();bid,_=self.make([pick])
        with (self.source/'cars.json').open('a') as file:file.write('\n')
        stale=self.client.get('/api/admin/previews/'+bid).json();self.assertEqual(stale['state'],'stale')
        for kind in ['changes','preview','manifest']:self.assertEqual(self.client.get(f'/api/admin/previews/{bid}/download?kind={kind}').status_code,409)
        bid,_=self.make([pick])
        with self.app.state.store.connect() as db:db.execute("UPDATE submissions SET status='pending',revision=3 WHERE id=?",(pick['id'],))
        self.assertEqual(self.client.get('/api/admin/previews/'+bid).json()['state'],'stale')
    def test_mutation_during_generation_does_not_save_partial_preview(self):
        pick=self.accepted()
        def mutate(*args):
            result=build_preview(*args)
            with (self.source/'gauntlet_data.json').open('a') as file:file.write('\n')
            return result
        with patch('backend.previews.build_preview',side_effect=mutate):
            r=self.client.post('/api/admin/previews',json={'request_key':secrets.token_hex(16),'items':[pick]})
        self.assertEqual(r.status_code,409)
        with self.app.state.store.connect() as db:self.assertEqual(db.execute('SELECT count(*) FROM preview_batches').fetchone()[0],0)
    def test_changed_review_during_generation_is_rejected(self):
        pick=self.accepted()
        def mutate(*args):
            result=build_preview(*args)
            with self.app.state.store.connect() as db:db.execute('UPDATE submissions SET revision=3 WHERE id=?',(pick['id'],))
            return result
        with patch('backend.previews.build_preview',side_effect=mutate):
            r=self.client.post('/api/admin/previews',json={'request_key':secrets.token_hex(16),'items':[pick]})
        self.assertEqual(r.status_code,409)
    def test_idempotent_generation_and_revision_validation(self):
        pick=self.accepted();key=secrets.token_hex(16);a,_=self.make([pick],key);b,_=self.make([pick],key);self.assertEqual(a,b)
        self.assertEqual(self.client.post('/api/admin/previews',json={'request_key':secrets.token_hex(16),'items':[pick,pick]}).status_code,422)
        self.assertEqual(self.client.post('/api/admin/previews',json={'request_key':key,'items':[dict(pick,revision=1)]}).status_code,409)
    def test_permissions_path_injection_no_source_and_engine_change(self):
        other=self.new_client();self.signup('player@example.com',other)
        self.assertEqual(other.get('/api/admin/accepted-submissions').status_code,403)
        self.assertEqual(other.get('/api/admin/preview-source').status_code,403);other.close()
        pick=self.accepted();body={'request_key':secrets.token_hex(16),'items':[pick]}
        self.assertEqual(self.client.post('/api/admin/previews',json={**body,'source':'C:/'}).status_code,422)
        self.assertEqual(self.client.post('/api/admin/previews',json=body,headers={'X-CSRF-Token':'bad'}).status_code,403)
        with patch('backend.previews.engine_hashes',return_value={'different':'hash'}):self.assertEqual(self.client.post('/api/admin/previews',json=body).status_code,409)
        app=create_app(self.path,reference_dir=self.source)
        with TestClient(app,base_url=ORIGIN) as client:
            client.cookies.update(self.client.cookies);client.headers.update(self.client.headers)
            self.assertFalse(client.get('/api/admin/preview-source').json()['configured'])
            self.assertEqual(client.post('/api/admin/previews',json=body).status_code,503)
    def test_different_formal_maintenance_tool_blocks_preview(self):
        (self.source/'apply_changes.py').write_text('different maintenance version',encoding='utf-8')
        response=self.client.post('/api/admin/previews',json={'request_key':secrets.token_hex(16),'items':[self.accepted()]})
        self.assertEqual(response.status_code,409)
        with self.app.state.store.connect() as db:self.assertEqual(db.execute('SELECT count(*) FROM preview_batches').fetchone()[0],0)

    def test_invalid_source_and_migration_preserve_existing_data(self):
        self.data['tracks'][0]['五区']['普通']=[]
        (self.source/'gauntlet_data.json').write_text(json.dumps(self.data),encoding='utf-8')
        bid,result=self.make([self.accepted()]);self.assertEqual(result['state'],'blocked');self.assertTrue(result['errors'])
        with self.app.state.store.connect() as db:
            before=[tuple(r) for r in db.execute('SELECT * FROM users')]
            db.execute('DROP TABLE preview_batches');db.execute('DELETE FROM schema_version WHERE version=6')
        migrated=Store(self.path)
        with migrated.connect() as db:
            self.assertEqual(db.execute('SELECT max(version) FROM schema_version').fetchone()[0],6)
            self.assertEqual(before,[tuple(r) for r in db.execute('SELECT * FROM users')])
            self.assertEqual(db.execute('PRAGMA foreign_key_check').fetchall(),[])

if __name__=='__main__':unittest.main()
