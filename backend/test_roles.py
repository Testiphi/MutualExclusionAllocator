import hashlib
import json
import secrets
import unittest
from unittest.mock import patch
from concurrent.futures import ThreadPoolExecutor
import threading
from fastapi import HTTPException
from backend import test_accounts as accounts
from backend.app import Store
from backend.roles import set_role
from fastapi.testclient import TestClient

ORIGIN=accounts.ORIGIN
PASSWORD=accounts.PASSWORD

class RolesTests(unittest.TestCase):
    setUp=accounts.AccountsTests.setUp
    tearDown=accounts.AccountsTests.tearDown
    new_client=accounts.AccountsTests.new_client
    post=accounts.AccountsTests.post
    token=accounts.AccountsTests.token
    signup=accounts.AccountsTests.signup

    def login(self,client,email):
        client.cookies.clear();me=client.get('/api/auth/me').json()
        client.headers.update({'Origin':ORIGIN,'X-CSRF-Token':me['csrf']})
        result=self.post('login',{'email':email,'password':PASSWORD},client)
        self.assertEqual(result.status_code,200,result.text)
        client.headers.update({'X-CSRF-Token':result.json()['csrf'],'X-Account-ID':result.json()['user']['id']})
        return result.json()['user']

    def owner(self):
        self.signup('owner@example.com');set_role(self.path,'owner@example.com','superadmin')
        return self.login(self.client,'owner@example.com')

    def invite(self,email='invitee@example.com',hours=72):
        result=self.client.post('/api/admin/invitations',json={'email':email,'expires_hours':hours})
        self.assertEqual(result.status_code,200,result.text);return result.json()

    def invitee(self,invite):
        client=self.new_client()
        response=self.post('register',{'email':invite['email'],'password':PASSWORD,'invite_code':invite['code']},client)
        self.assertEqual(response.status_code,200,response.text)
        return client

    def verify(self,client,email):return self.post('verify-email',{'token':self.token(email,'verify')},client)

    def test_owner_protection_and_admin_authorization(self):
        owner=self.owner();self.assertEqual(owner['role'],'superadmin')
        self.assertEqual(self.client.get('/api/auth/me').json()['user']['role'],'superadmin')
        self.assertEqual(self.client.get('/api/submissions?scope=review').status_code,200)
        self.assertEqual(self.client.post('/api/admin/members/'+owner['id']+'/revoke',json={'reason':'cannot revoke owner'}).status_code,403)
        with self.assertRaises(ValueError):set_role(self.path,'owner@example.com','player')
        with self.assertRaises(ValueError):set_role(self.path,'owner@example.com','admin')
        other=self.new_client();self.signup('admin@example.com',other);set_role(self.path,'admin@example.com','admin')
        admin=self.login(other,'admin@example.com');self.assertEqual(admin['role'],'admin')
        self.assertEqual(other.get('/api/submissions?scope=review').status_code,200)
        for path in ['/api/admin/invitations','/api/admin/members']:
            self.assertEqual(other.get(path).status_code,403)
        self.assertEqual(other.post('/api/admin/invitations',json={'email':'x@example.com'}).status_code,403)
        with self.assertRaises(ValueError):set_role(self.path,'admin@example.com','superadmin')
        other.close()

    def test_invited_registration_grants_only_after_email_verification(self):
        self.owner();invite=self.invite();other=self.invitee(invite)
        with self.app.state.store.connect() as db:
            row=db.execute('SELECT role,verified FROM users WHERE email=?',(invite['email'],)).fetchone()
            self.assertEqual(tuple(row),('player',0))
            stored=db.execute('SELECT * FROM admin_invitations WHERE id=?',(invite['id'],)).fetchone()
            self.assertEqual(stored['status'],'reserved')
            self.assertEqual(stored['code_hash'],hashlib.sha256(invite['code'].encode()).hexdigest())
            self.assertNotIn(invite['code'],repr(tuple(stored)))
        self.assertNotIn(invite['code'],self.client.get('/api/admin/invitations').text)
        self.assertEqual(self.post('login',{'email':invite['email'],'password':PASSWORD},other).status_code,403)
        self.assertEqual(self.verify(other,invite['email']).status_code,200)
        user=self.login(other,invite['email']);self.assertEqual(user['role'],'admin')
        self.assertEqual(other.get('/api/submissions?scope=review').status_code,200)
        self.assertEqual(other.get('/api/admin/invitations').status_code,403)
        with self.app.state.store.connect() as db:
            self.assertEqual(db.execute('SELECT status FROM admin_invitations WHERE id=?',(invite['id'],)).fetchone()[0],'used')
        self.assertEqual(self.client.post(f'/api/admin/invitations/{invite["id"]}/revoke',json={'revision':3}).status_code,409)
        other.close()

    def test_invalid_wrong_email_and_role_injection_do_not_create_accounts(self):
        self.owner();invite=self.invite();other=self.new_client()
        for email,code in [('wrong@example.com',invite['code']),('invitee@example.com','rpa_invalid')]:
            self.assertEqual(self.post('register',{'email':email,'password':PASSWORD,'invite_code':code},other).status_code,400)
        self.assertEqual(self.post('register',{'email':'p@example.com','password':PASSWORD,'role':'superadmin'},other).status_code,422)
        self.assertEqual(self.client.post('/api/admin/invitations',json={'email':'p@example.com','role':'superadmin'}).status_code,422)
        with self.app.state.store.connect() as db:self.assertEqual(db.execute('SELECT count(*) FROM users').fetchone()[0],1)
        other.close()

    def test_revocation_after_registration_preserves_email_verification_as_player(self):
        self.owner();invite=self.invite();other=self.invitee(invite)
        self.assertEqual(self.client.post(f'/api/admin/invitations/{invite["id"]}/revoke',json={'revision':1}).status_code,409)
        self.assertEqual(self.client.post(f'/api/admin/invitations/{invite["id"]}/revoke',json={'revision':2}).status_code,200)
        response=self.verify(other,invite['email']);self.assertEqual(response.status_code,200);self.assertIn('失效',response.json()['message'])
        self.assertEqual(self.login(other,invite['email'])['role'],'player')
        self.assertEqual(other.get('/api/submissions?scope=review').status_code,403)
        replacement=self.invite(invite['email'])
        self.assertEqual(self.post('redeem-invitation',{'invite_code':replacement['code']},other).status_code,200)
        self.login(other,invite['email'])
        self.post('forgot-password',{'email':invite['email']},other)
        response=self.post('reset-password',{'token':self.token(invite['email'],'reset'),'password':'replacement-test-password'},other)
        self.assertEqual(response.status_code,200)
        self.assertNotIn('邀请已失效',response.json()['message'])
        with self.app.state.store.connect() as db:self.assertEqual(db.execute('SELECT role FROM users WHERE email=?',(invite['email'],)).fetchone()[0],'admin')
        other.close()

    def test_expired_invite_before_and_after_registration(self):
        self.owner();invite=self.invite('expired@example.com')
        with self.app.state.store.connect() as db:db.execute('UPDATE admin_invitations SET expires_at=0 WHERE id=?',(invite['id'],))
        other=self.new_client();response=self.post('register',{'email':invite['email'],'password':PASSWORD,'invite_code':invite['code']},other)
        self.assertEqual(response.status_code,400);other.close()
        fresh=self.invite();other=self.invitee(fresh)
        with self.app.state.store.connect() as db:db.execute('UPDATE admin_invitations SET expires_at=0 WHERE id=?',(fresh['id'],))
        self.assertEqual(self.verify(other,fresh['email']).status_code,200)
        self.assertEqual(self.login(other,fresh['email'])['role'],'player')
        other.close()

    def test_existing_player_redeem_revoke_and_preserve_profile(self):
        self.owner();other=self.new_client();user=self.signup('player@example.com',other)
        other.put('/api/me/profile',json={'revision':0,'cars':[],'stars':{}})
        invite=self.invite('player@example.com')
        response=self.post('register',{'email':'player@example.com','password':PASSWORD,'invite_code':invite['code']},other)
        self.assertEqual(response.status_code,409)
        self.assertEqual(self.post('redeem-invitation',{'invite_code':invite['code']},other).status_code,200)
        self.assertEqual(other.get('/api/me/profile').status_code,401)
        self.assertEqual(self.login(other,'player@example.com')['role'],'admin')
        self.assertEqual(other.get('/api/me/profile').json()['revision'],1)
        self.assertEqual(self.post('redeem-invitation',{'invite_code':invite['code']},other).status_code,400)
        self.assertEqual(self.client.post('/api/admin/members/'+user['id']+'/revoke',json={'reason':'测试回收权限'}).status_code,200)
        self.assertEqual(other.get('/api/me/profile').status_code,401)
        self.assertEqual(self.login(other,'player@example.com')['role'],'player')
        self.assertEqual(other.get('/api/me/profile').json()['profile'],{'cars':[],'stars':{}})
        other.close()

    def test_mail_failure_keeps_reservation_and_resend_can_activate(self):
        self.owner();invite=self.invite();other=self.new_client()
        with patch.object(self.app.state.mail_service,'deliver',side_effect=HTTPException(503,'模拟失败')):
            response=self.post('register',{'email':invite['email'],'password':PASSWORD,'invite_code':invite['code']},other)
        self.assertEqual(response.status_code,503)
        self.assertEqual(self.post('resend-verification',{'email':invite['email']},other).status_code,200)
        self.assertEqual(self.verify(other,invite['email']).status_code,200)
        self.assertEqual(self.login(other,invite['email'])['role'],'admin')
        other.close()

    def test_csrf_account_binding_and_expiry_bounds(self):
        self.owner()
        for hours in [0,169,True]:self.assertEqual(self.client.post('/api/admin/invitations',json={'email':'a@example.com','expires_hours':hours}).status_code,422)
        self.assertEqual(self.client.post('/api/admin/invitations',json={'email':'a@example.com'},headers={'X-CSRF-Token':'wrong'}).status_code,403)
        self.assertEqual(self.client.get('/api/admin/invitations',headers={'X-Account-ID':'wrong'}).status_code,401)

    def test_concurrent_invites_and_redemption_do_not_double_grant(self):
        self.owner();barrier=threading.Barrier(2)
        def create(_):
            with TestClient(self.app,base_url=ORIGIN) as c:
                c.cookies.update(self.client.cookies);c.headers.update(self.client.headers);barrier.wait()
                return c.post('/api/admin/invitations',json={'email':'player@example.com'})
        with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(create,range(2)))
        self.assertEqual(sorted(r.status_code for r in results),[200,409])
        invite=next(r.json() for r in results if r.status_code==200)
        other=self.new_client();self.signup('player@example.com',other);barrier=threading.Barrier(2)
        def redeem(_):
            with TestClient(self.app,base_url=ORIGIN) as c:
                c.cookies.update(other.cookies);c.headers.update(other.headers);barrier.wait()
                return c.post('/api/auth/redeem-invitation',json={'invite_code':invite['code']}).status_code
        with ThreadPoolExecutor(max_workers=2) as pool:codes=list(pool.map(redeem,range(2)))
        self.assertEqual(codes.count(200),1)
        self.assertTrue(all(code in (200,400,401,409) for code in codes))
        with self.app.state.store.connect() as db:self.assertEqual(db.execute("SELECT count(*) FROM invitation_events WHERE action='activated'").fetchone()[0],1)
        other.close()

    def test_v4_migration_keeps_ids_passwords_and_profiles(self):
        self.signup();self.client.put('/api/me/profile',json={'revision':0,'cars':[],'stars':{}})
        with self.app.state.store.connect() as db:
            before={table:[tuple(r) for r in db.execute('SELECT * FROM '+table)] for table in ['users','profiles','auth_tokens','sessions']}
            for table in ['invitation_events','admin_invitations','super_admins','access_events']:db.execute('DROP TABLE '+table)
            db.execute('DELETE FROM schema_version WHERE version=5')
        store=Store(self.path)
        with store.connect() as db:
            self.assertEqual(db.execute('SELECT max(version) FROM schema_version').fetchone()[0],5)
            self.assertEqual(before,{table:[tuple(r) for r in db.execute('SELECT * FROM '+table)] for table in before})
            self.assertEqual(db.execute('PRAGMA foreign_key_check').fetchall(),[])

if __name__=='__main__':unittest.main()
