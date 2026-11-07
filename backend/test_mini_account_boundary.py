"""In-process fixtures only; no listener, real platform, SMTP, OCR or old state."""
import secrets
import unittest
from unittest.mock import Mock

from fastapi.testclient import TestClient
from backend.mini_account_boundary import AccountBoundary, AccountBoundaryOptions
from backend.mini_api import MiniGateway
from backend import test_mini_accounts as fixture

P, PASSWORD = fixture.P, fixture.PASSWORD


class BoundaryOffTests(unittest.TestCase):
    def test_default_does_not_initialize_and_is_closed(self):
        factory = Mock(side_effect=AssertionError('must not initialize'))
        with TestClient(AccountBoundary(factory)) as client:
            r = client.get(P+'/session')
            self.assertEqual(r.status_code, 404)
            self.assertEqual(r.headers['cache-control'], 'no-store')
        factory.assert_not_called()

    def test_switches_are_strict(self):
        for args in ({'enabled': 'false'}, {'cloud_writes': 1}, {'cloud_writes': True}):
            with self.assertRaises(ValueError):
                AccountBoundaryOptions(**args)
        with self.assertRaises(ValueError):
            AccountBoundary(lambda: object(), AccountBoundaryOptions(True))


class BoundaryTests(unittest.TestCase):
    def setUp(self):
        self.f = fixture.NativeAccountTests(); self.f.setUp(); self.addCleanup(self.f.tearDown)
        self.f.register()
        self.options = {'store': self.f.guests, 'account_store': self.f.accounts,
                        'verifier': lambda code: 'explicit-fixture-'+code,
                        'fixture': True, 'image_policy': 'disabled', 'account_a_only': True}
        self.client = self.make_client()

    def make_client(self, writes=False):
        # Exercise existing website handlers and parent store, not a new auth algorithm.
        gateway = MiniGateway(self.f.app, config=self.options, source=self.f.app.state,
                              service=None, origin='http://127.0.0.1:8044', production=False)
        client = TestClient(AccountBoundary(lambda: gateway, AccountBoundaryOptions(True, writes)),
                            base_url='http://127.0.0.1:8044', client=('127.0.0.1', 12000))
        client.__enter__(); self.addCleanup(client.__exit__, None, None, None)
        return client

    def login(self, password=PASSWORD, key=None):
        return self.client.post(P+'/auth/login', headers=self.f.guest, json={
            'schema': 1, 'request_key': key or secrets.token_hex(16),
            'email': 'alice@example.test', 'password': password})

    def auth(self, response):
        value = response.json()
        return {'Authorization': 'Bearer '+value['token'], 'X-Account-ID': value['actor']['id']}

    def test_wrong_password_preserves_parent_and_features_only_a(self):
        self.assertEqual(self.login('wrong-fixture-password').status_code, 401)
        self.assertEqual(self.client.get(P+'/session', headers=self.f.guest).status_code, 200)
        r = self.login(); self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.json()['features']['native_batches'],
                         {'A': 'ready', 'B': 'pending', 'C': 'pending', 'D': 'pending', 'E': 'pending'})
        self.assertEqual(r.json()['features']['profiles'], {'cn': 'account', 'global': 'account'})
        guest = self.f.guests.authenticate(self.f.guest['Authorization'])
        with self.f.guests.connect() as db:
            expiry = db.execute('SELECT expires FROM sessions WHERE sid=?', (guest['sid'],)).fetchone()[0]
        self.assertLessEqual(r.json()['expires_at'], expiry)

    def test_excluded_routes_and_mail_recovery_never_reach_app(self):
        with self.f.app.state.store.connect() as db:
            before = db.execute('SELECT count(*) FROM users').fetchone()[0]
        for path in ('/api/auth/login', P+'/auth/register', P+'/auth/verify-email',
                     P+'/auth/forgot-password', P+'/auth/redeem-invitation',
                     '/api/mini/v1/map-recognition/jobs', P+'/feedback'):
            self.assertEqual(self.client.post(path, headers=self.f.guest, json={}).status_code, 404)
        self.assertEqual(self.client.get(P+'/operations/fixture-mail-key1?action=register', headers=self.f.guest).status_code, 404)
        with self.f.app.state.store.connect() as db:
            self.assertEqual(db.execute('SELECT count(*) FROM users').fetchone()[0], before)

    def test_readonly_null_and_write_gate_then_explicit_empty(self):
        auth = self.auth(self.login())
        for server in ('cn', 'global'):
            url = P+'/profile?server='+server
            r = self.client.get(url, headers=auth)
            self.assertEqual(r.status_code, 200, r.text)
            self.assertIsNone(r.json()['profile']); self.assertEqual(r.json()['revision'], 0)
            body = {'schema': 1, 'request_key': secrets.token_hex(16), 'explicit_save': True,
                    'intent': 'save', 'revision': 0, 'cars': [], 'stars': {}}
            if server == 'global': body['ocMap'] = {}
            self.assertEqual(self.client.put(url, headers=auth, json=body).status_code, 503)
            writable = self.make_client(True)
            self.assertEqual(writable.put(url, headers=auth, json=body).status_code, 200)
            r = self.client.get(url, headers=auth).json()
            self.assertEqual(r['revision'], 1); self.assertIsNotNone(r['profile'])

    def test_login_recovery_and_logout_do_not_resurrect_identity(self):
        key = 'boundary-login-recovery'
        response = self.login(key=key); auth = self.auth(response)
        url = P+'/operations/'+key+'?action=login'
        restored = self.client.get(url, headers=self.f.guest)
        self.assertEqual(restored.json()['token'], response.json()['token'])
        self.assertEqual(self.client.delete(P+'/session', headers=auth).status_code, 200)
        self.assertEqual(self.client.get(url, headers=self.f.guest).status_code, 401)
        self.assertEqual(self.client.get(P+'/session', headers=self.f.guest).status_code, 200)

    def test_host_cookie_origin_options_size_and_duplicate_query(self):
        for headers in ({'Host': 'evil.test'}, {'Cookie': ''}, {'Origin': ''}):
            r = self.client.get(P+'/session', headers={**self.f.guest, **headers})
            self.assertIn(r.status_code, (400, 403))
            self.assertEqual(r.headers['cache-control'], 'no-store')
        self.assertEqual(self.client.options(P+'/session').status_code, 403)
        r = self.client.post(P+'/auth/login', headers={**self.f.guest, 'Content-Type': 'application/json'}, content=b' '*65537)
        self.assertEqual(r.status_code, 413)
        self.assertEqual(self.client.get(P+'/operations/boundary-query-key?action=login&action=login', headers=self.f.guest).status_code, 404)

    def test_reauth_recovery_and_parent_revocation(self):
        original = self.login(); auth = self.auth(original)
        key = 'boundary-reauth-key'
        response = self.client.post(P+'/auth/reauth', headers=auth, json={
            'schema': 1, 'request_key': key, 'password': PASSWORD})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertNotEqual(response.json()['token'], original.json()['token'])
        self.assertEqual(self.client.get(P+'/session', headers=auth).status_code, 401)
        recovery = self.client.get(P+'/operations/'+key+'?action=reauth', headers=self.f.guest)
        self.assertEqual(recovery.json()['token'], response.json()['token'])
        with self.f.guests.connect() as db:
            db.execute('UPDATE sessions SET revoked=1')
        self.assertEqual(self.client.get(P+'/session', headers=self.auth(response)).status_code, 401)

    def test_https_proxy_and_a_only_routes(self):
        config = {**self.options, 'fixture': False}
        gateway = MiniGateway(self.f.app, config=config, source=self.f.app.state, service=None,
                              origin='https://mini-test.example.test', production=True)
        self.assertEqual(gateway.account.state.native_features['routes'], [])
        with TestClient(AccountBoundary(lambda: gateway, AccountBoundaryOptions(True)),
                        base_url='https://mini-test.example.test', client=('127.0.0.1', 12000)) as client:
            self.assertEqual(client.get(P+'/session', headers=self.f.guest).status_code, 400)
            proxy = {**self.f.guest, 'X-Forwarded-Proto': 'https', 'X-Real-IP': '192.0.2.4'}
            self.assertEqual(client.get(P+'/session', headers=proxy).status_code, 200)
            self.assertEqual(client.get(P+'/session', headers={**proxy, 'X-Real-IP': 'invalid'}).status_code, 400)


if __name__ == '__main__':
    unittest.main()
