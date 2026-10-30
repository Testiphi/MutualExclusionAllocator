import json
from pathlib import Path
import secrets
import sqlite3
import unittest
from unittest.mock import patch
from backend import test_contributions as fixtures
from backend.app import create_app
from backend.coverage import map_id
from backend.submissions import identity,packed

class ScopeMigrationTests(unittest.TestCase):
    def test_schema1_upgrade_preserves_selected_cn_map_and_event_bytes(self):
        from backend.coverage import migrate,state
        db=sqlite3.connect(':memory:');self.addCleanup(db.close);db.execute('CREATE TABLE users(id TEXT PRIMARY KEY)');db.execute("INSERT INTO users VALUES('existing')")
        migrate(db);db.execute('DROP TABLE coverage_global_choices');db.execute('UPDATE coverage_schema SET version=1')
        db.execute('INSERT INTO coverage_choices VALUES(?,?,?)',('existing',map_id('原地图'),123));snapshot='{"map_id":"old-original","rules":1}'
        db.execute('INSERT INTO coverage_events VALUES(1,?,?,?,?)',('existing','choose',snapshot,123))
        before_choices=db.execute('SELECT * FROM coverage_choices').fetchall();before_events=db.execute('SELECT * FROM coverage_events').fetchall()
        migrate(db);self.assertEqual(state(db)['coverage_schema'],2);self.assertEqual(before_choices,db.execute('SELECT * FROM coverage_choices').fetchall());self.assertEqual(before_events,db.execute('SELECT * FROM coverage_events').fetchall());self.assertEqual(db.execute('SELECT count(*) FROM coverage_global_choices').fetchone()[0],0)
    def test_orphan_international_choices_are_rejected(self):
        from backend.coverage import state
        db=sqlite3.connect(':memory:');self.addCleanup(db.close);db.execute('CREATE TABLE coverage_global_choices(id INTEGER)')
        with self.assertRaises(ValueError):state(db)

