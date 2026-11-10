"""B-E contracts and role/object boundaries in newly created full-feature fixtures."""
from pathlib import Path
from unittest.mock import patch
from urllib.parse import urlsplit,parse_qs
import base64
import io
import json
import secrets
import shutil
import tempfile
import time
import unittest
from PIL import Image
from fastapi.testclient import TestClient
from backend.app import ROOT,create_app
from backend.map_recognition import RecognitionService
from backend.score_repository import provision as score_provision
from backend.mini_auth import GuestStore,provision as guest_provision
from backend.mini_accounts import AccountStore,provision as account_provision
from backend.roles import set_role

P='/api/mini/account/v1'
PASSWORD='explicit-fixture-password-123'


class MirrorTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.lab=score_provision(ROOT);self.addCleanup(lambda:shutil.rmtree(self.lab))
        # One actual score-version system and one local queue. Worker inference is not part of these fixtures.
        ref=self.lab/'reference';ref.mkdir();names=['cars.json','gauntlet_data.json','cars.global.json','gauntlet_data.global.json','global-data-manifest.json']
        import hashlib
        hashes={}
        for name in names:
            raw=(ROOT/name).read_bytes();(ref/name).write_bytes(raw);hashes[name]=hashlib.sha256(raw).hexdigest()
        (self.lab/'.racepick-map-demo.json').write_text(json.dumps({'kind':'racepick-local-map-recognition'}))
        (self.lab/'config.json').write_text(json.dumps({'root':str(self.lab),'reference':str(ref),'reference_sha256':hashes,'models':{},'vendor':'unused','examples':{}}))
        self.options={'store':GuestStore(guest_provision(self.root/'guest')),'account_store':AccountStore(account_provision(self.root/'account')),
                      'verifier':lambda code:'explicit-fixture','fixture':True,'image_policy':'private_unmoderated','mirror_fixture_writes':True}
        self.patch=patch.object(RecognitionService,'start',lambda service:None);self.patch.start();self.addCleanup(self.patch.stop)
        self.app=create_app(self.lab/'accounts','http://127.0.0.1:8050',score_version_lab=self.lab,map_recognition=self.lab/'config.json',
                            contributions=True,coverage=True,feedback=True,notifications=True,usage=True,mini_config=self.options)
        self.client=TestClient(self.app,base_url='http://127.0.0.1:8050');self.client.__enter__();self.addCleanup(lambda:self.client.__exit__(None,None,None));self.addCleanup(self.temp.cleanup)
        r=self.client.post('/api/mini/v1/session',json={'code':'fixture','client_schema':1,'request_key':'fixture-guest-session'})
        self.guest={'Authorization':'Bearer '+r.json()['token']}
        self.user('player@example.test');self.auth=self.login('player@example.test')

    def user(self,email,role='player'):
        def action(action,body):
            r=self.client.post(P+'/auth/'+action,headers=self.guest,json={'schema':1,'request_key':secrets.token_hex(16),**body});self.assertEqual(r.status_code,200,r.text)
        action('register',{'email':email,'password':PASSWORD})
        mail=next(json.loads(p.read_text('utf-8')) for p in (self.lab/'accounts/outbox').glob('*.json') if json.loads(p.read_text('utf-8'))['to']==email)
        action('verify-email',{'token':parse_qs(urlsplit(mail['url']).fragment)['token'][0]})
        if role!='player':set_role(self.lab/'accounts',email,role)

    def login(self,email):
        r=self.client.post(P+'/auth/login',headers=self.guest,json={'schema':1,'request_key':secrets.token_hex(16),'email':email,'password':PASSWORD})
        self.assertEqual(r.status_code,200,r.text);v=r.json()
        return {'Authorization':'Bearer '+v['token'],'X-Account-ID':v['actor']['id']}

    def call(self,method,path,body=None,key=None,auth=None,expected=200):
        headers=dict(self.auth if auth is None else auth)
        if method not in ('GET','HEAD') and path!='/coverage/view':headers['Idempotency-Key']=key or (body.get('request_key') if isinstance(body,dict) else None) or secrets.token_hex(16)
        r=self.client.request(method,P+path,headers=headers,**({'json':body} if body is not None else {}))
        self.assertEqual(r.status_code,expected,r.text[:1000]);return r

    def entry(self):
        data=json.loads((ROOT/'gauntlet_data.json').read_bytes())
        t=next(t for t in data['tracks'] if t['五区']['理论']);e=t['五区']['理论'][0]
        return {'server':'cn','big':t['大地图'],'small':t['小地图'],'zone':'五区','tier':'理论','car':e['cars'][0]['name'],
                'stars':None,'notes':'explicit isolated fixture evidence','route':e.get('sc_type',''),'time':str(round(e['time']-.001,3)),'oc':False}

    def draft(self):
        key=secrets.token_hex(16);body={'request_key':key,'entries':[self.entry()]}
        return self.call('POST','/submissions',body,key).json()['ids'][0]

    def test_b_public_coverage_two_servers_binding_and_private_choice(self):
        for server in ['cn','global']:
            r=self.call('GET','/coverage?server='+server,auth={}).json()
            self.assertEqual(r['source_snapshot']['server'],server);self.assertEqual(r['access']['level'],0)
            self.assertIn('rows',r);self.assertIn('capabilities',r)
        oc=self.call('GET','/coverage?server=global&oc=true',auth={}).json();self.assertTrue(oc['oc']);self.assertTrue(all(c['target'].get('oc') is True for r in oc['rows'] for c in r['cells']))
        self.call('POST','/coverage/view',{'server':'cn','zone':'五区','tier':'高手','star_map':{}},auth={})
        self.call('GET','/coverage?server=cn&server=global',auth={},expected=422)
        self.call('GET','/coverage?invented=1',auth={},expected=422)
        self.call('POST','/coverage/choice',{'server':'cn','map_id':'a'*24},auth=self.guest,expected=401)

    def test_c_draft_submit_image_owner_and_idempotency(self):
        key=secrets.token_hex(16);body={'request_key':key,'entries':[self.entry()]}
        one=self.call('POST','/submissions',body,key).json();two=self.call('POST','/submissions',body,key).json();self.assertEqual(one,two)
        recovered=self.call('GET','/feature-operations/'+key).json();self.assertEqual(recovered,one)
        sid=one['ids'][0];stream=io.BytesIO();Image.new('RGB',(640,360),'red').save(stream,format='PNG')
        img=self.call('POST','/submissions/'+sid+'/images',{'revision':1,'data':base64.b64encode(stream.getvalue()).decode()}).json()
        evidence=self.call('GET','/submissions/'+sid+'/images/'+img['id']);self.assertEqual(evidence.headers['content-type'],'image/jpeg')
        self.user('other@example.test');other=self.login('other@example.test')
        self.call('GET','/submissions/'+sid+'/images/'+img['id'],auth=other,expected=404)
        self.auth=self.login('player@example.test')
        self.call('POST','/submissions/'+sid+'/submit',{'revision':2})
        detail=self.call('GET','/submissions/'+sid).json();self.assertEqual(detail['status'],'pending')
        self.call('PUT','/contributions/preferences',{'revision':0,'nickname':'Fixture Player','anonymous':False})
        self.assertIn('items',self.call('GET','/contributions/leaderboard?period=all',auth={}).json())

    def test_d_private_feedback_admin_reply_unread_and_read_cursor(self):
        key=secrets.token_hex(16)
        ticket=self.call('POST','/feedback',{'request_key':key,'category':'bug','title':'isolated fixture','description':'explicit fixture only'},key).json()
        self.user('admin@example.test','superadmin');admin=self.login('admin@example.test')
        self.call('POST','/admin/feedback/'+ticket['id']+'/handle',{'request_key':secrets.token_hex(16),'revision':1,'message':'fixture reply','status':'resolved'},auth=admin)
        self.auth=self.login('player@example.test')
        self.call('GET','/feedback/'+ticket['id'])
        unread=self.call('GET','/notifications').json();self.assertIn('counts',unread)
        with self.app.state.store.connect() as db:
            event=db.execute("SELECT id,item_id FROM notification_events WHERE channel='feedback' AND owner_id=? ORDER BY id DESC",(self.auth['X-Account-ID'],)).fetchone()
        self.call('POST','/notifications/read',{'channel':'feedback','item_id':event['item_id'],'event_id':event['id']})
        self.assertEqual(self.call('GET','/notifications').json()['counts']['feedback'],0)

    def test_e_roles_fixture_guard_recent_auth_and_one_time_secret(self):
        self.call('GET','/admin/accounts',expected=403)
        self.user('admin@example.test','admin');admin=self.login('admin@example.test')
        self.call('GET','/submissions?scope=review',auth=admin)
        self.call('GET','/admin/accounts',auth=admin,expected=403)
        self.user('owner@example.test','superadmin');self.auth=self.login('owner@example.test')
        self.call('GET','/admin/accounts')
        key=secrets.token_hex(16);invite=self.call('POST','/admin/invitations',{'email':'invited@example.test'},key).json()
        self.assertIn('code',invite)
        replay=self.call('POST','/admin/invitations',{'email':'invited@example.test'},key,expected=409).json()
        self.assertEqual(replay['code'],'ONE_TIME_RESULT_UNRECOVERABLE')
        self.assertNotIn(invite['code'].encode(),self.options['account_store'].path.read_bytes())
        sid=self.auth['Authorization'].split('.')[1]
        with self.options['account_store'].connect() as db:db.execute('UPDATE sessions SET authenticated_at=? WHERE sid=?',(int(time.time())-601,sid))
        self.call('POST','/admin/announcements',{'title':'fixture','body':'fixture','release_label':''},expected=403)

    def test_contract_all_batches_and_disabled_writes_preserve_website_boundary(self):
        spec=self.call('GET','/contract').json();self.assertTrue(all(b in {e['batch'] for e in spec['x-native-policy']['routes']} for b in 'BCDE'))
        self.assertIn('components',spec);self.assertIn(P+'/submissions',spec['paths'])
        frozen=json.loads((ROOT/'docs/MINI_FEATURES_OPENAPI_20261103.json').read_text('utf-8'))
        self.assertEqual(spec,frozen,'Typed native schema drift must be explicitly exported/reviewed')
        self.options['mirror_fixture_writes']=False
        self.call('POST','/submissions',{'request_key':secrets.token_hex(16),'entries':[self.entry()]},expected=503)
        r=self.client.post('/api/submissions',headers=self.auth,json={'entries':[]});self.assertEqual(r.status_code,403)

    def test_write_opt_in_requires_isolated_score_lab_and_never_production(self):
        from backend.mini_features import writes_enabled
        from types import SimpleNamespace
        self.assertFalse(writes_enabled(self.options,SimpleNamespace(production=True)))
        self.assertFalse(writes_enabled(self.options,SimpleNamespace(production=False)))
        self.assertTrue(writes_enabled(self.options,self.app.state))

    def test_bad_fields_and_key_mismatch_do_not_echo_inputs_or_write(self):
        r=self.call('POST','/feedback',{'request_key':'valid-fixture-request','category':'unknown','title':'fixture-secret','description':'x'},expected=422)
        self.assertNotIn('fixture-secret',r.text)
        key=secrets.token_hex(16)
        self.call('POST','/submissions',{'request_key':key,'entries':[self.entry()]},key=secrets.token_hex(16),expected=409)

    def test_e_review_prepare_execute_and_rollback_only_in_owned_fixture(self):
        sid=self.draft();self.call('POST','/submissions/'+sid+'/submit',{'revision':1})
        self.user('owner@example.test','superadmin');self.auth=self.login('owner@example.test')
        preview=self.call('POST','/admin/submissions/'+sid+'/preview',{'revision':2,'entry':self.entry()}).json()
        accepted=self.call('POST','/admin/submissions/'+sid+'/review',{'revision':2,'action':'accept','entry':preview['candidate'],
            'basis':preview['basis'],'reason':'isolated fixture acceptance','quality':{'completeness':3,'evidence':4,'value':3,'reason':'fixture quality'}}).json()
        self.call('POST','/admin/score-versions/reauth',{'password':PASSWORD})
        key=secrets.token_hex(16)
        prepared=self.call('POST','/admin/score-versions',{'request_key':key,'items':[{'id':sid,'revision':accepted['revision']}]},key).json()
        before=self.app.state.score_versions.current()[0]['id']
        approval={'digest':prepared['digest'],'effects_confirmed':True,'items':[{'submission_id':sid,'confirmed':True,'slower_confirmed':False}]}
        applied=self.call('POST','/admin/score-versions/'+prepared['id']+'/execute',approval).json()
        self.assertEqual(applied['state'],'applied');self.assertNotEqual(self.app.state.score_versions.current()[0]['id'],before)
        rolled=self.call('POST','/admin/score-versions/'+prepared['id']+'/rollback',{'reason':'isolated fixture rollback'}).json()
        self.assertEqual(rolled['state'],'rolled_back')

    def test_b_role_matrix_retains_native_entitlements_alongside_public_web(self):
        for role in ('player','admin','superadmin'):
            email=role+'-matrix@example.test';self.user(email,role);self.auth=self.login(email)
            native=self.call('GET','/coverage?server=global').json()
            expected_level=0 if role=='player' else 2
            self.assertEqual(native['access']['level'],expected_level)
            with TestClient(self.app,base_url='http://127.0.0.1:8050') as browser:
                me=browser.get('/api/auth/me').json()
                r=browser.post('/api/auth/login',headers={'Origin':'http://127.0.0.1:8050','X-CSRF-Token':me['csrf']},json={'email':email,'password':PASSWORD})
                self.assertEqual(r.status_code,200,r.text)
                website=browser.get('/api/coverage?server=global').json()
            self.assertNotIn('access',website)
            self.assertEqual(native['user_id'],website['user_id'])
            self.assertEqual([c['car'] for c in native['columns']],[c['car'] for c in website['columns']])
            native_cells=[c for row in native['rows'] for c in row['cells']]
            web_cells=[c for row in website['rows'] for c in row['cells']]
            self.assertEqual([c['key'] for c in native_cells],[c['key'] for c in web_cells])
            self.assertTrue(all(c['value'] is not None for c in web_cells if c['status']=='filled'))
            self.assertEqual(any(c['visibility']=='locked' for c in native_cells),role=='player')
            self.assertTrue(all(n['value']==w['value'] for n,w in zip(native_cells,web_cells) if n['visibility']!='locked'))
        self.call('GET','/submissions',auth={},expected=401)
        self.call('GET','/admin/accounts',auth=self.guest,expected=401)

    def test_c_native_file_upload_retries_ignore_envelope_boundary_and_urls_are_native(self):
        sid=self.draft();stream=io.BytesIO();Image.new('RGB',(320,640),'blue').save(stream,format='PNG')
        key=secrets.token_hex(16);headers={**self.auth,'Idempotency-Key':key};path=P+'/submissions/'+sid+'/images/upload?revision=1'
        one=self.client.post(path,headers=headers,files={'image':('fixture.png',stream.getvalue(),'application/octet-stream')})
        two=self.client.post(path,headers=headers,files={'image':('other-name.png',stream.getvalue(),'image/png')})
        self.assertEqual(one.status_code,200,one.text);self.assertEqual(one.json(),two.json())
        detail=self.call('GET','/submissions/'+sid).json()
        self.assertTrue(detail['images'][0]['url'].startswith(P+'/submissions/'))
        self.call('GET',detail['images'][0]['url'][len(P):])

    def test_d_usage_token_is_signed_for_server_actor_and_events_keep_their_ids(self):
        bootstrap={'visitor_id':secrets.token_hex(16),'session_id':secrets.token_hex(16)}
        token=self.call('POST','/usage/session',bootstrap).json()['token']
        auth={**self.auth,'X-Usage-Token':token}
        event={'events':[{'id':secrets.token_hex(16),'kind':'visit','page':'home','server':'cn','reason':'open'}]}
        key=secrets.token_hex(16)
        self.assertEqual(self.call('POST','/usage/events',event,key,auth).json()['accepted'],1)
        self.assertEqual(self.call('POST','/usage/events',event,key,auth).json()['accepted'],1)
        self.assertEqual(self.call('POST','/usage/events',event,auth=auth).json()['accepted'],0)
        self.user('other-stats@example.test');other=self.login('other-stats@example.test')
        self.call('POST','/usage/events',event,auth={**other,'X-Usage-Token':token},expected=409)
