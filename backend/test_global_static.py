"""Local global reference data must not replace the mainland API data pair."""
import json
from pathlib import Path
import tempfile
import unittest

from fastapi.testclient import TestClient
from backend.app import create_app

ROOT = Path(__file__).resolve().parents[1]


class GlobalStaticTests(unittest.TestCase):
    def test_local_assets_keep_both_data_pairs_distinct(self):
        with tempfile.TemporaryDirectory(prefix='racepick-global-assets-') as folder:
            with TestClient(create_app(Path(folder)), base_url='http://127.0.0.1:8000') as client:
                self.assertEqual(client.get('/?server=global').status_code, 200)
                pair = {}
                for name in ('cars.global.json', 'gauntlet_data.global.json'):
                    response = client.get('/' + name)
                    self.assertEqual(response.status_code, 200, response.text)
                    pair[name] = response.json()
                    self.assertEqual(pair[name]['_meta']['server_id'], 'global')
                self.assertEqual(pair['cars.global.json']['_meta'], pair['gauntlet_data.global.json']['_meta'])
                self.assertEqual(client.get('/global-data-manifest.json').status_code, 200)
                for name in ('cars.json', 'gauntlet_data.json'):
                    response = client.get('/' + name)
                    self.assertEqual(response.status_code, 200)
                    self.assertEqual(response.json(), json.loads((ROOT / name).read_text(encoding='utf-8')))
                self.assertEqual(client.get('/_star_curve_fit.py').status_code, 404)
                self.assertEqual(client.get('/maintenance-car-identities.json').status_code, 404)
                health = client.get('/api/health').json()
                self.assertEqual(health['mode'], 'local')
                self.assertEqual(health['schema'], 6)


if __name__ == '__main__':
    unittest.main()
