"""Disposable in-process isolated HTTPS fixtures. No real account/platform/OCR calls."""
from contextlib import closing
from concurrent.futures import ThreadPoolExecutor
import threading
import hashlib
import json
import os
from pathlib import Path
import secrets
import tempfile
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs,urlsplit

from fastapi.testclient import TestClient
from backend.app import ROOT, create_app, Store
from backend.mailing import MailConfig
from backend.mini_account_isolation import provision, preflight, readonly, service_lock, backup_stopped, restore_stopped, prepare_account_stopped
from backend.mini_account_service import make_app, KIND
from backend.mini_auth import MiniError, WechatVerifier

A='/api/mini/account/v1'
ORIGIN='https://account-isolation.example.test'
PROXY={'X-Forwarded-Proto':'https','X-Real-IP':'192.0.2.8'}
PASSWORD='fixture-isolation-password-only'
SNAPSHOT=Path(os.environ.get('RACEPICK_TEST_SNAPSHOT_ROOT',ROOT.parent/'offline-evaluation/mini-ocr-gateway-release-20261104-01/RacePick-MiniOCR-Baseline-20261104-delivery-v2/snapshot'))
BINDING=ROOT/'docs/MINI_OCR_CN_BINDING_20261104.json'


class AccountServiceTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.parent=Path(self.tmp.name).resolve();self.root=self.parent/'state'
        provision(self.root,SNAPSHOT,ORIGIN,BINDING,wechat_binding=self._testMethodName.startswith("test_wechat_binding"))
        self.secret=self.parent/'platform-secret';self.secret.write_text('fixture-secret-only');self.secret.chmod(0o600)
        self.mini=self.parent/'mini.json'
        self.write(self.mini,{'kind':'racepick-mini-guests-v1','state_dir':str(self.root/'guests'),
            'appid':'wx'+'0'*16,'app_secret_file':str(self.secret),'image_policy':'disabled','account_state_dir':str(self.root/'native')})
        self.config=self.parent/'service.json'
        self.declaration={'kind':KIND,'origin':ORIGIN,'state_root':str(self.root),
                          'mini_config':str(self.mini),'enabled':True,'cloud_writes':False}
        self.write(self.config,self.declaration)
        self.platform=patch.object(WechatVerifier,'__call__',return_value='owned-fixture-platform-subject')
        self.platform.start();self.addCleanup(self.platform.stop)

    def write(self,path,data):
        path.write_text(json.dumps(data),encoding='utf-8');path.chmod(0o600)

    def client(self,writes=False,registration=False,wechat_binding=False):
        self.write(self.config,{**self.declaration,'cloud_writes':writes,'registration':registration,'wechat_binding':wechat_binding})
        app=make_app(self.config)
        client=TestClient(app,base_url=ORIGIN,client=('127.0.0.1',12000));client.__enter__()
        self.addCleanup(client.__exit__,None,None,None)
        return app,client

    def test_isolated_registration_lifecycle_and_website_identity(self):
        app,client=self.client(registration=True)
        self.assertTrue(client.get('/_account-test/health',headers=PROXY).json()['registration'])
        guest_result=client.post('/api/mini/v1/session',headers=PROXY,json={'code':'fixture-code',
            'client_schema':1,'request_key':secrets.token_hex(16)})
        self.assertEqual(guest_result.status_code,200)
        guest={**PROXY,'Authorization':'Bearer '+guest_result.json()['token']}
        email='new-player@example.test';creds={'email':email,'password':PASSWORD}
        def post(action,body,key=None):
            return client.post(A+'/auth/'+action,headers=guest,
                json={'schema':1,'request_key':key or secrets.token_hex(16),**body})
        def recover(action,key):
            return client.get(A+'/operations/'+key,params={'action':action},headers=guest)
        def mail():
            return list((self.root/'accounts/outbox').glob('*.json'))
        def token(file):
            return parse_qs(urlsplit(json.loads(file.read_bytes())['url']).fragment)['token'][0]
        key=secrets.token_hex(16)
        self.assertEqual(post('register',{**creds,'email':'player@example.com'}).status_code,400)
        self.assertEqual(post('register',{**creds,'invite_code':''}).status_code,400)
        self.assertEqual(post('register',creds,key).status_code,200)
        self.assertEqual(recover('register',key).status_code,200)
        self.assertEqual(post('register',{**creds,'email':email.upper()}).status_code,200)
        old_files=set(mail());self.assertEqual(len(old_files),1)
        self.assertEqual(post('login',creds).json()['code'],'EMAIL_NOT_VERIFIED')
        self.assertEqual(post('resend-verification',{'email':email}).status_code,429)
        expired=token(next(iter(old_files)));rejected=secrets.token_hex(16)
        with app.web.state.store.connect() as db:
            db.execute('UPDATE auth_tokens SET expires_at=0')
            db.execute('UPDATE mail_deliveries SET created_at=created_at-61')
        self.assertEqual(post('verify-email',{'token':expired},rejected).status_code,400)
        self.assertTrue(recover('verify-email',rejected).json()['operation_resolved'])
        missing=recover('verify-email',secrets.token_hex(16))
        self.assertEqual(missing.status_code,404)
        self.assertNotIn('operation_resolved',missing.json())
        # Make the unused original link live again so the next check proves
        # resend revocation independently of the expiry check above.
        with app.web.state.store.connect() as db:
            db.execute("UPDATE auth_tokens SET expires_at=strftime('%s','now')+600")
        resend=secrets.token_hex(16)
        self.assertEqual(post('resend-verification',{'email':email},resend).status_code,200)
        self.assertEqual(recover('resend-verification',resend).status_code,200)
        new_files=set(mail())-old_files;self.assertEqual(len(new_files),1)
        self.assertEqual(post('verify-email',{'token':expired}).status_code,400)
        valid=token(next(iter(new_files)));verify=secrets.token_hex(16)
        self.assertEqual(post('verify-email',{'token':valid},verify).status_code,200)
        self.assertEqual(recover('verify-email',verify).status_code,200)
        self.assertEqual(post('verify-email',{'token':valid}).status_code,400)
        self.assertEqual(post('reset-password',{'token':valid,'password':PASSWORD}).status_code,404)
        self.assertEqual(client.post('/api/auth/register',headers=PROXY,json=creds).status_code,404)
        native=post('login',creds)
        self.assertEqual(native.status_code,200)
        actor=native.json()['actor']
        self.assertEqual(actor['role'],'player');self.assertTrue(actor['verified'])
        session=client.get('/api/auth/me',headers=PROXY).json()
        web=client.post('/api/auth/login',headers={**PROXY,'Origin':ORIGIN,'X-CSRF-Token':session['csrf']},json=creds)
        self.assertEqual(web.status_code,200)
        self.assertEqual(web.json()['user'],actor)
        client.cookies.clear()
        auth={**PROXY,'Authorization':'Bearer '+native.json()['token'],'X-Account-ID':actor['id']}
        for server in ('cn','global'):
            profile=client.get(A+'/profile',params={'server':server},headers=auth)
            self.assertEqual(profile.status_code,200)
            self.assertEqual(profile.json()['revision'],0)
            self.assertIsNone(profile.json()['profile'])
        self.assertEqual(client.put(A+'/profile?server=cn',headers=auth,json={}).status_code,503)

    def test_registration_cannot_start_alongside_cloud_writes(self):
        self.write(self.config,{**self.declaration,'registration':True,'cloud_writes':True})
        with self.assertRaises(ValueError):make_app(self.config)

    def prepare_fixture(self,app):
        # Explicit local fixture setup via ORIGINAL handlers, never public registration.
        with TestClient(app.web,base_url=ORIGIN,client=('127.0.0.1',12000)) as internal:
            session=internal.get('/api/auth/me',headers=PROXY).json()
            headers={**PROXY,'Origin':ORIGIN,'X-CSRF-Token':session['csrf']}
            r=internal.post('/api/auth/register',headers=headers,json={'email':'isolated@example.test','password':PASSWORD})
            self.assertEqual(r.status_code,200,r.text)
            mail=json.loads(next((self.root/'accounts/outbox').glob('*.json')).read_bytes())
            token=parse_qs(urlsplit(mail['url']).fragment)['token'][0]
            self.assertEqual(internal.post('/api/auth/verify-email',headers=headers,json={'token':token}).status_code,200)

    def guest_login(self,client,email='isolated@example.test',code='fixture-code'):
        r=client.post('/api/mini/v1/session',headers=PROXY,json={'code':code,
            'client_schema':1,'request_key':secrets.token_hex(16)})
        self.assertEqual(r.status_code,200,r.text)
        guest={**PROXY,'Authorization':'Bearer '+r.json()['token']}
        r=client.post(A+'/auth/login',headers=guest,json={'schema':1,'request_key':secrets.token_hex(16),
            'email':email,'password':PASSWORD})
        self.assertEqual(r.status_code,200,r.text)
        return guest,{**PROXY,'Authorization':'Bearer '+r.json()['token'],'X-Account-ID':r.json()['actor']['id']}

    def test_wechat_binding_lifecycle_and_concurrent_ownership(self):
        emails=['binding-one@example.test','binding-two@example.test']
        for email in emails:
            prepare_account_stopped(self.root,email,PASSWORD)
        app,client=self.client(wechat_binding=True)
        self.assertTrue(client.get('/_account-test/health',headers=PROXY).json()['wechat_binding'])
        auth=[self.guest_login(client,email,'guest-'+str(i))[1] for i,email in enumerate(emails)]
        ids=[header['X-Account-ID'] for header in auth]
        with app.web.state.store.connect() as db:
            for uid in ids:
                db.execute('INSERT INTO profiles VALUES (?,?,?,?,?)',(uid,'["f5"]','{"f5":5}',3,1))
                db.execute('INSERT INTO profiles_global VALUES (?,?,?,?,?,?)',
                           (uid,'["ssc"]','{"ssc":6}','{"ssc":true}',4,1))

        def profiles(header):
            return [client.get(A+'/profile',params={'server':s},headers=header).json() for s in ('cn','global')]

        baseline=[profiles(header) for header in auth]
        self.assertEqual([[row['revision'] for row in p] for p in baseline],[[3,4],[3,4]])

        def change(header,action='wechat-bind',key=None,password=PASSWORD,code='new-code'):
            payload={'schema':1,'request_key':key or secrets.token_hex(16),'password':password}
            if action=='wechat-bind':payload['code']=code
            return client.post(A+'/auth/'+action,headers=header,json=payload)

        self.assertEqual(change(auth[0],password='incorrect').json()['code'],'ACCOUNT_PASSWORD_INVALID')
        barrier=threading.Barrier(2)
        def concurrent_exchange(code):
            barrier.wait(timeout=8)
            return 'owned-fixture-platform-subject'
        keys=[secrets.token_hex(16),secrets.token_hex(16)]
        with patch.object(WechatVerifier,'__call__',side_effect=concurrent_exchange):
            with ThreadPoolExecutor(max_workers=2) as pool:
                results=list(pool.map(lambda i:change(auth[i],key=keys[i],code='bind-'+str(i)),range(2)))
        self.assertEqual(sorted(r.status_code for r in results),[200,409])
        winner=next(i for i,r in enumerate(results) if r.status_code==200)
        loser=1-winner
        self.assertEqual(results[loser].json()['code'],'WECHAT_ALREADY_IN_USE')
        expected={'actor_id':ids[winner],'bound':True}
        self.assertEqual(results[winner].json(),expected)
        replay=client.get(A+'/operations/'+keys[winner],params={'action':'wechat-bind'},headers=auth[winner])
        self.assertEqual(replay.json(),expected)
        cross=client.get(A+'/operations/'+keys[winner],params={'action':'wechat-bind'},headers=auth[loser])
        self.assertEqual(cross.status_code,404)
        self.assertEqual(change(auth[winner]).json()['code'],'WECHAT_ALREADY_BOUND')
        self.assertTrue(client.get(A+'/session',headers=auth[winner]).json()['features']['wechat_binding_v1']['bound'])
        self.assertEqual(profiles(auth[winner]),baseline[winner])
        self.assertEqual(change(auth[winner],action='wechat-unbind').json(),{'actor_id':ids[winner],'bound':False})
        self.assertEqual(change(auth[winner],action='wechat-unbind').json()['code'],'WECHAT_NOT_BOUND')
        self.assertEqual(profiles(auth[winner]),baseline[winner])
        browser=TestClient(app,base_url=ORIGIN,client=('127.0.0.1',12001))
        self.addCleanup(browser.close)
        me=browser.get('/api/auth/me',headers=PROXY).json()
        login=browser.post('/api/auth/login',headers={**PROXY,'Origin':ORIGIN,'X-CSRF-Token':me['csrf']},
                           json={'email':emails[winner],'password':PASSWORD})
        self.assertEqual(login.status_code,200)
        self.assertEqual(login.json()['user']['id'],ids[winner])
        self.assertEqual(client.put(A+'/profile?server=cn',headers=auth[winner],json={}).status_code,503)

    def test_wechat_binding_rejects_invalid_identity_and_disabled_account(self):
        prepare_account_stopped(self.root,'isolated@example.test',PASSWORD)
        app,client=self.client(wechat_binding=True)
        _,auth=self.guest_login(client)
        def bind():
            return client.post(A+'/auth/wechat-bind',headers=auth,json={
                'schema':1,'request_key':secrets.token_hex(16),'password':PASSWORD,'code':'new-code'})
        with patch.object(WechatVerifier,'__call__',side_effect=MiniError(401,'PLATFORM_CODE_REJECTED','expired')):
            self.assertEqual(bind().json()['code'],'WECHAT_CODE_EXPIRED')
        with patch.object(WechatVerifier,'__call__',return_value='different-fixture-subject'):
            self.assertEqual(bind().json()['code'],'WECHAT_IDENTITY_CHANGED')
        def disabled_during_exchange(code):
            with app.web.state.store.connect() as db:
                db.execute('INSERT INTO account_controls VALUES (?,1,1,1)',(auth['X-Account-ID'],))
            return 'owned-fixture-platform-subject'
        with patch.object(WechatVerifier,'__call__',side_effect=disabled_during_exchange):
            self.assertEqual(bind().json()['code'],'ACCOUNT_DISABLED')
        self.assertEqual(bind().json()['code'],'ACCOUNT_DISABLED')
        with app.web.state.store.connect() as db:
            self.assertEqual(db.execute('SELECT count(*) FROM mini_wechat_bindings').fetchone()[0],0)

    def test_disabled_opens_no_state_or_credentials(self):
        self.write(self.config,{**self.declaration,'enabled':False,'state_root':str(self.parent/'absent')})
        with patch('backend.mini_account_service.preflight',side_effect=AssertionError('no state reads')):
            with TestClient(make_app(self.config),base_url=ORIGIN) as client:
                self.assertEqual(client.get(A+'/session').status_code,404)
                self.assertEqual(client.get('/').status_code,404)

    def test_preflight_and_startup_do_not_change_database_bytes(self):
        names=('accounts/accounts.sqlite3','guests/guests.sqlite3','native/native-accounts.sqlite3')
        before={n:hashlib.sha256((self.root/n).read_bytes()).hexdigest() for n in names}
        preflight(self.root,ORIGIN)
        app,client=self.client()
        self.assertIsNotNone(app.native)
        self.assertEqual(before,{n:hashlib.sha256((self.root/n).read_bytes()).hexdigest() for n in names})
        self.assertEqual(client.get('/',headers=PROXY).status_code,200)
        with closing(readonly(self.root/names[0])) as db:
            self.assertEqual(db.execute('SELECT count(*) FROM users').fetchone()[0],0)

    def test_old_schema_rejected_without_migration(self):
        import sqlite3
        path=self.root/'accounts/accounts.sqlite3'
        with closing(sqlite3.connect(path)) as db:
            with db:db.execute('DROP TABLE profiles_global')
        before=path.read_bytes()
        with self.assertRaises(ValueError):preflight(self.root)
        with self.assertRaises(ValueError):create_app(self.root/'accounts',ORIGIN,production=True,
            mail_config=MailConfig(),isolated_account_root=self.root)
        self.assertEqual(before,path.read_bytes())

    def test_wrong_origin_snapshot_or_mixed_paths_rejected(self):
        with self.assertRaises(ValueError):preflight(self.root,'https://other.example.test')
        with self.assertRaises(ValueError):provision(self.root,SNAPSHOT,ORIGIN,BINDING)
        target=self.root/'snapshot/cars.json';target.write_bytes(target.read_bytes()+b' ')
        with self.assertRaises(ValueError):preflight(self.root)

    def test_startup_rejects_cross_state_before_credentials(self):
        raw=json.loads(self.mini.read_bytes());raw['state_dir']=str(self.parent/'old-guests');self.write(self.mini,raw)
        app=make_app(self.config)
        with patch('backend.mini_auth.load_config',side_effect=AssertionError('must reject before credentials')):
            with self.assertRaises(ValueError):app.start()

    def test_readonly_profile_and_all_public_registration_mail_admin_closed(self):
        app,client=self.client();self.prepare_fixture(app)
        guest,auth=self.guest_login(client)
        for server in ('cn','global'):
            r=client.get(A+'/profile?server='+server,headers=auth)
            self.assertEqual(r.status_code,200,r.text);self.assertIsNone(r.json()['profile'])
            self.assertEqual(client.put(A+'/profile?server='+server,headers=auth,json={}).status_code,503)
        for path in ('/api/auth/register','/api/auth/verify-email','/api/auth/resend-verification',
                     '/api/auth/forgot-password','/api/auth/reset-password','/api/admin/accounts',
                     A+'/auth/register','/api/mini/v1/map-recognition/jobs','/api/usage/events'):
            self.assertEqual(client.post(path,headers=guest,json={}).status_code,404)
        self.assertEqual(client.get('/api/health',headers=PROXY).status_code,404)
        me=client.get('/api/auth/me',headers=PROXY).json()
        self.assertEqual(me['mail_mode'],'file');self.assertTrue(me['account_login_only'])
        self.assertFalse(me['community_controls'])

    def test_website_native_same_cn_global_record_conflicts_and_no_implicit_import(self):
        app,client=self.client(True);self.prepare_fixture(app);guest,auth=self.guest_login(client)
        browser=TestClient(app,base_url=ORIGIN,client=('127.0.0.1',12001));self.addCleanup(browser.close)
        me=browser.get('/api/auth/me',headers=PROXY).json()
        r=browser.post('/api/auth/login',headers={**PROXY,'Origin':ORIGIN,'X-CSRF-Token':me['csrf']},
            json={'email':'isolated@example.test','password':PASSWORD})
        self.assertEqual(r.status_code,200,r.text)
        web={**PROXY,'Origin':ORIGIN,'X-CSRF-Token':r.json()['csrf'],'X-Account-ID':r.json()['user']['id'],'X-Profile-Save':'explicit'}
        cookie=r.headers['set-cookie']
        self.assertIn('Secure',cookie);self.assertIn('HttpOnly',cookie);self.assertIn('SameSite=strict',cookie)
        cn=json.loads((self.root/'snapshot/cars.json').read_bytes())
        cn_car=next(c['nickname'] for c in cn['cars'] if c.get('nickname') and c.get('zones'))
        scores=json.loads((self.root/'snapshot/gauntlet_data.global.json').read_bytes())
        oc=next(e['cars'][0]['name'] for t in scores['tracks'] for e in t['五区']['理论'] if e['cars'][0].get('oc') is True)
        for server,car in (('cn',cn_car),('global',oc)):
            native_url=A+'/profile?server='+server;web_url='/api/me/profile?server='+server
            first=browser.get(web_url,headers=web).json()
            self.assertIsNone(first['profile']);self.assertEqual(first['revision'],0)
            body={'revision':0,'cars':[car],'stars':{car:6}}
            if server=='global':body['ocMap']={car:True}
            self.assertEqual(browser.put(web_url,headers=web,json=body).status_code,200)
            native=client.get(native_url,headers=auth).json()
            self.assertEqual(native['revision'],1)
            self.assertEqual(native['profile'],{k:v for k,v in body.items() if k!='revision'})
            key=secrets.token_hex(16)
            empty={'schema':1,'request_key':key,'explicit_save':True,'intent':'save','revision':1,'cars':[],'stars':{}}
            if server=='global':empty['ocMap']={}
            self.assertEqual(client.put(native_url,headers=auth,json=empty).status_code,200)
            loaded=browser.get(web_url,headers=web).json()
            self.assertEqual(loaded['revision'],2);self.assertEqual(loaded['profile']['cars'],[])
            conflict=client.put(native_url,headers=auth,json={**empty,'request_key':secrets.token_hex(16)})
            self.assertEqual(conflict.status_code,409)
            self.assertEqual(conflict.json()['current']['revision'],2)
            self.assertEqual(conflict.json()['submitted']['revision'],1)
            other='cn' if server=='global' else 'global'
            self.assertEqual(client.get(A+'/operations/'+key+'?action=profile-save&server='+other,headers=auth).status_code,409)
        # Browser Cookie cannot act as native identity; native Bearer cannot act as website Cookie.
        self.assertEqual(browser.get(A+'/session',headers=PROXY).status_code,403)
        self.assertIsNone(client.get('/api/auth/me',headers=auth).json()['user'])

    def test_snapshot_bytes_and_https_proxy_boundary(self):
        app,client=self.client()
        self.assertEqual(client.get('/').status_code,400)
        self.assertEqual(client.get('/',headers={**PROXY,'Host':'evil.example.test'}).status_code,400)
        self.assertEqual(client.get('/',headers={**PROXY,'X-Real-IP':'invalid'}).status_code,400)
        with TestClient(app.web,base_url=ORIGIN,client=('192.0.2.10',12002)) as direct:
            self.assertEqual(direct.get('/',headers=PROXY).status_code,400)
        for name in ('cars.json','gauntlet_data.json','cars.global.json','gauntlet_data.global.json','global-data-manifest.json'):
            r=client.get('/'+name,headers=PROXY)
            self.assertEqual(r.status_code,200,r.text[:80])
            self.assertEqual(r.content,(SNAPSHOT/name).read_bytes())
        health=client.get('/_account-test/health',headers=PROXY)
        self.assertEqual(health.status_code,200,health.text)
        self.assertFalse(health.json()['production_business']);self.assertFalse(health.json()['ocr_enabled'])
        self.assertEqual(health.json()['coverage_schema'],0)
        self.assertEqual(health.json()['global_score_schema'],0)

    def test_exclusive_service_and_independent_backup_restore(self):
        with service_lock(self.root):
            with self.assertRaises(ValueError):backup_stopped(self.root,self.parent/'backup-live')
        result=backup_stopped(self.root,self.parent/'backup')
        self.assertTrue(result['independent_target'])
        restore_stopped(self.parent/'backup',self.parent/'restored')
        self.assertEqual(preflight(self.parent/'restored')['schemas'],preflight(self.root)['schemas'])
        with self.assertRaises(ValueError):restore_stopped(self.parent/'backup',self.root)
        with self.assertRaises(ValueError):create_app(self.root/'accounts',ORIGIN,production=True,mail_config=MailConfig())

    def test_offline_prepare_new_account_once_and_populated_restore(self):
        result=prepare_account_stopped(self.root,'isolated@example.test',PASSWORD)
        self.assertTrue(result['verified']);self.assertFalse(result['external_mail_sent'])
        with self.assertRaises(ValueError):prepare_account_stopped(self.root,'isolated@example.test',PASSWORD)
        app,client=self.client(True);_,auth=self.guest_login(client)
        body={'schema':1,'request_key':'isolated-backup-save-key','explicit_save':True,'intent':'save',
              'revision':0,'cars':[],'stars':{},'ocMap':{}}
        self.assertEqual(client.put(A+'/profile?server=global',headers=auth,json=body).status_code,200)
        with self.assertRaises(ValueError):backup_stopped(self.root,self.parent/'live-backup')
        app.stop()
        backup_stopped(self.root,self.parent/'populated-backup')
        restore_stopped(self.parent/'populated-backup',self.parent/'populated-restored')
        restored=self.parent/'populated-restored'
        preflight(restored)
        for relative in ('accounts/accounts.sqlite3','guests/guests.sqlite3','native/native-accounts.sqlite3',
                         'guests/token.key','native/token.key'):
            self.assertEqual((self.root/relative).read_bytes(),(restored/relative).read_bytes())
        with closing(readonly(restored/'accounts/accounts.sqlite3')) as db:
            self.assertEqual(db.execute('SELECT verified FROM users').fetchone()[0],1)
            self.assertEqual(db.execute('SELECT revision FROM profiles_global').fetchone()[0],1)


if __name__=='__main__':unittest.main()
