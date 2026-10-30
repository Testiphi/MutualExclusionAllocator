import copy
import json
import unittest
from unittest.mock import patch
from backend.coverage import matrix,map_id,state
from backend.app import create_app
from backend import test_contributions as fixtures

def sample():
    catalog={'cars':[{'nickname':'a','title':'Car A','zones':['五区','四区'],'star_rule':{'min':1,'max':6,'zone4Max':4}},
                     {'nickname':'b','title':'Car B','zones':['五区'],'star_rule':{'min':1,'max':6}}]}
    track=lambda big:{'大地图':big,'小地图':'道路','五区':{'理论':[{'cars':[{'name':'a'}],'time':25},{'cars':[{'name':'b'}],'time':27},{'cars':[{'name':'b','oc':True}],'time':23},{'cars':[{'name':'a'}],'time':20,'sc':True,'sc_type':'跳图'}],
        '高手':[{'cars':[{'name':'a','stars':5}],'time':26}],'普通':[],'自动':[]},'四区':{'理论':[],'高手':[]}}
    return {'tracks':[track('甲地图'),track('乙地图'),track('丙地图')]},catalog

class CoverageMatrixTests(unittest.TestCase):
    def test_fixed_sample_columns_cover_maps_without_exposing_whole_rows(self):
        data,cars=sample();access={'level':0,'chosen':None}
        result=matrix(data,cars,access)
        self.assertEqual([c['value'] for c in result['rows'][0]['cells']],[25,None])
        self.assertEqual([c['value'] for c in result['rows'][2]['cells']],[25,None])
        self.assertNotIn('reference',result['rows'][0])
        filtered=matrix(data,cars,access,big=map_id('丙地图'),query='b')
        self.assertIsNone(filtered['rows'][0]['cells'][0]['value'])
        special=matrix(data,cars,access,route='special');self.assertEqual(special['rows'][0]['cells'][0]['value'],20)
        self.assertEqual(special['rows'][2]['cells'][0]['value'],20)
    def test_scope_and_one_column_per_car_with_bounded_star_selection(self):
        data,cars=sample();access={'level':1,'chosen':map_id('丙地图')}
        data['tracks'][0]['五区']['高手'].append({'cars':[{'name':'a','stars':6}],'time':24})
        result=matrix(data,cars,access);self.assertEqual(result['rows'][2]['cells'][1]['value'],27)
        zone4=matrix(data,cars,access,zone='四区',tier='高手');self.assertEqual([c['stars'] for c in zone4['columns']],[4]);self.assertEqual(zone4['columns'][0]['star_options'],[1,2,3,4])
        expert=matrix(data,cars,{'level':0,'chosen':None},tier='高手',star_map={'a':5})
        self.assertEqual(len(expert['columns']),2);self.assertEqual(expert['columns'][0]['stars'],5);self.assertEqual(expert['rows'][0]['cells'][0]['value'],26)
        self.assertEqual(expert['rows'][0]['cells'][0]['target']['stars'],5);self.assertEqual(expert['rows'][2]['cells'][0]['value'],26)
        with self.assertRaises(Exception):matrix(data,cars,access,zone='四区',tier='高手',star_map={'a':5})
        cars['capabilities']={'zones':['五区'],'tiers':['理论'],'max_stars_only':True,'oc':True}
        global_view=matrix(data,cars,{'level':2,'chosen':None},server='global');self.assertEqual(global_view['rows'][0]['cells'][0]['target']['server'],'global')
    def test_coverage_sort_uses_unique_tracks_and_does_not_move_when_stars_change(self):
        data,cars=sample();data['tracks'][2]['五区']['理论']=[e for e in data['tracks'][2]['五区']['理论'] if e['cars'][0]['name']!='a']
        result=matrix(data,cars,{'level':0,'chosen':None});self.assertEqual(result['columns'][0]['car'],'b')
        self.assertEqual(result['columns'][0]['coverage_count'],3)
        five=matrix(data,cars,{'level':0,'chosen':None},tier='高手',star_map={'a':5})
        six=matrix(data,cars,{'level':0,'chosen':None},tier='高手',star_map={'a':6})
        self.assertEqual([c['car'] for c in five['columns']],[c['car'] for c in six['columns']])
        self.assertEqual([c['car'] for c in five['columns'] if c['public']],[c['car'] for c in six['columns'] if c['public']])

    def test_complementary_columns_are_fixed_before_search_and_map_filters(self):
        data,cars=sample();cars['cars'].append({**cars['cars'][1],'nickname':'c','title':'Car C'})
        for i,t in enumerate(data['tracks']):
            t['五区']['理论']=[{'cars':[{'name':name}],'time':25+n} for n,name in enumerate(('a','c') if i<2 else ('b','c'))]
        # c covers every map, so one full reference column suffices; a/b remain locked.
        result=matrix(data,cars,{'level':0,'chosen':None})
        self.assertEqual([c['car'] for c in result['columns'] if c['public']],['c'])
        self.assertTrue(all(any(c['value'] is not None for c in r['cells']) for r in result['rows']))
        self.assertTrue(all(c['value'] is None for r in result['rows'] for c in r['cells'] if not c['public']))
        hidden=matrix(data,cars,{'level':0,'chosen':None},query='Car A',big=map_id('甲地图'))
        self.assertFalse(hidden['columns'][0]['public']);self.assertIsNone(hidden['rows'][0]['cells'][0]['value'])
        # Losing c's last-row record needs a complementary second column, without exposing a whole row.
        data['tracks'][2]['五区']['理论']=[{'cars':[{'name':'b'}],'time':27}]
        result=matrix(data,cars,{'level':0,'chosen':None})
        self.assertEqual({c['car'] for c in result['columns'] if c['public']},{'a','b'})
        self.assertTrue(all(c['value'] is None for r in result['rows'] for c in r['cells'] if not c['public']))

    def test_explicit_maximum_theory_star_and_pagination(self):
        data,cars=sample();data['tracks'][0]['五区']['理论'][0]['cars'][0]['stars']=6
        result=matrix(data,cars,{'level':0,'chosen':None});self.assertEqual(result['rows'][0]['cells'][0]['value'],25)
        data['tracks'][0]['五区']['理论'].append({'cars':[{'name':'a'}],'time':25})
        self.assertEqual(matrix(data,cars,{'level':0,'chosen':None})['rows'][0]['cells'][0]['value'],25)
        many=copy.deepcopy(cars['cars'][0]);cars['cars']=[{**many,'nickname':'x'+str(i),'title':'X'+str(i)} for i in range(60)]
        self.assertEqual(len(matrix(data,cars,{'level':0,'chosen':None})['columns']),48)
        result=matrix(data,cars,{'level':0,'chosen':None},offset=48);self.assertEqual(len(result['columns']),12);self.assertEqual(result['column_total'],60)
        first=matrix(data,cars,{'level':0,'chosen':None})['columns']
        self.assertFalse({c['car'] for c in first}&{c['car'] for c in result['columns']})
        self.assertEqual(len({c['car'] for c in first+result['columns']}),60)
        last=matrix(data,cars,{'level':0,'chosen':None},offset=240);self.assertEqual(last['column_offset'],48);self.assertEqual(len(last['columns']),12)