class GlobalSubmissionTests(unittest.TestCase):
    new_client=fixtures.ContributionTests.new_client
    post=fixtures.ContributionTests.post
    token=fixtures.ContributionTests.token
    signup=fixtures.ContributionTests.signup
    login=fixtures.ContributionTests.login
    tearDown=fixtures.ContributionTests.tearDown
    def setUp(self):
        fixtures.ContributionTests.setUp(self);self.client.close();self.player.close()
        self.app=create_app(self.path,score_version_lab=self.lab,contributions=True,coverage=True)
        self.client=self.new_client();self.player=self.new_client();self.login(self.client,'owner@example.com');self.login(self.player,'player@example.com')
        self.global_writer=self.app.state.global_score_versions
        _,raw=self.global_writer.current();data=json.loads(raw['gauntlet_data.global.json'])
        track=next(t for t in data['tracks'] if any(not e.get('sc') and not e['cars'][0].get('oc') for e in t['五区']['理论']))
        record=next(e for e in track['五区']['理论'] if not e.get('sc') and not e['cars'][0].get('oc'))
        self.entry={'server':'global','oc':False,'big':track['大地图'],'small':track['小地图'],'zone':'五区','tier':'理论','car':record['cars'][0]['name'],'stars':None,'route':'','time':str(round(record['time']-.001,3)),'notes':'隔离测试证据，不代表真实成绩','video_url':'','unlisted':False}
        self.cn_before=self.app.state.score_versions.current();self.global_before=self.global_writer.current();self.seed={n:(Path(__file__).parents[1]/n).read_bytes() for n in raw}
    def create(self,entry=None):
        r=self.player.post('/api/submissions',json={'request_key':secrets.token_hex(16),'entries':[entry or self.entry]});self.assertEqual(r.status_code,200,r.text);return r.json()['ids'][0]
    def accepted(self,entry=None):
        entry=entry or self.entry;sid=self.create(entry)
        r=self.player.post('/api/submissions/'+sid+'/submit',json={'revision':1});self.assertEqual(r.status_code,200,r.text)
        p=self.client.post('/api/admin/submissions/'+sid+'/preview',json={'revision':2,'entry':entry});self.assertEqual(p.status_code,200,p.text)
        r=self.client.post('/api/admin/submissions/'+sid+'/review',json={'revision':2,'action':'accept','entry':p.json()['candidate'],'basis':p.json()['basis'],'reason':'独立测试采纳','quality':{'completeness':3,'evidence':4,'value':3,'reason':'独立测试评分'}});self.assertEqual(r.status_code,200,r.text)
        return sid,r.json()['revision']
    def plan(self,entry=None):
        sid,rev=self.accepted(entry);body={'request_key':secrets.token_hex(16),'items':[{'id':sid,'revision':rev}]}
        r=self.client.post('/api/admin/score-versions?server=global',json=body);self.assertEqual(r.status_code,200,r.text);return r.json(),body
    def execute(self,m):
        r=self.client.post('/api/admin/score-versions/reauth?server=global',json={'password':fixtures.PASSWORD});self.assertEqual(r.status_code,200,r.text)
        return self.client.post('/api/admin/score-versions/'+m['id']+'/execute?server=global',json={'digest':m['digest'],'effects_confirmed':True,'items':[{'submission_id':i['submission_id'],'confirmed':True,'slower_confirmed':True,'slower_reason':'隔离测试明确接受'} for i in m['result']['items'] if i['kind']!='unchanged']})
    def test_catalog_scope_legacy_keys_and_reject_cross_server_or_future_scope(self):
        catalog=self.player.get('/api/submissions/catalog?server=global').json();self.assertEqual(catalog['capabilities']['zones'],['五区']);self.assertEqual(catalog['capabilities']['tiers'],['理论'])
        cn={**self.entry};cn.pop('server');cn.pop('oc');self.assertEqual(identity(cn),packed([cn[k] for k in ('big','small','zone','tier','car','stars','route')]))
        self.assertNotEqual(identity(cn),identity(self.entry));self.assertNotEqual(identity(self.entry),identity({**self.entry,'oc':True}))
        for change in ({'zone':'四区'},{'tier':'高手'},{'server':'bad'},{'oc':True,'route':'跳图'}):
            r=self.player.post('/api/submissions',json={'request_key':secrets.token_hex(16),'entries':[{**self.entry,**change}]});self.assertEqual(r.status_code,422,r.text)
        sid=self.create();r=self.player.put('/api/submissions/'+sid,json={'revision':1,'entry':cn});self.assertEqual(r.status_code,422)
    def test_apply_and_rollback_are_isolated_idempotent_and_refresh_bound_snapshot(self):
        m,body=self.plan();again=self.client.post('/api/admin/score-versions?server=global',json=body);self.assertEqual(again.json()['id'],m['id'])
        bad=self.client.post('/api/admin/score-versions',json={**body,'request_key':secrets.token_hex(16)});self.assertEqual(bad.status_code,409)
        r=self.execute(m);self.assertEqual(r.status_code,200,r.text);self.assertEqual(self.execute(m).status_code,200)
        snap=self.player.get('/api/scores/global-snapshot').json();self.assertEqual(snap['version'],m['target']);self.assertNotEqual(snap['files']['gauntlet_data.global.json'],self.global_before[1]['gauntlet_data.global.json'].decode())
        self.assertEqual(self.cn_before,self.app.state.score_versions.current())
        r=self.client.post('/api/admin/score-versions/'+m['id']+'/rollback?server=global',json={'reason':'测试回滚'});self.assertEqual(r.status_code,200,r.text)
        _,restored=self.global_writer.current();self.assertEqual(restored,self.global_before[1]);self.assertEqual(self.cn_before,self.app.state.score_versions.current())
        for n,b in self.seed.items():self.assertEqual((Path(__file__).parents[1]/n).read_bytes(),b)
        with self.app.state.store.connect() as db:
            row=db.execute('SELECT quality_points,bonus FROM contributions WHERE user_id=?',(self.player_user['id'],)).fetchone();self.assertEqual(tuple(row),(10,0))
    def test_global_failed_apply_aborts_and_stale_approval_cannot_execute(self):
        m,_=self.plan()
        def crash(phase):
            if phase=='apply_before_commit':raise OSError('injected crash')
        with patch.object(self.global_writer,'checkpoint',side_effect=crash):r=self.execute(m)
        self.assertEqual(r.status_code,409,r.text);self.assertEqual(self.global_writer.current(),self.global_before);self.assertEqual(self.global_writer.detail(m['id'])['state'],'aborted')
    def test_each_server_choice_and_dynamic_shared_entitlements(self):
        with self.app.state.store.connect() as db:
            for i in range(5):db.execute('INSERT INTO contributions(user_id,target_key,quality_points,bonus) VALUES(?,?,?,?)',(self.player_user['id'],'fixture-'+str(i),8,10))
        gm=self.player.get('/api/coverage?server=global').json()['maps'][0]
        self.assertEqual(self.player.post('/api/coverage/choice',json={'map_id':map_id('测试地图')}).status_code,200)
        self.assertEqual(self.player.post('/api/coverage/choice',json={'server':'global','map_id':gm['id']}).status_code,200)
        for server,chosen in [('cn',map_id('测试地图')),('global',gm['id'])]:self.assertEqual(self.player.get('/api/coverage?server='+server).json()['access']['chosen'],chosen)
        self.assertEqual(self.player.post('/api/coverage/choice',json={'server':'global','map_id':map_id('测试地图')}).status_code,422)
        with self.app.state.store.connect() as db:db.execute('UPDATE contributions SET bonus=0,quality_points=0')
        reply=self.player.get('/api/coverage?server=global').json();self.assertEqual(reply['access']['level'],0);self.assertEqual(reply['access']['chosen'],gm['id'])
    def test_oc_submission_never_compares_against_non_oc_and_cannot_cross_scope(self):
        entry={**self.entry,'oc':True};m,_=self.plan(entry);self.assertTrue(m['result']['items'][0]['target']['oc']);r=self.execute(m);self.assertEqual(r.status_code,200,r.text)
        raw=self.global_writer.current()[1];data=json.loads(raw['gauntlet_data.global.json']);track=next(t for t in data['tracks'] if t['大地图']==entry['big'] and t['小地图']==entry['small'])
        self.assertTrue(any(e['cars'][0].get('oc') and e['cars'][0]['name']==entry['car'] for e in track['五区']['理论']))
        self.assertEqual(self.cn_before,self.app.state.score_versions.current())

if __name__=='__main__':unittest.main()
