"""Production-shaped fixtures, including trusted proxy and the same persisted OCR queue.

All platform exchanges are patched fixtures, never real WeChat validation.
"""
from pathlib import Path
from unittest.mock import patch, Mock
import json
import tempfile
import time
import unittest
from fastapi.testclient import TestClient
from backend.mini_auth import KIND, GuestStore, MiniError, WechatVerifier, provision, load_config
from backend.mini_api import MiniGateway
from backend import test_map_ocr_production as ocr_fixture
from backend.test_map_recognition import picture

PREFIX = '/api/mini/v1'


class MiniProductionTests(unittest.TestCase):
    def setUp(self):
        self.fixture = ocr_fixture.OcrProductionTests(); self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        state = provision(root/'guests')
        secret = root/'secret'; secret.write_text('fixture-secret-no-real-credential'); secret.chmod(0o600)
        path = root/'config.json'
        path.write_text(json.dumps({'kind': KIND, 'state_dir': str(state), 'appid': 'wx0000000000000000',
                                    'app_secret_file': str(secret), 'image_policy': 'private_unmoderated'})); path.chmod(0o600)
        self.config = load_config(path)
        self.verifier = patch.object(WechatVerifier, '__call__', return_value='explicit-platform-fixture')
        self.verifier.start(); self.addCleanup(self.verifier.stop)
        f = self.fixture
        self.service = f.service
        app = MiniGateway(f.app, config=self.config, source=f.app.state, service=self.service, origin='https://racepick.cn', production=True)
        self.client = TestClient(app, base_url='https://racepick.cn', client=('127.0.0.1', 60000))
        self.client.headers.update({'X-Forwarded-Proto': 'https', 'X-Real-IP': '192.0.2.8'})
        self.addCleanup(self.client.close)
        r = self.client.post(PREFIX+'/session', json={'code': 'fixture-code', 'client_schema': 1, 'request_key': 'fixture-login-key'})
        self.assertEqual(r.status_code, 200, r.text)
        self.client.headers['Authorization'] = 'Bearer '+r.json()['token']
        self.catalog = self.client.get(PREFIX+'/map-recognition/catalog?server=cn').json()

    def upload(self, key='production-shape-upload'):
        return self.client.post(PREFIX+'/map-recognition/jobs', params={'server': 'cn', 'catalog_version': self.catalog['catalog_version'], 'request_key': key},
                                files={'image': ('fixture.png', picture(), 'image/png')})

    def test_native_uses_production_catalog_and_web_ip_budget(self):
        before = self.fixture.app.state.score_versions.current()
        job = self.upload(); self.assertEqual(job.status_code, 202, job.text)
        with self.service.store.connect() as db:
            row = dict(db.execute('SELECT * FROM jobs WHERE id=?', (job.json()['id'],)).fetchone())
        self.assertEqual(json.loads(row['catalog'])['version'], self.catalog['catalog_version'])
        self.assertTrue(row['owner'].startswith('mini-v1:'))
        self.service.store.fail_pending('fixture completion')
        # Nineteen website uploads + one native upload consume the SAME trusted-IP 20/10min budget.
        for _ in range(19):
            r = self.fixture.upload(); self.assertEqual(r.status_code, 202, r.text)
            self.service.store.fail_pending('fixture completion')
        self.assertEqual(self.upload('another-native-upload').status_code, 429)
        self.assertEqual(before, self.fixture.app.state.score_versions.current())

    def test_trusted_proxy_and_activity_change_are_enforced(self):
        self.assertEqual(self.client.get(PREFIX+'/snapshot?server=cn', headers={'X-Real-IP': 'invalid'}).status_code, 400)
        self.assertEqual(self.client.get(PREFIX+'/snapshot?server=cn', headers={'X-Forwarded-Proto': 'http'}).status_code, 400)
        job = self.upload().json()['id']
        real = self.service.provider
        self.service.provider = lambda server: {**real(server), 'version': '0'*64}
        self.assertEqual(self.client.get(PREFIX+'/map-recognition/jobs/'+job,
            params={'server': 'cn', 'catalog_version': self.catalog['catalog_version']}).status_code, 409)

    def test_shared_queue_wait_expiry_and_media_metadata_retention(self):
        job = self.upload().json()['id']
        with self.service.store.connect() as db:
            db.execute('UPDATE jobs SET created=? WHERE id=?', (time.time()-121, job))
        self.service.store.expire_pending()
        row = self.service.store.get(self.config['store'].authenticate(self.client.headers['Authorization'])['owner'], job, 'cn')
        self.assertEqual(row['state'], 'failed')
        self.assertFalse(self.service.store.image_path(job).exists())
        with self.service.store.connect() as db:
            db.execute('UPDATE jobs SET expires=? WHERE id=?', (time.time()-601, job))
        self.service.store.cleanup()
        with self.service.store.connect() as db:
            self.assertIsNone(db.execute('SELECT id FROM jobs WHERE id=?', (job,)).fetchone())


class WechatProviderTests(unittest.TestCase):
    def test_fixed_host_bounded_responses_and_sanitized_platform_errors(self):
        provider = WechatVerifier('wx0000000000000000', 'fixture-only-secret')
        for body, status in [(b'[]',503), (b'x'*8193,503), (b'not-json',503),
                             (b'{"errcode":40029}',401), (b'{"errcode":45011}',429), (b'{"errcode":-1}',503)]:
            response = Mock(); response.read.return_value = body
            opener = Mock(); opener.open.return_value.__enter__ = Mock(return_value=response)
            opener.open.return_value.__exit__ = Mock(return_value=False)
            with patch('backend.mini_auth.build_opener', return_value=opener):
                with self.assertRaises(MiniError) as caught:
                    provider('fixture-code')
            self.assertEqual(caught.exception.status,status)
            self.assertNotIn('fixture-only-secret',str(caught.exception))
            self.assertTrue(opener.open.call_args.args[0].full_url.startswith('https://api.weixin.qq.com/sns/jscode2session?'))
            self.assertEqual(response.read.call_args.args[0],8193)

    def test_private_state_requires_explicit_schema_and_does_not_overwrite(self):
        with tempfile.TemporaryDirectory() as root:
            state=provision(Path(root)/'guests')
            with self.assertRaises(ValueError): provision(state)
            with GuestStore(state).connect() as db: db.execute('UPDATE meta SET version=2')
            with self.assertRaises(ValueError): GuestStore(state)