class CoverageAPITests(unittest.TestCase):
    new_client=fixtures.ContributionTests.new_client
    post=fixtures.ContributionTests.post
    token=fixtures.ContributionTests.token
    signup=fixtures.ContributionTests.signup
    login=fixtures.ContributionTests.login
    submission=fixtures.ContributionTests.submission
    detail=fixtures.ContributionTests.detail
    review=fixtures.ContributionTests.review
    tearDown=fixtures.ContributionTests.tearDown
    def setUp(self):
        fixtures.ContributionTests.setUp(self);self.client.close();self.player.close()
        self.samples=patch('backend.coverage.public_columns',return_value=set());self.samples.start();self.addCleanup(self.samples.stop)
        self.app=create_app(self.path,score_version_lab=self.lab,contributions=True,coverage=True)
        self.client=self.new_client();self.player=self.new_client();self.login(self.client,'owner@example.com');self.login(self.player,'player@example.com')
    def grant_fixture(self,count=5,high=0):
        uid=self.player_user['id']
        with self.app.state.store.connect() as db:
            db.execute('DELETE FROM contributions WHERE user_id=?',(uid,))
            for i in range(count):db.execute('INSERT INTO contributions(user_id,target_key,quality_points,bonus) VALUES(?,?,?,?)',(uid,'fixture'+str(i),8 if i<high else 6,10))
    def test_readonly_view_post_validates_csrf_and_star_overrides_without_saving_garage(self):
        body={'tier':'高手','q':'恶魔','star_map':{'恶魔':5}}
        self.assertEqual(self.player.post('/api/coverage/view',json=body,headers={'X-CSRF-Token':'bad'}).status_code,403)
        with self.app.state.store.connect() as db:before=db.execute('SELECT count(*) FROM profiles').fetchone()[0]
        result=self.player.post('/api/coverage/view',json=body);self.assertEqual(result.status_code,200,result.text)
        self.assertEqual(result.json()['columns'][0]['stars'],5)
        self.assertEqual(len(result.json()['columns']),1)
        with self.app.state.store.connect() as db:self.assertEqual(db.execute('SELECT count(*) FROM profiles').fetchone()[0],before)
        self.assertEqual(self.player.post('/api/coverage/view',json={'zone':'四区','tier':'高手','star_map':{'恶魔':6}}).status_code,422)

    def test_homepage_has_public_entry_for_each_server(self):
        self.assertIn('href="/score-table"',self.player.get('/').text)
        self.assertIn('href="/score-table?server=global"',self.player.get('/?server=global').text)

    def test_choice_requires_real_ledger_csrf_identity_and_is_idempotent(self):
        url='/api/coverage/choice';body={'map_id':map_id('测试地图')}
        self.assertEqual(self.player.post(url,json=body).status_code,409)
        self.grant_fixture();self.assertEqual(self.player.post(url,json=body,headers={'X-CSRF-Token':'bad'}).status_code,403)
        self.assertEqual(self.player.post(url,json=body,headers={'X-Account-ID':self.owner['id']}).status_code,401)
        self.assertEqual(self.player.post(url,json={'map_id':'a'*24}).status_code,422)
        self.assertEqual(self.player.post(url,json=body).status_code,200);self.assertEqual(self.player.post(url,json=body).status_code,200)
        with self.app.state.store.connect() as db:self.assertEqual(state(db)['coverage_counts']['coverage_events'],1)
        self.assertEqual(self.player.get('/api/coverage').json()['access']['chosen'],body['map_id'])
    def test_ledger_reduction_removes_access_without_deleting_choice_and_new_schema_cannot_be_omitted(self):
        self.grant_fixture();self.player.post('/api/coverage/choice',json={'map_id':map_id('测试地图')})
        reply=self.player.get('/api/coverage',params={'tier':'高手','stars':'6'}).json();cell=next(c for c in reply['rows'][0]['cells'] if c['status']=='filled');self.assertEqual(cell['value'],25)
        with self.app.state.store.connect() as db:db.execute('UPDATE contributions SET quality_points=0,bonus=0')
        reply=self.player.get('/api/coverage',params={'tier':'高手','stars':'6'}).json();self.assertEqual(reply['access']['level'],0);self.assertTrue(reply['access']['chosen']);self.assertTrue(all(c['value'] is None for c in reply['rows'][0]['cells']))
        with self.assertRaises(ValueError):create_app(self.path,score_version_lab=self.lab,contributions=True)
    def test_full_level_is_dynamic_admins_work_independently_and_unlocks_both_servers(self):
        self.grant_fixture(15,5);self.assertEqual(self.player.get('/api/coverage').json()['access']['level'],2)
        self.assertTrue(self.client.get('/api/coverage').json()['access']['admin'])
        r=self.player.get('/api/coverage?server=global').json();self.assertEqual(r['server'],'global');self.assertTrue(all(c['value'] is not None for row in r['rows'] for c in row['cells'] if c['status']=='filled'))
        self.assertEqual(self.player.get('/api/coverage?server=global&zone=四区').status_code,422)
    def test_existing_submission_chain_accepts_prefill_and_pending_is_private_without_filling_cell(self):
        reply=self.player.get('/api/coverage',params={'tier':'高手','stars':'5','q':'恶魔'}).json();cell=reply['rows'][0]['cells'][0];self.assertEqual(cell['status'],'empty')
        entry={**cell['target'],'time':'26.125','notes':'真实流程的独立临时库测试','video_url':'','unlisted':False}
        result=self.player.post('/api/submissions',json={'request_key':'coverage-test-0001','entries':[entry]});self.assertEqual(result.status_code,200,result.text);sid=result.json()['ids'][0]
        self.assertEqual(self.player.post('/api/submissions/'+sid+'/submit',json={'revision':1}).status_code,200)
        after=self.player.get('/api/coverage',params={'tier':'高手','stars':'5','q':'恶魔'}).json()['rows'][0]['cells'][0];self.assertEqual(after['status'],'empty');self.assertEqual(after['mine']['status'],'pending')
        owner=self.client.get('/api/coverage',params={'tier':'高手','stars':'5','q':'恶魔'}).json()['rows'][0]['cells'][0];self.assertNotIn('mine',owner)
        self.assertEqual(self.player.get('/api/coverage').json()['access']['points'],0)
    def test_disabled_user_rejected_and_responses_are_not_shared_cached(self):
        r=self.player.get('/api/coverage');self.assertIn('no-store',r.headers['cache-control']);self.assertEqual(r.headers['vary'],'Cookie')
        self.client.post('/api/admin/accounts/'+self.player_user['id']+'/control',json={'revision':0,'action':'disable','reason':'测试停用'})
        # Account control invalidates sessions. Public browsing can continue, with no account rights.
        after=self.player.get('/api/coverage');self.assertEqual(after.status_code,200);self.assertIsNone(after.json()['user_id']);self.assertEqual(after.json()['access']['level'],0)
