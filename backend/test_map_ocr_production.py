"""Production-bound API integration in disposable fixtures, never a real server."""
from pathlib import Path
import json
import secrets
import time
import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from backend import test_global_score_production as fixtures
from backend.global_score_production import migrate
from backend.map_ocr_production import provision,ProductionRecognitionService
from backend.production import make_app
from backend.test_map_recognition import picture

class OcrProductionTests(unittest.TestCase):
    def setUp(self):
        self.fixture=fixtures.GlobalScoreProductionTests();self.fixture.setUp();self.addCleanup(self.fixture.tearDown)
        f=self.fixture;migrate(f.config,f.source,f.dataset,f.version)
        self.path=provision(f.path/'map-recognition')
        with patch.dict('os.environ',{'RACEPICK_MAP_RECOGNITION_CONFIG':str(self.path)}):self.app=make_app(f.config,'unused')
        self.client=TestClient(self.app,base_url='https://racepick.cn',client=('127.0.0.1',50000))
        self.client.headers.update({'X-Forwarded-Proto':'https','X-Real-IP':'192.0.2.8','Origin':'https://racepick.cn'})
        self.client.headers['X-CSRF-Token']=self.client.get('/api/auth/me').json()['csrf'];self.addCleanup(self.client.close)
        self.service=self.app.state.map_recognition
        run='fixture-run';self.service.root.joinpath('supervisor-state.json').write_text(json.dumps({'state':'running','updated':time.time(),'run_id':run}))
        self.service.root.joinpath('worker-state.json').write_text(json.dumps({'state':'ready','run_id':run}))
    def upload(self):
        cat=self.client.get('/api/map-recognition/catalog').json()
        return self.client.post('/api/map-recognition/jobs',params={'server':'cn','catalog_version':cat['version'],'request_key':secrets.token_hex(16)},
                                content=picture(),headers={'Content-Type':'image/png'})
    def test_active_catalog_private_queue_and_existing_features(self):
        cat=self.client.get('/api/map-recognition/catalog?server=global').json()
        self.assertEqual(len(cat['maps']),44)
        before=self.app.state.score_versions.current();global_before=self.app.state.global_score_versions.current()
        response=self.upload();self.assertEqual(response.status_code,202,response.text)
        row=self.service.store.get(self.service.store.claim()['owner'],response.json()['id'],'cn')
        self.assertEqual(json.loads(row['catalog'])['version'],row['version'])
        self.assertEqual(self.client.get('/api/map-recognition/examples').status_code,404)
        self.assertEqual(self.client.get('/map-recognition/media/'+row['id']+'.image').status_code,404)
        self.assertIn('id="coverageEntryNew">新功能',self.client.get('/').text)
        self.assertIn('id="mapRecognitionHost"',self.client.get('/').text)
        self.assertEqual(before,self.app.state.score_versions.current());self.assertEqual(global_before,self.app.state.global_score_versions.current())
        with self.app.state.store.connect() as db:self.assertFalse(self.app.state.global_score_versions.enabled(db))
    def test_stale_catalog_result_rejected_and_bad_proxy_blocked(self):
        response=self.upload();self.assertEqual(response.status_code,202,response.text);job=response.json()['id']
        real=self.service.provider
        def changed(server):return {**real(server),'version':'0'*64}
        self.service.provider=changed
        self.assertEqual(self.client.get('/api/map-recognition/jobs/'+job).status_code,409)
        self.assertEqual(self.client.get('/api/map-recognition/catalog',headers={'X-Real-IP':'invalid'}).status_code,400)
        self.assertEqual(self.client.post('/api/map-recognition/jobs',headers={'Content-Type':'image/png','Origin':'https://evil.invalid'},content=picture()).status_code,403)
    def test_ip_quota_survives_new_sessions_and_worker_unavailability(self):
        for _ in range(20):
            response=self.upload();self.assertEqual(response.status_code,202,response.text)
            self.service.store.fail_pending('fixture completed')
            self.client.cookies.clear();self.client.headers['X-CSRF-Token']=self.client.get('/api/auth/me').json()['csrf']
        self.assertEqual(self.upload().status_code,429)
        self.service.root.joinpath('supervisor-state.json').write_text('{}')
        self.assertEqual(self.upload().status_code,503)
    def test_expiry_removes_metadata_and_only_owned_media(self):
        response=self.upload();job=response.json()['id'];keep=self.service.root/'media/keep.txt';keep.write_text('keep')
        with self.service.store.connect() as db:db.execute('UPDATE jobs SET expires=? WHERE id=?',(time.time()-1000,job))
        self.service.store.cleanup()
        self.assertFalse(self.service.store.image_path(job).exists());self.assertEqual(keep.read_text(),'keep')
        with self.service.store.connect() as db:self.assertEqual(db.execute('SELECT count(*) FROM jobs').fetchone()[0],0)
        with self.assertRaises(ValueError):provision(self.service.root)

    def test_disk_and_extreme_aspect_limits(self):
        from collections import namedtuple
        usage=namedtuple('usage','total used free')
        with patch('backend.map_recognition.shutil.disk_usage',return_value=usage(1000,999,1)):
            self.assertEqual(self.upload().status_code,503)
        oversized=self.service.store.media/('a'*32+'.image')
        with oversized.open('wb') as stream:stream.truncate(129*1024*1024)
        self.assertEqual(self.upload().status_code,503);oversized.unlink()
        import io
        from PIL import Image
        from backend.map_recognition import validate_image,RecognitionError
        stream=io.BytesIO();Image.new('RGB',(32,10000)).save(stream,format='PNG')
        with self.assertRaises(RecognitionError):validate_image(stream.getvalue(),'image/png')

if __name__=='__main__':unittest.main()
