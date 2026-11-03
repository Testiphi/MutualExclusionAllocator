"""Native adapter fixtures: actual version stores/shared queue; no WeChat or production calls."""
from pathlib import Path
from unittest.mock import Mock, patch
import hashlib
import io
import json
import secrets
import shutil
import tempfile
import time
import unittest
from PIL import Image
from fastapi.testclient import TestClient
from backend.app import create_app, ROOT
from backend.map_recognition import RecognitionService, MAX_BYTES
from backend.mini_auth import GuestStore, MiniError, provision as provision_guests
from backend.score_repository import provision as provision_lab

PREFIX = '/api/mini/v1'


def picture(color='red', size=(640, 360)):
    stream = io.BytesIO()
    Image.new('RGB', size, color).save(stream, format='PNG')
    return stream.getvalue()


class MiniApiTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='racepick-mini-fixture-')
        self.guests = GuestStore(provision_guests(Path(self.temp.name)/'native'))
        self.lab = provision_lab(ROOT)
        (self.lab/'reference').mkdir()
        names = ['cars.json', 'gauntlet_data.json', 'cars.global.json', 'gauntlet_data.global.json', 'global-data-manifest.json']
        self.raw = {n: (ROOT/n).read_bytes() for n in names}
        for n, raw in self.raw.items():
            (self.lab/'reference'/n).write_bytes(raw)
        (self.lab/'.racepick-map-demo.json').write_text(json.dumps({'kind': 'racepick-local-map-recognition'}))
        config = {'root': str(self.lab), 'reference': str(self.lab/'reference'), 'models': {}, 'vendor': 'unused',
                  'reference_sha256': {n: hashlib.sha256(raw).hexdigest() for n, raw in self.raw.items()}, 'examples': {}}
        self.ocr_config = self.lab/'config.json'
        self.ocr_config.write_text(json.dumps(config))
        self.verifier = Mock(side_effect=lambda code: 'fixture-subject-'+code)
        self.options = {'store': self.guests, 'verifier': self.verifier, 'fixture': True, 'image_policy': 'private_unmoderated'}
        self.start = patch.object(RecognitionService, 'start', lambda service: None)
        self.health = patch.object(RecognitionService, 'health', lambda service: 'ready')
        self.start.start(); self.health.start()
        self.app = create_app(self.lab/'accounts', 'http://127.0.0.1:8043', map_recognition=self.ocr_config,
                              score_version_lab=self.lab, contributions=True, coverage=True, mini_config=self.options)
        self.client = TestClient(self.app, base_url='http://127.0.0.1:8043', client=('127.0.0.1', 12345))
        self.client.__enter__()
        self.session = self.login('fixture-code-1')
        self.auth = {'Authorization': 'Bearer '+self.session['token']}
        self.catalog = self.client.get(PREFIX+'/map-recognition/catalog', params={'server': 'cn'}, headers=self.auth).json()
        self.queue = self.app.state.map_recognition.store
        self.before = (self.app.state.score_versions.current(), self.app.state.global_score_versions.current())

    def tearDown(self):
        self.client.__exit__(None, None, None)
        self.start.stop(); self.health.stop()
        # Only this test's freshly provisioned random laboratory is removed.
        self.assertEqual(self.lab.parent, ROOT.parent/'.score-version-sandboxes')
        shutil.rmtree(self.lab)
        self.temp.cleanup()

    def login(self, code, key='session-fixture-0001'):
        response = self.client.post(PREFIX+'/session', json={'code': code, 'client_schema': 1, 'request_key': key})
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def params(self, key=None, **extra):
        params = {'server': 'cn', 'catalog_version': self.catalog['catalog_version'], **extra}
        if key is not None:
            params['request_key'] = key
        return params

    def upload(self, key='upload-fixture-0001', raw=None, **kwargs):
        return self.client.post(PREFIX+'/map-recognition/jobs', params=self.params(key), headers=self.auth,
                                files={'image': ('shot.png', picture() if raw is None else raw, 'image/png')}, **kwargs)

    def query(self, job_id, auth=None, **extra):
        return self.client.get(PREFIX+'/map-recognition/jobs/'+job_id, params=self.params(**extra), headers=auth or self.auth)

    def recover(self, key='upload-fixture-0001'):
        return self.client.get(PREFIX+'/map-recognition/jobs/by-request', params=self.params(key), headers=self.auth)

    def test_snapshot_raw_bytes_and_website_state_unchanged(self):
        for server, names in [('cn', ['cars.json', 'gauntlet_data.json']), ('global', ['cars.global.json', 'gauntlet_data.global.json', 'global-data-manifest.json'])]:
            r = self.client.get(PREFIX+'/snapshot', params={'server': server}, headers=self.auth)
            self.assertEqual(r.status_code, 200, r.text)
            self.assertEqual(r.headers['cache-control'], 'no-store')
            value = r.json(); self.assertEqual(value['identity'], self.session['identity'])
            self.assertEqual(set(value['files']), set(names))
            for n in names:
                entry = value['files'][n]
                self.assertEqual(entry['text'].encode('utf-8'), self.raw[n])
                self.assertEqual(entry['sha256'], hashlib.sha256(self.raw[n]).hexdigest())
                self.assertEqual(entry['bytes'], len(self.raw[n]))
        self.assertEqual(self.before, (self.app.state.score_versions.current(), self.app.state.global_score_versions.current()))
        with self.app.state.store.connect() as db:
            self.assertEqual(db.execute('SELECT count(*) FROM users').fetchone()[0], 0)
            self.assertEqual(db.execute('SELECT count(*) FROM sessions').fetchone()[0], 0)

    def test_session_response_loss_returns_same_token_and_restart_preserves_auth(self):
        again = self.login('fixture-code-1')
        self.assertEqual(again['token'], self.session['token'])
        self.assertEqual(self.verifier.call_count, 1)
        self.assertLessEqual(again['expires_at']-time.time(), 3600)
        reopened = GuestStore(self.guests.root)
        self.assertEqual(reopened.authenticate(self.auth['Authorization'])['identity'], self.session['identity'])
        r = self.client.post(PREFIX+'/session', json={'code': 'fixture-code-1', 'client_schema': 1, 'request_key': 'other-fixture-key'})
        self.assertEqual(r.status_code, 409)
        self.assertNotIn('session_key', json.dumps(again))

    def test_uncertain_code_not_replayed_to_platform(self):
        self.verifier.side_effect = MiniError(503, 'PLATFORM_UNAVAILABLE', 'fixture outage')
        body = {'code': 'fixture-code-uncertain', 'client_schema': 1, 'request_key': 'fixture-uncertain-key'}
        self.assertEqual(self.client.post(PREFIX+'/session', json=body).status_code, 503)
        self.assertEqual(self.client.post(PREFIX+'/session', json=body).status_code, 409)
        self.assertEqual(self.verifier.call_count, 2)

    def test_session_expiry_revocation_and_invalid_identity(self):
        self.assertEqual(self.query('0'*32, auth={'Authorization': 'Bearer invalid'}).status_code, 401)
        self.assertEqual(self.client.delete(PREFIX+'/session', headers=self.auth).status_code, 200)
        self.assertEqual(self.client.get(PREFIX+'/snapshot?server=cn', headers=self.auth).status_code, 401)
        other = self.login('fixture-code-expiry')
        with self.guests.connect() as db:
            db.execute('UPDATE sessions SET expires=? WHERE sid=?', (int(time.time())-1, other['token'][:48]))
        self.assertEqual(self.client.get(PREFIX+'/snapshot?server=cn', headers={'Authorization': 'Bearer '+other['token']}).status_code, 401)

    def test_web_boundaries_and_native_cookie_origin_rejection(self):
        self.assertEqual(self.client.post('/api/map-recognition/jobs', content=picture(), headers={'Content-Type': 'image/png', **self.auth}).status_code, 403)
        self.assertEqual(self.client.get(PREFIX+'/snapshot?server=cn', headers={**self.auth, 'Origin': 'https://evil.example'}).status_code, 403)
        self.assertEqual(self.client.get(PREFIX+'/snapshot?server=cn', headers={**self.auth, 'Cookie': 'racepick_local_session=x'}).status_code, 403)
        self.assertEqual(self.client.get(PREFIX+'/snapshot?server=cn', headers={**self.auth, 'Host': 'evil.example'}).status_code, 400)
        self.assertEqual(self.client.options(PREFIX+'/session').status_code, 403)

    def test_upload_response_loss_same_key_same_file_and_conflict(self):
        first = self.upload(); self.assertEqual(first.status_code, 202, first.text)
        job = first.json()['id']
        self.assertEqual(self.upload().json()['id'], job)
        self.assertEqual(self.recover().json()['id'], job)
        self.assertEqual(self.upload(raw=picture('blue')).status_code, 409)
        self.assertEqual(len(list(self.queue.media.glob('*.image'))), 1)
        self.assertEqual(self.query(job).json()['state'], 'queued')

    def test_recovery_distinguishes_absent_reading_interrupted_and_found(self):
        self.assertEqual(self.recover().json()['recovery'], 'not_found')
        owner = self.guests.authenticate(self.auth['Authorization'])['owner']
        with self.guests.connect() as db:
            db.execute('INSERT INTO uploads VALUES (?,?,?,?,?,?)', (owner, 'upload-fixture-0001', self.catalog['catalog_version'], 'reading', 'lease', time.time()))
        reading = self.recover()
        self.assertEqual(reading.json()['recovery'], 'reading')
        self.assertEqual(reading.headers['retry-after'], '2')
        self.assertEqual(self.upload().status_code, 409)
        with self.guests.connect() as db:
            db.execute('UPDATE uploads SET updated=?', (time.time()-31,))
        self.assertEqual(self.recover().json()['recovery'], 'interrupted')
        self.assertEqual(self.upload().status_code, 202)
        self.assertEqual(self.recover().json()['recovery'], 'found')

    def test_shared_web_native_global_capacity_and_owner_limit(self):
        for i in range(8):
            self.queue.create('website-owner-'+str(i), 'website-key-'+str(i).zfill(16), 'cn', self.catalog['catalog_version'], picture(), 'image/png')
        limited = self.upload(); self.assertEqual(limited.status_code, 429)
        self.assertEqual(limited.headers['retry-after'], '5')
        self.assertEqual(self.queue.path, self.app.state.map_recognition.store.path)
        with self.queue.connect() as db:
            self.assertEqual(db.execute('SELECT count(*) FROM jobs').fetchone()[0], 8)

    def test_cross_owner_server_and_catalog_change(self):
        job = self.upload().json()['id']
        other = self.login('fixture-code-other')
        self.assertEqual(self.query(job, {'Authorization': 'Bearer '+other['token']}).status_code, 403)
        self.assertEqual(self.query(job, server='global').status_code, 403)
        self.assertEqual(self.query(job, catalog_version='0'*64).status_code, 409)
        self.assertEqual(self.client.get(PREFIX+'/snapshot?server=unknown', headers=self.auth).status_code, 400)
        self.assertEqual(self.client.get(PREFIX+'/map-recognition/catalog?server=global', headers=self.auth).status_code, 403)

    def test_cancel_is_idempotent_and_cannot_publish_late_result(self):
        job = self.upload().json()['id']; self.queue.claim()
        path = PREFIX+'/map-recognition/jobs/'+job
        for _ in range(2):
            self.assertEqual(self.client.delete(path, params=self.params(), headers=self.auth).json()['state'], 'cancelled')
        self.queue.finish(job, result={'not': 'publishable'})
        self.assertEqual(self.query(job).json()['state'], 'cancelled')
        self.assertFalse(self.queue.image_path(job).exists())

    def test_expired_task_is_410_and_private_media_removed(self):
        job = self.upload().json()['id']
        with self.queue.connect() as db:
            db.execute('UPDATE jobs SET expires=? WHERE id=?', (time.time()-1, job))
        self.assertEqual(self.query(job).status_code, 410)
        self.assertEqual(self.recover().status_code, 410)
        self.assertFalse(self.queue.image_path(job).exists())

    def test_multipart_field_count_mime_pixel_and_envelope_limits(self):
        path = PREFIX+'/map-recognition/jobs'
        self.assertEqual(self.upload(data={'server': 'cn'}).status_code, 400)
        self.assertEqual(self.client.post(path, params=self.params('upload-second-field'), headers=self.auth,
            files=[('image', ('a.png', picture(), 'image/png')), ('image', ('b.png', picture(), 'image/png'))]).status_code, 400)
        self.assertEqual(self.client.post(path, params=self.params('upload-unsupported'), headers=self.auth,
            files={'image': ('x.txt', b'hello', 'text/plain')}).status_code, 415)
        self.assertEqual(self.upload(raw=picture(size=(6000,3000))).status_code, 422)
        self.assertEqual(self.upload(raw=picture()+b'0'*MAX_BYTES).status_code, 413)
        self.assertEqual(self.client.post(path, params=self.params('upload-body-big-key'), headers={**self.auth,'Content-Type':'multipart/form-data; boundary=x'}, content=b'0'*(MAX_BYTES+65537)).status_code, 413)

    def test_sanitized_result_retains_five_slots_without_raw_ocr(self):
        job = self.upload().json()['id']; self.queue.claim()
        raw = {'schema_version': 1, 'server': 'cn', 'catalog_version': self.catalog['catalog_version'], 'status': 'partial',
               'slots': [{'slot': i, 'state': 'unresolved', 'observed': ['unrelated-sensitive-text'], 'big': 'guess', 'small': 'guess'} for i in range(1,6)]}
        raw['slots'][0].update(state='matched', **self.catalog['maps'][0])
        self.queue.finish(job, result=raw)
        value = self.query(job).json()['result']
        self.assertEqual(len(value['slots']), 5)
        self.assertNotIn('unrelated-sensitive-text', json.dumps(value))
        self.assertIsNone(value['slots'][1]['big'])
        self.assertEqual(value['slots'][0]['big'], self.catalog['maps'][0]['big'])

    def test_disabled_by_default_and_no_implicit_guest_provision(self):
        with tempfile.TemporaryDirectory() as root:
            app = create_app(Path(root), 'http://127.0.0.1:8994')
            with TestClient(app, base_url='http://127.0.0.1:8994') as client:
                self.assertEqual(client.post(PREFIX+'/session', json={}).status_code, 404)
                self.assertEqual(client.get(PREFIX+'/snapshot?server=cn').status_code, 404)
            self.assertFalse((Path(root)/'guests.sqlite3').exists())
        with self.assertRaises(ValueError):
            create_app(production=True, mini_config=self.options)

    def test_worker_unavailable_then_original_key_can_retry(self):
        with patch.object(RecognitionService, 'health', return_value='unavailable'):
            self.assertEqual(self.upload().status_code, 503)
        self.assertEqual(self.recover().json()['recovery'], 'interrupted')
        self.assertEqual(self.upload().status_code, 202)

    def test_session_issuance_budget_and_query_budget(self):
        for i in range(9):
            self.login('fixture-code-budget-'+str(i))
        r = self.client.post(PREFIX+'/session', json={'code': 'over-budget', 'client_schema': 1, 'request_key': 'session-over-budget'})
        self.assertEqual(r.status_code, 429)
        self.assertGreater(int(r.headers['retry-after']), 0)

    def test_generic_binary_part_still_requires_actual_image_format(self):
        r = self.client.post(PREFIX+'/map-recognition/jobs', params=self.params('upload-binary-part1'), headers=self.auth,
                             files={'image': ('wx-temp-file', picture(), 'application/octet-stream')})
        self.assertEqual(r.status_code, 202, r.text)

    def test_upload_disconnect_can_resume_by_original_key(self):
        import asyncio
        import httpx
        from starlette.requests import ClientDisconnect
        async def run():
            async def interrupted():
                yield b'partial multipart data'
                raise ClientDisconnect()
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=self.app, client=('127.0.0.1', 12345)), base_url='http://127.0.0.1:8043') as client:
                return await client.post(PREFIX+'/map-recognition/jobs', params=self.params('upload-disconnect1'),
                                         headers={**self.auth,'Content-Type':'multipart/form-data; boundary=fixture'}, content=interrupted())
        self.assertEqual(asyncio.run(run()).status_code, 503)
        r = self.client.get(PREFIX+'/map-recognition/jobs/by-request', params=self.params('upload-disconnect1'), headers=self.auth)
        self.assertEqual(r.json()['recovery'], 'interrupted')
        self.assertEqual(self.upload(key='upload-disconnect1').status_code, 202)

    def test_local_native_metadata_grace_matches_production_policy(self):
        job = self.upload().json()['id']
        with self.queue.connect() as db:
            db.execute('UPDATE jobs SET expires=? WHERE id=?', (time.time()-601,job))
        self.assertEqual(self.recover().status_code,410)
        with self.queue.connect() as db:
            self.assertIsNone(db.execute('SELECT id FROM jobs WHERE id=?',(job,)).fetchone())
