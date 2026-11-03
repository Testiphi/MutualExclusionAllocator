"""Batch A only: new disposable accounts/outbox/native state; no SMTP/platform/production."""
from pathlib import Path
from urllib.parse import parse_qs,urlsplit
from unittest.mock import Mock
import json
import secrets
import tempfile
import time
import unittest
from fastapi.testclient import TestClient
from backend.app import create_app
from backend.mini_auth import GuestStore,provision as guest_provision
from backend.mini_accounts import AccountStore,provision as account_provision
from backend.roles import set_role

P='/api/mini/account/v1'
PASSWORD='fixture-only-password-1234'


class NativeAccountTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.guests=GuestStore(guest_provision(self.root/'guest'))
        self.accounts=AccountStore(account_provision(self.root/'native-account'))
        options={'store':self.guests,'account_store':self.accounts,'verifier':lambda code:'explicit-fixture-'+code,
                 'fixture':True,'image_policy':'disabled'}
        self.app=create_app(self.root/'website','http://127.0.0.1:8044',mini_config=options)
        self.client=TestClient(self.app,base_url='http://127.0.0.1:8044',client=('127.0.0.1',12345));self.client.__enter__()
        r=self.client.post('/api/mini/v1/session',json={'code':'fixture-code','client_schema':1,'request_key':'fixture-session-key'})
        self.assertEqual(r.status_code,200,r.text)
        self.guest={'Authorization':'Bearer '+r.json()['token']}

    def tearDown(self):
        self.client.__exit__(None,None,None);self.temp.cleanup()

    def action(self,name,fields=None,auth=None,key=None):
        return self.client.post(P+'/auth/'+name,json={'schema':1,'request_key':key or secrets.token_hex(16),**(fields or {})},headers=auth or self.guest)

    def mail_token(self,email,purpose):
        for path in sorted((self.root/'website/outbox').glob('*.json'),reverse=True):
            value=json.loads(path.read_text('utf-8'))
            if value['to']==email and value['purpose']==purpose:return parse_qs(urlsplit(value['url']).fragment)['token'][0]
        raise AssertionError('fixture mailbox token missing')

    def register(self,email='alice@example.test',password=PASSWORD,verify=True):
        r=self.action('register',{'email':email,'password':password});self.assertEqual(r.status_code,200,r.text)
        if verify:
            token=self.mail_token(email,'verify')
            r=self.action('verify-email',{'token':token});self.assertEqual(r.status_code,200,r.text)
        return email

    def login(self,email='alice@example.test',password=PASSWORD,key=None):
        r=self.action('login',{'email':email,'password':password},key=key);self.assertEqual(r.status_code,200,r.text)
        value=r.json()
        return value,{'Authorization':'Bearer '+value['token'],'X-Account-ID':value['actor']['id']}

    def save(self,auth,revision=0,cars=None,stars=None,key=None,**extra):
        return self.client.put(P+'/profile?server=cn',headers=auth,json={'schema':1,'request_key':key or secrets.token_hex(16),
            'explicit_save':True,'intent':'save','revision':revision,'cars':cars or [],'stars':stars or {},**extra})

    def test_guest_does_not_become_website_account_and_tokens_are_not_interchangeable(self):
        r=self.client.get(P+'/session',headers=self.guest)
        self.assertIsNone(r.json()['actor']);self.assertEqual(r.json()['session_kind'],'wechat_guest')
        self.assertEqual(self.client.get(P+'/profile?server=cn',headers=self.guest).status_code,401)
        with self.app.state.store.connect() as db:self.assertEqual(db.execute('SELECT count(*) FROM users').fetchone()[0],0)
        self.register();value,auth=self.login()
        self.assertEqual(self.client.get('/api/mini/v1/snapshot?server=cn',headers=auth).status_code,401)
        self.assertEqual(self.client.get('/api/me/profile',headers=auth).status_code,401)
        self.assertFalse(value['association']['persistent_binding'])
        self.assertFalse(value['high_privilege_writes_ready'])

    def test_registration_verification_resend_and_reset_reuse_website_tokens(self):
        self.register(verify=False)
        self.assertEqual(self.action('login',{'email':'alice@example.test','password':PASSWORD}).status_code,403)
        old=self.mail_token('alice@example.test','verify')
        self.assertEqual(self.action('resend-verification',{'email':'alice@example.test'}).status_code,200)
        self.assertEqual(self.action('verify-email',{'token':old}).status_code,400)
        self.assertEqual(self.action('verify-email',{'token':self.mail_token('alice@example.test','verify')}).status_code,200)
        value,auth=self.login()
        self.assertEqual(self.action('forgot-password',{'email':'alice@example.test'}).status_code,200)
        token=self.mail_token('alice@example.test','reset')
        self.assertEqual(self.action('reset-password',{'token':token,'password':PASSWORD+'new'}).status_code,200)
        self.assertEqual(self.client.get(P+'/session',headers=auth).status_code,401)
        self.login(password=PASSWORD+'new')

    def test_login_recovery_same_token_no_cookie_and_no_password_or_token_in_native_db(self):
        self.register();wrapped=Mock(wraps=self.app.state.native_accounts.handlers['login'])
        self.app.state.native_accounts.handlers['login']=wrapped
        key='fixture-login-recovery'
        first=self.action('login',{'email':'alice@example.test','password':PASSWORD},key=key)
        second=self.action('login',{'email':'alice@example.test','password':PASSWORD},key=key)
        self.assertEqual(first.status_code,200,first.text);self.assertEqual(first.json()['token'],second.json()['token'])
        self.assertEqual(wrapped.call_count,1);self.assertNotIn('set-cookie',first.headers)
        recovered=self.client.get(P+'/operations/'+key+'?action=login',headers=self.guest)
        self.assertEqual(recovered.json()['token'],first.json()['token'])
        data=self.accounts.path.read_bytes()
        self.assertNotIn(PASSWORD.encode(),data);self.assertNotIn(first.json()['token'].encode(),data)
        self.assertNotIn('csrf',first.json())

    def test_same_operation_key_cannot_change_body_or_send_mail_twice(self):
        key='fixture-register-retry'
        fields={'email':'alice@example.test','password':PASSWORD}
        self.assertEqual(self.action('register',fields,key=key).status_code,200)
        self.assertEqual(self.action('register',fields,key=key).status_code,200)
        self.assertEqual(len(list((self.root/'website/outbox').glob('*.json'))),1)
        self.assertEqual(self.action('register',{**fields,'password':PASSWORD+'new'},key=key).status_code,409)

    def test_role_fields_cannot_be_client_declared(self):
        r=self.action('register',{'email':'alice@example.test','password':PASSWORD,'role':'superadmin'})
        self.assertEqual(r.status_code,400);self.assertNotIn(PASSWORD,r.text)
        with self.app.state.store.connect() as db:self.assertEqual(db.execute('SELECT count(*) FROM users').fetchone()[0],0)

    def test_profile_revision_conflict_empty_garage_and_explicit_import(self):
        self.register();value,auth=self.login()
        self.assertIsNone(self.client.get(P+'/profile?server=cn',headers=auth).json()['profile'])
        self.assertEqual(self.save(auth,explicit_save=False).status_code,409)
        self.assertEqual(self.save(auth,intent='import_guest').status_code,409)
        r=self.save(auth,intent='import_guest',confirm_guest_import=True)
        self.assertEqual(r.status_code,200,r.text)
        remote=self.client.get(P+'/profile?server=cn',headers=auth).json()
        self.assertEqual(remote['profile'],{'cars':[],'stars':{}});self.assertEqual(remote['revision'],1)
        conflict=self.save(auth,0)
        self.assertEqual(conflict.status_code,409,conflict.text)
        self.assertEqual(conflict.json()['current']['revision'],1)
        self.assertEqual(conflict.json()['submitted']['revision'],0)
        self.assertEqual(self.save(auth,1).json()['revision'],2)

    def test_profile_response_loss_idempotence_and_cross_actor_rejection(self):
        self.register();value,auth=self.login();key='fixture-profile-retry'
        self.assertEqual(self.save(auth,key=key).json()['revision'],1)
        self.assertEqual(self.save(auth,key=key).json()['revision'],1)
        self.assertEqual(self.client.get(P+'/profile?server=cn',headers={**auth,'X-Account-ID':'other'}).status_code,401)
        self.assertEqual(self.client.get(P+'/profile?server=global',headers=auth).json()['storage'],'account')
        self.assertEqual(self.client.put(P+'/profile?server=global',headers=auth,json={}).status_code,409)

    def test_login_switch_invalidates_old_native_account_not_website_other_sessions(self):
        self.register();self.register('bob@example.test')
        value,alice=self.login()
        browser=TestClient(self.app,base_url='http://127.0.0.1:8044');me=browser.get('/api/auth/me').json()
        r=browser.post('/api/auth/login',json={'email':'alice@example.test','password':PASSWORD},headers={'Origin':'http://127.0.0.1:8044','X-CSRF-Token':me['csrf']})
        self.assertEqual(r.status_code,200,r.text)
        other,bob=self.login('bob@example.test')
        self.assertEqual(self.client.get(P+'/session',headers=alice).status_code,401)
        self.assertEqual(browser.get('/api/auth/me').json()['user']['id'],value['actor']['id'])
        self.assertEqual(self.client.delete(P+'/session',headers=bob).status_code,200)
        self.assertEqual(self.client.get(P+'/session',headers=self.guest).json()['session_kind'],'wechat_guest')
        self.assertEqual(browser.get('/api/auth/me').status_code,200);browser.close()

    def test_role_change_disable_and_password_anchor_revocation_invalidate_native(self):
        email=self.register();value,auth=self.login()
        set_role(self.root/'website',email,'admin')
        self.assertEqual(self.client.get(P+'/session',headers=auth).status_code,401)
        value,auth=self.login();self.assertEqual(value['actor']['role'],'admin')
        with self.app.state.store.connect() as db:
            db.execute('INSERT INTO account_controls VALUES(?,1,1,?)',(value['actor']['id'],int(time.time())))
        self.assertEqual(self.client.get(P+'/session',headers=auth).status_code,403)

    def test_all_three_account_roles_get_server_actor_and_only_batch_a_is_ready(self):
        for i,role in enumerate(['player','admin','superadmin']):
            email=self.register('role'+str(i)+'@example.test')
            if role!='player':set_role(self.root/'website',email,role)
            value,auth=self.login(email)
            self.assertEqual(value['actor']['role'],role)
            self.assertEqual(value['features']['native_batches'],{'A':'ready','B':'pending','C':'pending','D':'pending','E':'pending'})
            self.assertEqual(self.client.get(P+'/profile?server=cn',headers=auth).status_code,200)
            self.assertEqual(self.client.post('/api/admin/score-versions',headers=auth,json={}).status_code,403)

    def test_reauthentication_rotates_session_and_can_recover_using_guest(self):
        self.register();value,auth=self.login();key='fixture-reauth-key'
        r=self.action('reauth',{'password':PASSWORD},auth,key)
        self.assertEqual(r.status_code,200,r.text);self.assertNotEqual(r.json()['token'],value['token'])
        self.assertEqual(self.client.get(P+'/session',headers=auth).status_code,401)
        recovered=self.client.get(P+'/operations/'+key+'?action=reauth',headers=self.guest)
        self.assertEqual(recovered.json()['token'],r.json()['token'])

    def test_native_state_and_guest_expiry_fail_closed(self):
        self.register();value,auth=self.login()
        with self.guests.connect() as db:db.execute('UPDATE sessions SET revoked=1')
        self.assertEqual(self.client.get(P+'/session',headers=auth).status_code,401)
        with self.assertRaises(ValueError):account_provision(self.accounts.root)

    def test_account_prefix_closed_without_optional_account_state_and_cookies_not_auth(self):
        with tempfile.TemporaryDirectory() as root:
            app=create_app(Path(root),'http://127.0.0.1:8991')
            with TestClient(app,base_url='http://127.0.0.1:8991') as client:self.assertEqual(client.get(P+'/session').status_code,404)
        self.assertEqual(self.client.get(P+'/session',headers={**self.guest,'Origin':'http://127.0.0.1:8044'}).status_code,403)
        self.assertEqual(self.client.get(P+'/session').status_code,401)

    def test_two_device_profile_conflict_keeps_both_sessions_and_no_automatic_import(self):
        self.register();value,first=self.login()
        r=self.client.post('/api/mini/v1/session',json={'code':'fixture-device-2','client_schema':1,'request_key':'fixture-device-session'})
        guest2={'Authorization':'Bearer '+r.json()['token']}
        r=self.action('login',{'email':'alice@example.test','password':PASSWORD},guest2)
        self.assertEqual(r.status_code,200,r.text)
        second={'Authorization':'Bearer '+r.json()['token'],'X-Account-ID':r.json()['actor']['id']}
        self.assertIsNone(self.client.get(P+'/profile?server=cn',headers=second).json()['profile'])
        self.assertEqual(self.save(first).status_code,200)
        self.assertEqual(self.save(second).status_code,409)
        self.assertEqual(self.client.get(P+'/session',headers=first).status_code,200)

    def test_invitation_redemption_uses_shared_grant_and_revokes_old_native_session(self):
        import hashlib
        issuer=self.register('issuer@example.test');set_role(self.root/'website',issuer,'superadmin')
        self.register();value,auth=self.login();code='fixture-invitation-secret-123456'
        with self.app.state.store.connect() as db:
            uid=db.execute('SELECT id FROM users WHERE email=?',(issuer,)).fetchone()[0]
            db.execute("INSERT INTO admin_invitations(id,code_hash,email,issuer_id,status,expires_at,created_at,updated_at,revision) VALUES (?,?,?,?,'open',?,?,?,1)",
                       ('fixture-invitation',hashlib.sha256(code.encode()).hexdigest(),'alice@example.test',uid,int(time.time())+3600,int(time.time()),int(time.time())))
        r=self.action('redeem-invitation',{'invite_code':code},auth)
        self.assertEqual(r.status_code,200,r.text)
        self.assertEqual(self.client.get(P+'/session',headers=auth).status_code,401)
        value,auth=self.login();self.assertEqual(value['actor']['role'],'admin')

    def test_uncertain_registration_is_not_reexecuted_after_committed_mail(self):
        original=self.app.state.native_accounts.handlers['register']
        def uncertain(*args):
            original(*args)
            raise OSError('explicit fixture failure after commit')
        self.app.state.native_accounts.handlers['register']=Mock(side_effect=uncertain)
        key='fixture-uncertain-register';body={'email':'alice@example.test','password':PASSWORD}
        self.assertEqual(self.action('register',body,key=key).status_code,503)
        self.assertEqual(self.action('register',body,key=key).status_code,409)
        self.assertEqual(self.client.get(P+'/operations/'+key+'?action=register',headers=self.guest).status_code,409)
        self.assertEqual(self.app.state.native_accounts.handlers['register'].call_count,1)
        self.assertEqual(len(list((self.root/'website/outbox').glob('*.json'))),1)
