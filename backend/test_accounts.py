import json
from pathlib import Path
import tempfile
import unittest
from urllib.parse import urlsplit, parse_qs
from fastapi.testclient import TestClient
from backend.app import create_app, COOKIE, digest

ORIGIN='http://127.0.0.1:8000'
PASSWORD='local-password-12345'

class AccountsTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.path=Path(self.temp.name)
        self.app=create_app(self.path)
        self.client=self.new_client()
    def tearDown(self):
        self.client.close(); self.temp.cleanup()
    def new_client(self):
        c=TestClient(self.app,base_url=ORIGIN)
        me=c.get('/api/auth/me').json()
        c.headers.update({'Origin':ORIGIN,'X-CSRF-Token':me['csrf'],'X-Profile-Save':'explicit'})
        return c
    def post(self,path,data,client=None):
        return (client or self.client).post('/api/auth/'+path,json=data)
    def token(self,email,purpose):
        messages=[json.loads(p.read_text(encoding='utf-8')) for p in sorted((self.path/'outbox').glob('*.json'))]
        mail=[m for m in messages if m['to']==email and m['purpose']==purpose][-1]
        return parse_qs(urlsplit(mail['url']).fragment)['token'][0]
    def signup(self,email='player@example.com',client=None):
        c=client or self.client
        self.assertEqual(self.post('register',{'email':email,'password':PASSWORD},c).status_code,200)
        self.assertEqual(self.post('verify-email',{'token':self.token(email,'verify')},c).status_code,200)
        old=c.cookies.get(COOKIE)
        r=self.post('login',{'email':email,'password':PASSWORD},c)
        self.assertEqual(r.status_code,200,r.text)
        self.assertNotEqual(old,c.cookies.get(COOKIE))
        c.headers['X-CSRF-Token']=r.json()['csrf']
        c.headers['X-Account-ID']=r.json()['user']['id']
        return r.json()['user']
    def test_registration_verification_and_session_rotation(self):
        user=self.signup()
        self.assertEqual(user['role'],'player')
        fresh=TestClient(self.app,base_url=ORIGIN)
        cookie=fresh.get('/api/auth/me').headers['set-cookie']
        self.assertIn('HttpOnly',cookie)
        self.assertIn('SameSite=strict',cookie)
        fresh.close()
        with self.app.state.store.connect() as db:
            row=db.execute('SELECT * FROM users').fetchone()
            self.assertTrue(row['password_hash'].startswith('$argon2id$'))
            self.assertNotIn(PASSWORD,row['password_hash'])
            self.assertFalse(db.execute('SELECT * FROM auth_tokens').fetchall())
        self.assertEqual(self.post('logout',{}).status_code,200)
        self.assertEqual(self.client.get('/api/me/profile').status_code,401)
    def test_csrf_origin_host_and_extra_privilege_fields(self):
        self.assertEqual(self.client.post('/api/auth/register',json={'email':'x@example.com','password':PASSWORD},headers={'Origin':'https://evil.example'}).status_code,403)
        self.assertEqual(self.client.post('/api/auth/register',json={'email':'x@example.com','password':PASSWORD},headers={'X-CSRF-Token':'bad'}).status_code,403)
        self.assertEqual(self.client.get('/',headers={'Host':'evil.example'}).status_code,400)
        self.assertEqual(self.post('register',{'email':'x@example.com','password':PASSWORD,'role':'admin'}).status_code,422)
        self.assertEqual(self.client.post('/api/auth/register',content='x'*65537,headers={'Content-Type':'application/json'}).status_code,413)
    def test_profile_isolation_empty_and_compare_and_swap(self):
        self.signup()
        self.assertEqual(self.client.get('/api/me/profile').json(),{'revision':0,'profile':None})
        profile={'revision':0,'cars':[],'stars':{}}
        self.assertEqual(self.client.put('/api/me/profile',json=profile).json(),{'revision':1})
        self.assertEqual(self.client.get('/api/me/profile').json()['profile']['cars'],[])
        self.assertEqual(self.client.put('/api/me/profile',json=profile).status_code,409)
        other=self.new_client(); self.signup('other@example.com',other)
        self.assertIsNone(other.get('/api/me/profile').json()['profile'])
        self.assertEqual(other.put('/api/me/profile',json={**profile,'user_id':self.client.headers['X-Account-ID']}).status_code,422)
        self.assertEqual(self.client.put('/api/me/profile',json={'revision':1,'cars':['does-not-exist'],'stars':{}}).status_code,422)
        car=json.loads((Path(__file__).parents[1]/'cars.json').read_text(encoding='utf-8'))['cars']
        name=next(c['nickname'] for c in car if c.get('nickname') and c.get('zones'))
        for value in [0,7,True,'6']:
            self.assertEqual(self.client.put('/api/me/profile',json={'revision':1,'cars':[name],'stars':{name:value}}).status_code,422)
        self.assertEqual(self.client.put('/api/me/profile',json={'revision':1,'cars':[name],'stars':{name:6}}).status_code,200)
        other.close()
    def test_cross_tab_cookie_change_cannot_write_old_profile_to_new_account(self):
        self.signup()
        other=self.new_client(); self.signup('other@example.com',other)
        self.client.cookies.clear()
        self.client.cookies.update(other.cookies)
        self.client.headers['X-CSRF-Token']=other.headers['X-CSRF-Token']
        self.assertEqual(self.client.put('/api/me/profile',json={'revision':0,'cars':[],'stars':{}}).status_code,401)
        self.assertIsNone(other.get('/api/me/profile').json()['profile'])
        other.close()
    def test_reset_is_single_use_and_revokes_all_sessions(self):
        self.signup()
        self.assertEqual(self.post('forgot-password',{'email':'player@example.com'}).status_code,200)
        token=self.token('player@example.com','reset')
        self.assertEqual(self.post('reset-password',{'token':token,'password':'replacement-password-123'}).status_code,200)
        self.assertEqual(self.client.get('/api/me/profile').status_code,401)
        anonymous=self.new_client()
        self.assertEqual(self.post('reset-password',{'token':token,'password':PASSWORD},anonymous).status_code,400)
        self.assertEqual(self.post('login',{'email':'player@example.com','password':PASSWORD},anonymous).status_code,401)
        self.assertEqual(self.post('login',{'email':'player@example.com','password':'replacement-password-123'},anonymous).status_code,200)
        anonymous.close()
    def test_expiry_throttling_and_static_allowlist(self):
        self.signup()
        with self.app.state.store.connect() as db:
            db.execute('UPDATE sessions SET expires_at=0')
        self.assertEqual(self.client.get('/api/me/profile').status_code,401)
        anonymous=self.new_client()
        for i in range(10):
            self.assertEqual(self.post('login',{'email':'missing@example.com','password':PASSWORD},anonymous).status_code,401)
        self.assertEqual(self.post('login',{'email':'missing@example.com','password':PASSWORD},anonymous).status_code,429)
        for path in ['/backend/app.py','/.local-accounts/accounts.sqlite3','/gauntlet_data.xlsx','/.git/config','/auth.js/../backend/app.py','/api/admin/users']:
            self.assertEqual(anonymous.get(path).status_code,404,path)
        self.assertIn('/auth.js',anonymous.get('/').text)
        self.assertEqual(anonymous.get('/cars.json').status_code,200)
        anonymous.close()
    def test_unverified_expired_token_and_duplicate_email(self):
        creds={'email':'player@example.com','password':PASSWORD}
        self.post('register',creds)
        self.assertEqual(self.post('login',creds).status_code,403)
        self.post('register',{**creds,'email':' PLAYER@EXAMPLE.COM '})
        with self.app.state.store.connect() as db:
            self.assertEqual(db.execute('SELECT count(*) FROM users').fetchone()[0],1)
            db.execute('UPDATE auth_tokens SET expires_at=0')
        self.assertEqual(self.post('verify-email',{'token':self.token('player@example.com','verify')}).status_code,400)
    def test_simultaneous_profile_updates_allow_only_one_writer(self):
        self.signup()
        import threading
        from concurrent.futures import ThreadPoolExecutor
        barrier=threading.Barrier(2)
        def write():
            with TestClient(self.app,base_url=ORIGIN) as client:
                client.cookies.update(self.client.cookies)
                client.headers.update(self.client.headers)
                barrier.wait()
                return client.put('/api/me/profile',json={'revision':0,'cars':[],'stars':{}}).status_code
        with ThreadPoolExecutor(max_workers=2) as pool:
            results=list(pool.map(lambda _:write(),range(2)))
        self.assertEqual(sorted(results),[200,409])
        self.assertEqual(self.client.get('/api/me/profile').json()['revision'],1)

    def test_resend_replaces_old_token_and_verification_is_single_use(self):
        self.post('register',{'email':'player@example.com','password':PASSWORD})
        old=self.token('player@example.com','verify')
        self.assertEqual(self.post('resend-verification',{'email':'player@example.com'}).status_code,200)
        new=self.token('player@example.com','verify')
        self.assertNotEqual(old,new)
        self.assertEqual(self.post('verify-email',{'token':old}).status_code,400)
        self.assertEqual(self.post('verify-email',{'token':new}).status_code,200)
        self.assertEqual(self.post('verify-email',{'token':new}).status_code,400)

    def test_local_ports_use_distinct_session_cookie_names(self):
        self.signup()
        other_app=create_app(self.path/'other-port',origin='http://127.0.0.1:8001')
        with TestClient(other_app,base_url='http://127.0.0.1:8001') as other:
            other.cookies.update(self.client.cookies)
            response=other.get('/api/auth/me')
            self.assertIsNone(response.json()['user'])
            self.assertIn(COOKIE+'_8001=',response.headers['set-cookie'])
            self.client.cookies.update(other.cookies)
            self.assertEqual(self.client.get('/api/auth/me').json()['user']['email'],'player@example.com')

    def test_database_restart_preserves_data_and_backup(self):
        self.signup()
        self.client.put('/api/me/profile',json={'revision':0,'cars':[],'stars':{}})
        another=TestClient(create_app(self.path),base_url=ORIGIN)
        another.cookies.update(self.client.cookies)
        another.headers.update(self.client.headers)
        self.assertEqual(another.get('/api/me/profile').json()['revision'],1)
        import sqlite3
        from backend.manage import copy_database
        backup=self.path/'backup.sqlite3'
        copy_database(self.app.state.store.path,backup)
        with self.assertRaises(ValueError): copy_database(self.app.state.store.path,backup)
        restored=self.path/'restored'/'accounts.sqlite3'
        copy_database(backup,restored)
        restored_app=create_app(restored.parent)
        with restored_app.state.store.connect() as db:
            self.assertEqual(db.execute('SELECT revision FROM profiles').fetchone()[0],1)
        dest=sqlite3.connect(backup)
        self.assertEqual(dest.execute('PRAGMA integrity_check').fetchone()[0],'ok')
        self.assertEqual(dest.execute('SELECT revision FROM profiles').fetchone()[0],1)
        dest.close(); another.close()

if __name__=='__main__': unittest.main()
