"""New isolated state and patched platform only; no credentials or production calls."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from backend.mini_auth import KIND, provision, WechatVerifier
from backend.mini_guest_service import KIND as SNAPSHOT_KIND, FILES, load_snapshot, make_app, validate_origin

ROOT = Path(__file__).resolve().parents[1]


class MiniGuestServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.snapshot = self.root/'snapshot'
        self.snapshot.mkdir()
        data_root = ROOT if (ROOT/FILES[0]).is_file() else ROOT/'snapshot'
        self.raw = {n: (data_root/n).read_bytes() for n in FILES}
        for n, raw in self.raw.items():
            (self.snapshot/n).write_bytes(raw)
        self.manifest = {'kind': SNAPSHOT_KIND, 'files': {n: {
            'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)}
            for n, raw in self.raw.items()}}
        (self.snapshot/'snapshot.json').write_text(json.dumps(self.manifest), encoding='utf-8')
        self.state = provision(self.root/'guests')
        self.secret = self.root/'secret'
        self.secret.write_text('fixture-only-not-a-platform-secret', encoding='utf-8')
        self.secret.chmod(0o600)
        self.config = self.root/'mini.json'
        self.declaration = {'kind': KIND, 'state_dir': str(self.state),
            'appid': 'wx'+'0'*16, 'app_secret_file': str(self.secret), 'image_policy': 'disabled'}
        self.save_config()
        self.platform = patch.object(WechatVerifier, '__call__', return_value='owned-platform-fixture')
        self.verifier = self.platform.start()
        self.addCleanup(self.platform.stop)
        self.origin = 'https://mini-test.example.test'
        app, _ = make_app(self.snapshot, self.config, self.origin)
        self.client = TestClient(app, base_url=self.origin, client=('127.0.0.1', 1234))
        self.addCleanup(self.client.close)
        self.headers = {'X-Forwarded-Proto': 'https', 'X-Real-IP': '192.0.2.8'}

    def save_config(self):
        self.config.write_text(json.dumps(self.declaration), encoding='utf-8')
        self.config.chmod(0o600)

    def login(self):
        r = self.client.post('/api/mini/v1/session', headers=self.headers,
            json={'code': 'owned-fixture-code', 'client_schema': 1,
                  'request_key': 'stage-one-test-request'})
        self.assertEqual(r.status_code, 200, r.text)
        return r.json()

    def test_original_utf8_snapshots_have_no_image_or_account_capability(self):
        session = self.login()
        for server, names in [('cn', FILES[:2]), ('global', FILES[2:])]:
            r = self.client.get('/api/mini/v1/snapshot?server='+server,
                headers={**self.headers, 'Authorization': 'Bearer '+session['token']})
            self.assertEqual(r.status_code, 200, r.text)
            body = r.json()
            self.assertEqual(body['identity'], session['identity'])
            self.assertFalse(body['capabilities']['map_recognition'])
            self.assertIsNone(body['catalog_version'])
            self.assertEqual(set(body['files']), set(names))
            self.assertEqual(r.headers['cache-control'], 'no-store')
            for name in names:
                self.assertEqual(body['files'][name]['text'].encode('utf-8'), self.raw[name])
                self.assertEqual(body['files'][name]['sha256'], self.manifest['files'][name]['sha256'])
        self.assertEqual(self.verifier.call_count, 1)
        self.assertFalse((self.state/'accounts.sqlite3').exists())
        self.assertFalse((self.state/'recognition.sqlite3').exists())

    def test_trusted_proxy_host_and_browser_boundary(self):
        url = '/api/mini/v1/snapshot?server=cn'
        for headers in [{}, {**self.headers, 'Host': 'other.example.test'},
                        {**self.headers, 'X-Real-IP': 'not-an-ip'},
                        {**self.headers, 'X-Forwarded-Proto': 'http'}]:
            self.assertEqual(self.client.get(url, headers=headers).status_code, 400)
        for key in ['Origin', 'Cookie']:
            self.assertEqual(self.client.get(url, headers={**self.headers, key: 'blocked'}).status_code, 403)
        self.assertEqual(self.client.options(url, headers=self.headers).status_code, 403)
        self.assertEqual(self.client.get(url, headers=self.headers).status_code, 401)
        app, _ = make_app(self.snapshot, self.config, self.origin)
        with TestClient(app, base_url=self.origin, client=('192.0.2.20', 1234)) as client:
            self.assertEqual(client.get(url, headers=self.headers).status_code, 400)

    def test_later_phase_routes_are_unavailable_even_with_valid_guest(self):
        session = self.login()
        headers = {**self.headers, 'Authorization': 'Bearer '+session['token']}
        for method, url in [('GET', '/'), ('GET', '/api/health'),
            ('GET', '/api/mini/account/v1/session'), ('GET', '/api/mini/v1/contract'),
            ('GET', '/api/mini/v1/map-recognition/catalog?server=cn'),
            ('POST', '/api/mini/v1/map-recognition/jobs'), ('DELETE', '/api/mini/v1/session')]:
            self.assertEqual(self.client.request(method, url, headers=headers).status_code, 404)

    def test_refuses_account_config_or_unmoderated_images_before_loading_state(self):
        for extra in [{'account_state_dir': '/does-not-exist'}, {'image_policy': 'private_unmoderated'}]:
            self.declaration.update(extra)
            self.save_config()
            with patch('backend.mini_guest_service.load_config') as load:
                with self.assertRaises(ValueError):
                    make_app(self.snapshot, self.config, self.origin)
                load.assert_not_called()
            self.declaration.pop('account_state_dir', None)
            self.declaration['image_policy'] = 'disabled'

    def test_startup_never_initializes_or_reuses_missing_guest_state(self):
        self.declaration['state_dir'] = str(self.root/'not-provisioned')
        self.save_config()
        with self.assertRaises((ValueError, OSError)):
            make_app(self.snapshot, self.config, self.origin)
        self.assertFalse((self.root/'not-provisioned').exists())

    def test_snapshot_is_immutable_until_restart_and_corruption_is_rejected(self):
        source, _ = load_snapshot(self.snapshot)
        old = source.score_versions.current()
        (self.snapshot/FILES[0]).write_bytes(b'{}')
        self.assertEqual(source.score_versions.current(), old)
        with self.assertRaises(ValueError):
            load_snapshot(self.snapshot)

    def test_extra_state_files_cannot_be_mixed_into_snapshot(self):
        (self.snapshot/'accounts.sqlite3').write_bytes(b'not-a-database')
        with self.assertRaises(ValueError):
            load_snapshot(self.snapshot)

    def test_origin_must_be_explicit_https_dns_without_paths_or_credentials(self):
        for value in ['http://mini.example.test', 'https://127.0.0.1',
                      'https://mini.example.test/', 'https://user:pass@mini.example.test',
                      'https://mini.example.test/api', 'https://mini.example.test?token=x']:
            with self.assertRaises(ValueError):
                validate_origin(value)

    def test_inspection_imports_no_business_database_or_ocr_module(self):
        script = ('import sys; from backend.mini_guest_service import load_snapshot; '
                  f'load_snapshot({str(self.snapshot)!r}); '
                  'assert not any(n in sys.modules for n in '
                  "['backend.app','backend.mini_accounts','backend.mini_features',"
                  "'backend.map_recognition','backend.map_ocr_worker','onnxruntime'])")
        subprocess.run([sys.executable, '-B', '-c', script], cwd=ROOT, check=True,
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)


if __name__ == '__main__':
    unittest.main()
