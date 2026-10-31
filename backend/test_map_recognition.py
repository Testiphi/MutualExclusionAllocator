"""HTTP boundaries and private-job lifecycle; all state is disposable fixtures."""
from pathlib import Path
from unittest.mock import patch,Mock
import hashlib
import io
import json
import tempfile
import time
import unittest
from PIL import Image
from fastapi.testclient import TestClient
from backend.app import create_app,ROOT
from backend.map_recognition import RecognitionService,MAX_BYTES


def picture(color='red'):
    buffer=io.BytesIO();Image.new('RGB',(640,360),color).save(buffer,format='PNG');return buffer.getvalue()


class RecognitionHttpTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='racepick-recognition-tests-')
        self.root=Path(self.temp.name)/'isolated';self.root.mkdir();(self.root/'reference').mkdir()
        (self.root/'.racepick-map-demo.json').write_text(json.dumps({'kind':'racepick-local-map-recognition'}))
        files={name:(ROOT/name).read_bytes() for name in ['cars.json','gauntlet_data.json','cars.global.json','gauntlet_data.global.json','global-data-manifest.json']}
        for name,raw in files.items():(self.root/'reference'/name).write_bytes(raw)
        config={'root':str(self.root),'reference':str(self.root/'reference'),
                'reference_sha256':{n:hashlib.sha256(b).hexdigest() for n,b in files.items()},'models':{},'vendor':'unused','examples':{}}
        self.config=self.root/'config.json';self.config.write_text(json.dumps(config))
        self.start_patch=patch.object(RecognitionService,'start',lambda service:None);self.start_patch.start()
        self.app=create_app(data_dir=self.root/'accounts',origin='http://127.0.0.1:8991',map_recognition=self.config)
        self.client=TestClient(self.app,base_url='http://127.0.0.1:8991');self.client.__enter__()
        me=self.client.get('/api/auth/me').json();self.csrf=me['csrf']
        self.catalog=self.client.get('/api/map-recognition/catalog?server=cn').json()
        self.headers={'Origin':'http://127.0.0.1:8991','Content-Type':'image/png','X-CSRF-Token':self.csrf}
        self.store=self.app.state.map_recognition.store

    def tearDown(self):
        self.client.__exit__(None,None,None);self.start_patch.stop();self.temp.cleanup()

    def upload(self,key='fixture-request-000001',raw=None,**params):
        return self.client.post('/api/map-recognition/jobs',params={'server':'cn','catalog_version':self.catalog['version'],'request_key':key,**params},
                                content=picture() if raw is None else raw,headers=self.headers)

    def get(self,job,server='cn'):
        return self.client.get('/api/map-recognition/jobs/'+job+'?server='+server)

    def test_valid_private_upload_and_catalog_version(self):
        response=self.upload();self.assertEqual(response.status_code,202,response.text)
        job=response.json()['id'];status=self.get(job).json();self.assertEqual(status['state'],'queued')
        self.assertEqual(status['catalog_version'],self.catalog['version'])
        self.assertNotIn('owner',status);self.assertNotIn('path',status)
        self.assertEqual(self.store.image_path(job).read_bytes(),picture())

    def test_homepage_has_only_feature_mount_no_demo_instructions(self):
        html=self.client.get('/').text
        self.assertIn('id="mapRecognitionHost"',html)
        self.assertNotIn('id="mapRecognitionOpen"',html)
        self.assertNotIn('本地验收',html)

    def test_retry_is_idempotent_but_same_key_different_image_is_conflict(self):
        first=self.upload();second=self.upload()
        self.assertEqual(first.json()['id'],second.json()['id'])
        self.assertEqual(self.upload(raw=picture('blue')).status_code,409)
        self.assertEqual(len(list(self.store.media.glob('*.image'))),1)

    def test_cross_session_and_cross_server_reads_are_not_visible(self):
        job=self.upload().json()['id'];self.assertEqual(self.get(job,'global').status_code,404)
        self.client.cookies.clear();self.client.get('/api/auth/me')
        self.assertEqual(self.get(job).status_code,404)

    def test_wrong_origin_csrf_and_content_type_do_not_create_jobs(self):
        params={'server':'cn','catalog_version':self.catalog['version'],'request_key':'bad-boundary-request-01'}
        for changes in [{'Origin':'https://example.invalid'},{'X-CSRF-Token':'incorrect'},{'Content-Type':'application/json'}]:
            headers={**self.headers,**changes}
            self.assertEqual(self.client.post('/api/map-recognition/jobs',params=params,content=picture(),headers=headers).status_code,403)
        self.assertEqual(list(self.store.media.iterdir()),[])
        # The binary exception is not a global relaxation of existing APIs.
        self.assertEqual(self.client.post('/api/auth/login',content=picture(),headers=self.headers).status_code,403)

    def test_invalid_or_oversize_image_is_rejected(self):
        self.assertEqual(self.upload(raw=b'not an image').status_code,422)
        self.assertEqual(self.upload(raw=b'x'*(MAX_BYTES+1)).status_code,413)

    def test_declared_mime_must_match_actual_image(self):
        self.headers['Content-Type']='image/jpeg';self.assertEqual(self.upload().status_code,422)

    def test_example_uses_actual_format_even_if_legacy_filename_says_png(self):
        buffer=io.BytesIO();Image.new('RGB',(640,360),'blue').save(buffer,format='JPEG');raw=buffer.getvalue()
        directory=self.root/'examples';directory.mkdir();(directory/'legacy.png').write_bytes(raw)
        self.app.state.map_recognition.config['examples']={'jpeg':{'title':'JPEG样例','filename':'legacy.png','sha256':hashlib.sha256(raw).hexdigest()}}
        response=self.client.get('/api/map-recognition/examples/jpeg')
        self.assertEqual(response.status_code,200);self.assertEqual(response.headers['content-type'],'image/jpeg')
        self.assertEqual(response.content,raw)

    def test_current_catalog_binding_is_required(self):
        self.assertEqual(self.upload(catalog_version='0'*64).status_code,409)
        p=self.root/'reference/gauntlet_data.json';p.write_bytes(p.read_bytes()+b' ')
        self.assertEqual(self.client.get('/api/map-recognition/catalog?server=cn').status_code,409)

    def test_only_two_outstanding_jobs_per_session(self):
        self.assertEqual(self.upload(key='request-one-00000001').status_code,202)
        self.assertEqual(self.upload(key='request-two-00000002').status_code,202)
        self.assertEqual(self.upload(key='request-three-000003').status_code,429)

    def test_cancelled_running_job_cannot_publish_late_result(self):
        job=self.upload().json()['id'];claimed=self.store.claim();self.assertEqual(claimed['id'],job)
        response=self.client.delete('/api/map-recognition/jobs/'+job+'?server=cn',headers={**self.headers,'Content-Type':'application/json'})
        self.assertEqual(response.status_code,200);self.assertFalse(self.store.image_path(job).exists())
        self.store.finish(job,result={'should_not_publish':True})
        status=self.get(job).json();self.assertEqual(status['state'],'cancelled');self.assertIsNone(status['result'])

    def test_expiry_deletes_only_owned_temporary_media(self):
        job=self.upload().json()['id'];sentinel=self.store.media/'unrelated-keep.txt';sentinel.write_text('keep')
        with self.store.connect() as db:db.execute('UPDATE jobs SET expires=? WHERE id=?',(time.time()-1,job))
        self.assertEqual(self.get(job).status_code,410)
        self.assertFalse(self.store.image_path(job).exists());self.assertEqual(sentinel.read_text(),'keep')

    def test_worker_exit_marks_pending_failed_and_rejects_new_work(self):
        job=self.upload().json()['id'];self.app.state.map_recognition.process=Mock(poll=lambda:1)
        self.assertEqual(self.get(job).json()['state'],'failed')
        self.assertEqual(self.upload(key='after-worker-exit-01').status_code,503)

    def test_feature_disabled_and_production_guard(self):
        default=create_app(data_dir=Path(self.temp.name)/'default-accounts',origin='http://127.0.0.1:8992')
        with TestClient(default,base_url='http://127.0.0.1:8992') as client:
            self.assertEqual(client.get('/api/map-recognition/catalog').status_code,404)
            self.assertEqual(client.get('/map_recognition.js').status_code,404)
            self.assertNotIn('mapRecognitionOpen',client.get('/').text)
        forbidden=Path(self.temp.name)/'not-created-production'
        with self.assertRaises(ValueError):create_app(data_dir=forbidden,origin='https://example.invalid',production=True,map_recognition=self.config)
        self.assertFalse(forbidden.exists())

    def test_integrated_review_keeps_existing_features_and_new_badge(self):
        from backend import score_repository
        with patch.object(score_repository,'LABS',Path(self.temp.name)/'review-labs'):
            lab=score_repository.provision(self.root/'reference')
            config={**self.app.state.map_recognition.config,'root':str(lab),'reference':str(lab/'reference'),'examples':{}}
            (lab/'reference').mkdir()
            for name in config['reference_sha256']:
                (lab/'reference'/name).write_bytes((self.root/'reference'/name).read_bytes())
            (lab/'.racepick-map-demo.json').write_text(json.dumps({'kind':'racepick-local-map-recognition'}))
            path=lab/'config.json';path.write_text(json.dumps(config))
            app=create_app(lab/'accounts',origin='http://127.0.0.1:8993',score_version_lab=lab,
                           map_recognition=path,contributions=True,coverage=True,feedback=True,notifications=True,usage=True)
            with TestClient(app,base_url='http://127.0.0.1:8993') as client:
                html=client.get('/').text
                self.assertIn('id="coverageEntryNew">新功能</span>',html)
                self.assertIn('id="mapRecognitionHost"',html)
                self.assertEqual(client.get('/score-table').status_code,200)
                self.assertEqual(client.get('/api/auth/me').status_code,200)
                cn=client.get('/api/map-recognition/catalog?server=cn').json()
                self.assertEqual(len(cn['maps']),83)
                self.assertEqual(client.get('/api/map-recognition/examples').json(),[])
                with app.state.store.connect() as db:
                    self.assertEqual(db.execute('SELECT count(*) FROM users').fetchone()[0],0)
            # A valid but different lab must never share this review's accounts/queue.
            other=score_repository.provision(self.root/'reference')
            with self.assertRaises(ValueError):
                create_app(lab/'accounts',score_version_lab=other,map_recognition=path)


if __name__=='__main__':unittest.main(verbosity=2)
