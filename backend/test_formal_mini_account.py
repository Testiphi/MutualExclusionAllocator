"""In-process verification of the formal account perimeter."""
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from backend import test_mini_accounts as fixture
from backend.mini_api import MiniGateway
from backend.production import formal_mini_config


class FormalMiniAccountTests(unittest.TestCase):
    def test_production_configuration_defaults_to_readonly(self):
        self.assertIsNone(formal_mini_config(None, '0'))
        with self.assertRaises(ValueError):
            formal_mini_config(None, '1')
        with patch('backend.mini_auth.load_config', return_value={'account_store': object(), 'image_policy': 'disabled'}):
            config = formal_mini_config('fixture.json', '0')
            self.assertTrue(config['formal_account'])
            self.assertTrue(config['account_a_only'])
            self.assertFalse(config['formal_profile_writes'])
        with patch('backend.mini_auth.load_config', return_value={'account_store': object(), 'image_policy': 'private_unmoderated'}):
            with self.assertRaises(ValueError):
                formal_mini_config('fixture.json', '1')

    def test_formal_gate_blocks_writes_before_authentication_and_excludes_extra_routes(self):
        f = fixture.NativeAccountTests()
        f.setUp()
        self.addCleanup(f.tearDown)
        config = {'store': f.guests, 'account_store': f.accounts, 'fixture': True,
                  'verifier': lambda code: code, 'image_policy': 'disabled',
                  'account_a_only': True, 'formal_account': True, 'formal_profile_writes': False}
        gateway = MiniGateway(f.app, config=config, source=f.app.state, service=None,
                              origin='http://127.0.0.1:8044', production=False)
        with TestClient(gateway, base_url='http://127.0.0.1:8044') as client:
            self.assertEqual(client.put(fixture.P+'/profile?server=cn', json={}).json()['code'],
                             'ACCOUNT_CLOUD_WRITE_DISABLED')
            self.assertEqual(client.post(fixture.P+'/auth/register', json={}).status_code, 404)
            self.assertEqual(client.get(fixture.P+'/submissions/catalog?server=cn').status_code, 404)
            self.assertEqual(client.get(fixture.P+'/profile?server=cn').status_code, 401)
