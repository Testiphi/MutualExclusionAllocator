"""Shared queue fixtures; Linux tests exercise actual Unix peer credentials."""
import hashlib
import json
import os
from pathlib import Path
import socket
import struct
import tempfile
import threading
import time
import unittest

from backend.image_safety_aliyun import SafetyError
from backend.map_recognition import JobStore, RecognitionError
from backend.ocr_queue_bridge import QueueBridgeCore, QueueBridgeServer, QueueBridgeClient
from backend.test_image_safety_aliyun import image

OWNER='mini-v1:'+'a'*64
VERSION='b'*64
CATALOG={'server':'cn','version':VERSION,'maps':[{'big':'fixture','small':'map'}]}


class Reviewer:
    def __init__(self):self.entered=threading.Event();self.release=threading.Event();self.calls=0;self.error=None
    def review(self,raw,mime):
        self.calls+=1;self.entered.set()
        if not self.release.wait(5):raise TimeoutError()
        if self.error:raise SafetyError(self.error)
        return {'approved':True,'provider':'aliyun','service':'baselineCheck',
                'policy_version':'baseline-none-v1','image_sha256':hashlib.sha256(raw).hexdigest()}


class BridgeTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='bridge-fixture-');self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        (self.root/'queue.json').write_text(json.dumps({'kind':'racepick-map-queue-v1'}))
        self.store=JobStore(self.root,production=True);self.store.prepare_safety_schema()
        self.reviewer=Reviewer()
        self.core=QueueBridgeCore(self.store,self.reviewer,CATALOG,uploads_enabled=True,worker_health=lambda:'ready')
        def close():self.reviewer.release.set();self.core.close()
        self.addCleanup(close)
        self.raw=image()

    def msg(self,op='create',**extra):
        base={'op':op,'owner':OWNER,'server':'cn','catalog_version':VERSION}
        if op=='create':base.update(key='fixture-upload-key',ip='192.0.2.8',mime='image/png')
        if op=='recover':base['key']='fixture-upload-key'
        return {**base,**extra}

    def wait(self,job,state):
        until=time.monotonic()+5
        while time.monotonic()<until:
            row=self.store.get(OWNER,job,'cn')
            if row['state']==state:return row
            time.sleep(.01)
        self.fail('Timed out waiting for '+state)

    def test_checking_holds_shared_capacity_and_is_never_claimed_by_worker(self):
        first=self.core.dispatch(self.msg(),self.raw);self.assertTrue(self.reviewer.entered.wait(2))
        self.assertEqual(first['state'],'queued');self.assertIsNone(self.store.claim())
        for i in range(7):self.store.create('web'+str(i),'web-upload-key-'+str(i),'cn',VERSION,self.raw,'image/png',catalog=CATALOG,client='web-ip')
        with self.assertRaises(RecognitionError) as error:
            self.store.create('web8','web-upload-key-8','cn',VERSION,self.raw,'image/png',catalog=CATALOG,client='web-ip')
        self.assertEqual(error.exception.status,429)
        same=self.core.dispatch(self.msg(),self.raw)
        self.assertEqual(same['id'],first['id']);self.assertEqual(self.reviewer.calls,1)
        self.reviewer.release.set();self.wait(first['id'],'queued')

    def test_cancel_before_audit_return_prevents_queue_or_late_result(self):
        job=self.core.dispatch(self.msg(),self.raw)['id'];self.reviewer.entered.wait(2)
        self.core.dispatch(self.msg('cancel',id=job));self.reviewer.release.set()
        self.wait(job,'cancelled');self.store.finish(job,result={'unexpected':True})
        self.assertIsNone(self.store.claim());self.assertFalse(self.store.image_path(job).exists())
        recovered=self.core.dispatch(self.msg('recover'))
        self.assertEqual(recovered['state'],'cancelled')

    def test_disable_blocks_new_work_but_keeps_existing_recover_and_cancel(self):
        job=self.core.dispatch(self.msg(),self.raw)['id']
        self.core.uploads_enabled=False
        with self.assertRaisesRegex(SafetyError,'RECOGNITION_DISABLED'):
            self.core.dispatch(self.msg(key='another-upload-key'),self.raw)
        self.assertEqual(self.core.dispatch(self.msg('recover'))['id'],job)
        self.assertEqual(self.core.dispatch(self.msg('cancel',id=job))['state'],'cancelled')

    def test_owner_catalog_global_and_extra_fields_cannot_bypass_boundary(self):
        for changes,code in [({'owner':'web-owner'},'JOB_FORBIDDEN'),({'server':'global'},'SERVER_DISABLED'),
                             ({'catalog_version':'f'*64},'CATALOG_CHANGED'),({'maps':[]},'INVALID_QUERY')]:
            with self.subTest(changes=changes),self.assertRaisesRegex(SafetyError,code):
                self.core.dispatch(self.msg(**changes),self.raw)
        self.assertEqual(self.reviewer.calls,0)

    def test_rejection_is_recovered_without_supplier_retry(self):
        self.reviewer.error='IMAGE_SAFETY_REJECTED';self.reviewer.release.set()
        job=self.core.dispatch(self.msg(),self.raw)['id'];self.wait(job,'failed')
        self.assertEqual(self.core.dispatch(self.msg(),self.raw)['id'],job)
        self.assertEqual(self.core.dispatch(self.msg('recover'))['error_code'],'IMAGE_SAFETY_REJECTED')
        self.assertEqual(self.reviewer.calls,1);self.assertIsNone(self.store.claim())

    def test_shared_ip_web_and_mini_use_same_twenty_attempt_budget(self):
        client=hashlib.sha256(b'ocr-client:192.0.2.8').hexdigest()
        for i in range(20):
            job=self.store.create('web'+str(i),'web-upload-key-'+str(i),'cn',VERSION,self.raw,'image/png',catalog=CATALOG,client=client)
            self.store.cancel('web'+str(i),job,'cn')
        with self.assertRaises(RecognitionError) as caught:self.core.dispatch(self.msg(),self.raw)
        self.assertEqual(caught.exception.status,429);self.assertEqual(self.reviewer.calls,0)

    def test_safety_deadline_expires_and_releases_capacity(self):
        job=self.core.dispatch(self.msg(),self.raw)['id'];self.reviewer.entered.wait(2)
        with self.store.connect() as db:db.execute('UPDATE safety_checks SET deadline=?',(time.time()-1,))
        self.store.cleanup();self.assertEqual(self.store.get(OWNER,job,'cn')['state'],'failed')
        self.reviewer.release.set();self.assertIsNone(self.store.claim())
        self.assertFalse(self.store.image_path(job).exists())

    def test_normal_queue_start_does_not_migrate_safety_schema(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            (root/'queue.json').write_text(json.dumps({'kind':'racepick-map-queue-v1'}))
            store=JobStore(root,production=True)
            with store.connect() as db:
                self.assertIsNone(db.execute("SELECT name FROM sqlite_master WHERE name='safety_schema'").fetchone())
            with self.assertRaises(RecognitionError) as error:
                store.create_for_safety(OWNER,'another-upload-key','cn',VERSION,self.raw,'image/png',catalog=CATALOG,client='fixture')
            self.assertEqual(error.exception.status,503)
            self.assertIsNone(store.claim())


@unittest.skipUnless(hasattr(socket,'SO_PEERCRED'),'Linux peer credentials required')
class UnixBridgeTests(BridgeTests):
    def setUp(self):
        super().setUp()
        directory=self.root/'socket';directory.mkdir(mode=0o700)
        self.path=directory/'queue.sock'
        self.server=QueueBridgeServer(self.path,self.core,allowed_uid=os.geteuid())
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
        def close():self.server.shutdown();self.server.server_close();self.thread.join(2)
        self.addCleanup(close)
        self.client=QueueBridgeClient(self.path)

    def test_real_unix_create_recover_cancel_single_queue(self):
        job=self.client.request(self.msg(),self.raw)['id'];self.reviewer.entered.wait(2)
        self.assertEqual(self.client.request(self.msg('recover'))['id'],job)
        self.assertEqual(self.client.request(self.msg('cancel',id=job))['state'],'cancelled')
        self.assertEqual(self.reviewer.calls,1)
        self.assertEqual(self.path.stat().st_mode&0o777,0o660)

    def test_peer_uid_mismatch_rejected_before_body(self):
        self.server.allowed_uid=os.geteuid()+10000
        with self.assertRaisesRegex(SafetyError,'BRIDGE_PEER_FORBIDDEN'):
            self.client.request(self.msg('catalog'))
        self.assertEqual(self.reviewer.calls,0)

    def test_extra_frame_and_oversized_frame_are_rejected(self):
        header=json.dumps(self.msg('catalog')).encode()
        for raw in [struct.pack('!II',8193,0),struct.pack('!II',len(header),0)+header+b'extra']:
            with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as c:
                c.settimeout(3);c.connect(str(self.path));c.sendall(raw);c.shutdown(socket.SHUT_WR)
                size=struct.unpack('!I',c.recv(4))[0]
                reply=json.loads(c.recv(size))
                self.assertEqual(reply['error'],'BRIDGE_INVALID_REQUEST')
        self.assertEqual(self.reviewer.calls,0)
