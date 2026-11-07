"""HTTP -> queue port -> sole fixture JobStore; platform/reviewers are synthetic."""
import hashlib
import json
import os
from pathlib import Path
import socket
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from backend.mini_auth import KIND,provision,WechatVerifier
from backend.mini_guest_service import FILES,load_snapshot,digest
from backend.mini_ocr_guest_service import make_app
from backend.map_recognition import JobStore
from backend.ocr_queue_bridge import QueueBridgeCore,QueueBridgeServer,QueueBridgeClient
from backend.test_image_safety_aliyun import image
from backend.test_ocr_queue_bridge import Reviewer

ROOT=Path(__file__).resolve().parents[1]
PREFIX='/api/mini/v1'


class OcrHttpTests(unittest.TestCase):
    use_unix=False
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='ocr-http-fixture-');self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name).resolve();self.snapshot=self.root/'snapshot';self.snapshot.mkdir()
        data_root=ROOT if (ROOT/FILES[0]).exists() else ROOT/'snapshot'
        records={}
        for name in FILES:
            raw=(data_root/name).read_bytes();(self.snapshot/name).write_bytes(raw)
            records[name]={'sha256':digest(raw),'bytes':len(raw)}
        (self.snapshot/'snapshot.json').write_text(json.dumps({'kind':'racepick-mini-guest-snapshot-v1','files':records}))
        source,_=load_snapshot(self.snapshot);info,contents=source.score_versions.current()
        self.catalog={'server':'cn','version':digest((info['id']+':').encode()+contents['gauntlet_data.json']),
            'maps':[{'big':r['大地图'],'small':r['小地图']} for r in json.loads(contents['gauntlet_data.json'])['tracks']]}
        self.queue=self.root/'queue';self.queue.mkdir(mode=0o700)
        (self.queue/'queue.json').write_text(json.dumps({'kind':'racepick-map-queue-v1'}))
        self.store=JobStore(self.queue,production=True);self.store.prepare_safety_schema()
        self.reviewer=Reviewer()
        self.core=QueueBridgeCore(self.store,self.reviewer,self.catalog,uploads_enabled=True,worker_health=lambda:'ready')
        def finish():self.reviewer.release.set();self.core.close()
        self.addCleanup(finish)
        self.state=provision(self.root/'guests')
        self.secret=self.root/'secret';self.secret.write_text('fixture-only-secret');self.secret.chmod(0o600)
        self.config=self.root/'guest.json'
        self.declaration={'kind':KIND,'state_dir':str(self.state),'appid':'wx'+'0'*16,
            'app_secret_file':str(self.secret),'image_policy':'aliyun_baseline','bridge_socket':'/run/local-fixture.sock'}
        self.platform=patch.object(WechatVerifier,'__call__',side_effect=lambda code:'fixture-platform-'+code)
        self.platform.start();self.addCleanup(self.platform.stop)
        core=self.core
        class InProcess:
            def request(self,message,raw=b''):return core.dispatch(message,raw)
        self.client_factory=lambda _:InProcess()
        if self.use_unix:
            folder=self.root/'socket';folder.mkdir(mode=0o700)
            self.socket_path=folder/'queue.sock'
            self.server=QueueBridgeServer(self.socket_path,self.core,allowed_uid=os.geteuid())
            self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
            def close():self.server.shutdown();self.server.server_close();self.thread.join(2)
            self.addCleanup(close)
            self.client_factory=lambda _:QueueBridgeClient(self.socket_path)
        self.origin='https://mini-test.example.test'
        self.headers={'X-Forwarded-Proto':'https','X-Real-IP':'192.0.2.8'}
        self.client=self.build()
        self.auth=self.login('first-code')

    def build(self):
        self.config.write_text(json.dumps(self.declaration));self.config.chmod(0o600)
        app,_=make_app(self.snapshot,self.config,self.origin,client_factory=self.client_factory)
        client=TestClient(app,base_url=self.origin,client=('127.0.0.1',30000))
        self.addCleanup(client.close)
        return client

    def login(self,code):
        r=self.client.post(PREFIX+'/session',headers=self.headers,
            json={'code':code,'client_schema':1,'request_key':'login-request-'+code})
        self.assertEqual(r.status_code,200,r.text)
        return {**self.headers,'Authorization':'Bearer '+r.json()['token']}

    def params(self,key=None):
        value={'server':'cn','catalog_version':self.catalog['version']}
        if key is not None:value['request_key']=key
        return value

    def upload(self,key='fixture-upload-key',raw=None):
        return self.client.post(PREFIX+'/map-recognition/jobs',params=self.params(key),headers=self.auth,
            files={'image':('fixture.png',image() if raw is None else raw,'image/png')})

    def test_default_disabled_has_only_session_snapshot_without_bridge_access(self):
        self.declaration['image_policy']='disabled'
        self.client_factory=lambda _:(_ for _ in ()).throw(AssertionError('No bridge construction while disabled'))
        client=self.build()
        r=client.get(PREFIX+'/snapshot?server=cn',headers=self.auth)
        self.assertEqual(r.status_code,200);self.assertFalse(r.json()['capabilities']['map_recognition'])
        self.assertIsNone(r.json()['catalog_version'])
        self.assertEqual(client.get(PREFIX+'/map-recognition/catalog?server=cn',headers=self.auth).status_code,404)
        self.assertEqual(self.reviewer.calls,0)

    def test_snapshot_catalog_and_identity_bind_while_global_remains_disabled(self):
        cn=self.client.get(PREFIX+'/snapshot?server=cn',headers=self.auth).json()
        catalog=self.client.get(PREFIX+'/map-recognition/catalog?server=cn',headers=self.auth).json()
        self.assertTrue(cn['capabilities']['map_recognition'])
        self.assertEqual(cn['catalog_version'],catalog['catalog_version'])
        self.assertEqual(cn['identity'],catalog['identity']);self.assertEqual(catalog['content_safety'],'required_approval')
        global_data=self.client.get(PREFIX+'/snapshot?server=global',headers=self.auth).json()
        self.assertFalse(global_data['capabilities']['map_recognition']);self.assertIsNone(global_data['catalog_version'])
        self.assertEqual(self.client.get(PREFIX+'/map-recognition/catalog?server=global',headers=self.auth).status_code,403)

    def test_original_key_response_loss_restart_and_changed_image(self):
        first=self.upload();self.assertEqual(first.status_code,202,first.text)
        job=first.json()['id'];self.assertTrue(self.reviewer.entered.wait(2))
        self.assertIsNone(self.store.claim())
        self.assertEqual(self.upload().json()['id'],job)
        self.client=self.build()
        recovered=self.client.get(PREFIX+'/map-recognition/jobs/by-request',params=self.params('fixture-upload-key'),headers=self.auth)
        self.assertEqual(recovered.json()['id'],job);self.assertEqual(self.reviewer.calls,1)
        self.assertEqual(self.upload(raw=image('blue')).status_code,409)

    def test_bridge_commit_then_response_loss_recovers_same_key(self):
        core=self.core
        class LostOnce:
            lost=False
            def request(self,message,raw=b''):
                result=core.dispatch(message,raw)
                if message['op']=='create' and not self.lost:
                    self.lost=True;raise OSError('fixture response lost after commit')
                return result
        wire=LostOnce();self.client_factory=lambda _:wire;self.client=self.build()
        uncertain=self.upload();self.assertEqual(uncertain.status_code,503,uncertain.text)
        recovered=self.client.get(PREFIX+'/map-recognition/jobs/by-request',params=self.params('fixture-upload-key'),headers=self.auth)
        self.assertEqual(recovered.json()['recovery'],'found')
        retry=self.upload();self.assertEqual(retry.status_code,202,retry.text)
        self.assertEqual(retry.json()['id'],recovered.json()['id'])
        self.assertTrue(self.reviewer.entered.wait(2));self.assertEqual(self.reviewer.calls,1)

    def test_completed_result_exposes_only_bound_map_slots(self):
        self.reviewer.release.set();job=self.upload().json()['id']
        until=time.monotonic()+3;claimed=None
        while time.monotonic()<until:
            claimed=self.store.claim()
            if claimed:break
            time.sleep(.01)
        self.assertIsNotNone(claimed)
        result={'schema_version':1,'server':'cn','catalog_version':self.catalog['version'],'status':'complete',
            'observed':'private unrelated OCR text','diagnostics':'private',
            'slots':[{'slot':i+1,'state':'matched',**row,'observed':'private','boxes':[1,2]} for i,row in enumerate(self.catalog['maps'][:5])]}
        self.store.finish(job,result=result)
        response=self.client.get(PREFIX+'/map-recognition/jobs/'+job,params=self.params(),headers=self.auth)
        self.assertEqual(response.status_code,200,response.text)
        self.assertNotIn('private',response.text);self.assertNotIn('boxes',response.text)
        self.assertTrue(response.json()['result']['needs_user_confirmation'])

    def test_disable_keeps_manual_snapshot_recovery_and_cancel(self):
        job=self.upload().json()['id'];self.core.uploads_enabled=False
        snapshot=self.client.get(PREFIX+'/snapshot?server=cn',headers=self.auth)
        self.assertEqual(snapshot.status_code,200);self.assertFalse(snapshot.json()['capabilities']['map_recognition'])
        self.assertEqual(self.upload('second-upload-key').status_code,503)
        query=PREFIX+'/map-recognition/jobs/'+job
        self.assertEqual(self.client.get(query,params=self.params(),headers=self.auth).status_code,200)
        cancelled=self.client.delete(query,params=self.params(),headers=self.auth)
        self.assertEqual(cancelled.json()['state'],'cancelled')
        self.reviewer.release.set();self.assertIsNone(self.store.claim())

    def test_cookie_origin_query_and_account_boundaries(self):
        route=PREFIX+'/map-recognition/catalog?server=cn'
        for bad in [{'Cookie':'anything=x'},{'Origin':'https://evil.test'}]:
            self.assertEqual(self.client.get(route,headers={**self.auth,**bad}).status_code,403)
        self.assertEqual(self.client.options(route,headers=self.auth).status_code,403)
        self.assertEqual(self.client.get(route+'&extra=1',headers=self.auth).status_code,400)
        for route in ['/api/mini/account/v1/me','/api/mini/v1/contributions','/api/mini/v1/session']:
            self.assertEqual(self.client.delete(route,headers=self.auth).status_code,404)

    def test_other_session_cannot_read_cancel_or_recover_original(self):
        job=self.upload().json()['id'];other=self.login('second-code')
        for method in [self.client.get,self.client.delete]:
            self.assertIn(method(PREFIX+'/map-recognition/jobs/'+job,params=self.params(),headers=other).status_code,(403,404))
        r=self.client.get(PREFIX+'/map-recognition/jobs/by-request',params=self.params('fixture-upload-key'),headers=other)
        self.assertEqual(r.json()['recovery'],'not_found')

    def test_loader_rejects_account_or_queue_credentials_and_unmoderated_policy(self):
        for changes in [{'account_state_dir':'/forbidden'}, {'queue_config':'/forbidden'},
                        {'image_policy':'private_unmoderated'},{'credentials_file':'/forbidden'}]:
            original=dict(self.declaration);self.declaration.update(changes)
            with self.assertRaises(ValueError):self.build()
            self.declaration=original


@unittest.skipUnless(hasattr(socket,'SO_PEERCRED'),'Actual Linux Unix socket required')
class UnixOcrHttpTests(OcrHttpTests):
    use_unix=True
