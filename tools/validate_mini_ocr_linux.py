"""Run ONLY in a disposable offline chroot with /work/source and fixture wheels.

No real provider/code/secret. Synthetic TLS, platform exchange and OCR worker.
"""
import datetime
import hashlib
import http.client
import io
import json
import multiprocessing
import os
from pathlib import Path
import resource
import ssl
import struct
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import zlib

SOURCE=Path('/work/source')
sys.path.insert(0,str(SOURCE))


def drop(uid,gid):
    os.setgroups([]);os.setgid(gid);os.setuid(uid);os.umask(0o077)


def chown_tree(path,uid,gid):
    for p in [path,*path.rglob('*')]:os.chown(p,uid,gid)


def broker(control,root,catalog):
    drop(10001,10002)
    from backend.map_recognition import JobStore,digest
    from backend.ocr_queue_bridge import QueueBridgeCore,QueueBridgeServer
    store=JobStore(Path(root)/'queue',production=True)
    class Reviewer:
        calls=0
        def review(self,raw,mime):
            self.calls+=1
            return {'approved':True,'provider':'aliyun','service':'baselineCheck',
                    'policy_version':'baseline-none-v1','image_sha256':digest(raw)}
    reviewer=Reviewer();core=QueueBridgeCore(store,reviewer,catalog,uploads_enabled=True,worker_health=lambda:'ready')
    server=QueueBridgeServer(Path(root)/'socket/guest.sock',core,allowed_uid=10002,socket_gid=10002)
    stop=threading.Event()
    def fake_worker():
        while not stop.is_set():
            job=store.claim()
            if job:
                store.finish(job['id'],result={'schema_version':1,'server':'cn','catalog_version':catalog['version'],
                    'status':'complete','observed':'private unrelated fixture OCR',
                    'slots':[{'slot':i+1,'state':'matched',**row,'observed':'private'} for i,row in enumerate(catalog['maps'][:5])]})
            stop.wait(.02)
    worker=threading.Thread(target=fake_worker,daemon=True);worker.start()
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    control.send({'ready':True,'uid':os.getuid()})
    try:
        while control.poll(60):
            command=control.recv()
            if command=='stop':break
            if command=='disable':core.uploads_enabled=False
            control.send({'uploads_enabled':core.uploads_enabled,'reviews':reviewer.calls})
    finally:
        stop.set();server.shutdown();server.server_close();core.close();worker.join(2);thread.join(2)
        control.close()


def guest(control,root):
    drop(10002,10002)
    queue_hidden=False
    try:open(Path(root)/'queue/recognition.sqlite3','rb').close()
    except PermissionError:queue_hidden=True
    assert queue_hidden
    from backend.mini_auth import WechatVerifier
    WechatVerifier.__call__=lambda self,code:'explicit-fixture-subject'
    from backend.mini_ocr_guest_service import make_app
    app,_=make_app('/work/snapshot',Path(root)/'guest.json','https://mini-test.racepick.cn')
    control.send({'ready':True,'uid':os.getuid(),'queue_hidden':queue_hidden,
                  'model_loaded':'backend.map_ocr_engine' in sys.modules})
    import uvicorn
    uvicorn.run(app,host='127.0.0.1',port=8011,proxy_headers=False,access_log=False,
                log_level='error',server_header=False,lifespan='off')


def split_http():
    from backend.mini_snapshot import load_snapshot,digest
    from backend.mini_auth import provision,KIND
    from backend.map_recognition import JobStore
    from PIL import Image
    source,manifest=load_snapshot('/work/snapshot');info,contents=source.score_versions.current()
    catalog={'server':'cn','version':digest((info['id']+':').encode()+contents['gauntlet_data.json']),
        'maps':[{'big':r['大地图'],'small':r['小地图']} for r in json.loads(contents['gauntlet_data.json'])['tracks']]}
    root=Path(tempfile.mkdtemp(prefix='split-uid-'));root.chmod(0o755)
    for name in ['queue','socket','nginx']:(root/name).mkdir(mode=0o700)
    (root/'queue/queue.json').write_text(json.dumps({'kind':'racepick-map-queue-v1'}))
    store=JobStore(root/'queue',production=True);store.prepare_safety_schema()
    chown_tree(root/'queue',10001,10002)
    os.chown(root/'socket',10001,10002);(root/'socket').chmod(0o750)
    state=provision(root/'guests');chown_tree(state,10002,10002)
    secret=root/'secret';secret.write_text('explicit-fixture-not-real-secret');secret.chmod(0o600);os.chown(secret,10002,10002)
    config=root/'guest.json';config.write_text(json.dumps({'kind':KIND,'state_dir':str(state),
        'appid':'wx'+'0'*16,'app_secret_file':str(secret),'image_policy':'aliyun_baseline',
        'bridge_socket':str(root/'socket/guest.sock')}));config.chmod(0o600);os.chown(config,10002,10002)
    from cryptography import x509
    from cryptography.x509.oid import NameOID
    from cryptography.hazmat.primitives import hashes,serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    import ipaddress
    key=rsa.generate_private_key(public_exponent=65537,key_size=2048)
    name=x509.Name([x509.NameAttribute(NameOID.COMMON_NAME,'isolated fixture CA')])
    now=datetime.datetime.now(datetime.timezone.utc)
    certificate=(x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(key.public_key())
        .serial_number(x509.random_serial_number()).not_valid_before(now-datetime.timedelta(days=1))
        .not_valid_after(now+datetime.timedelta(days=1)).add_extension(x509.BasicConstraints(ca=True,path_length=None),critical=True)
        .add_extension(x509.SubjectAlternativeName([x509.IPAddress(ipaddress.ip_address('127.0.0.1')),
                        x509.DNSName('mini-test.racepick.cn')]),critical=False).sign(key,hashes.SHA256()))
    cert=root/'fixture.crt';cert.write_bytes(certificate.public_bytes(serialization.Encoding.PEM))
    private=root/'fixture.key';private.write_bytes(key.private_bytes(serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,serialization.NoEncryption()));private.chmod(0o600);os.chown(private,10002,10002)
    os.chown(root/'nginx',10002,10002)
    proxy=Path('/work/templates/nginx-proxy.conf.in').read_text()
    (root/'proxy.conf').write_text(proxy)
    routes=Path('/work/templates/nginx-routes.conf.in').read_text().replace('__PROXY_INCLUDE__',str(root/'proxy.conf'))
    (root/'routes.conf').write_text(routes)
    (root/'nginx.conf').write_text('events {}\nhttp {\n'+Path('/work/templates/nginx-rate.conf.in').read_text()+
        '\naccess_log off; client_body_temp_path '+str(root/'nginx/body')+'; proxy_temp_path '+str(root/'nginx/proxy')+';\n'+
        'fastcgi_temp_path '+str(root/'nginx/fastcgi')+'; uwsgi_temp_path '+str(root/'nginx/uwsgi')+'; scgi_temp_path '+str(root/'nginx/scgi')+';\n'+
        'server { listen 127.0.0.1:8443 ssl; server_name mini-test.racepick.cn; ssl_certificate '+str(cert)+
        '; ssl_certificate_key '+str(private)+'; include '+str(root/'routes.conf')+'; location / { return 404; } } }\n'+
        'pid '+str(root/'nginx/pid')+'; error_log stderr warn;\n')
    ctx=multiprocessing.get_context('fork');parent,bchild=ctx.Pipe();gparent,gchild=ctx.Pipe()
    bp=ctx.Process(target=broker,args=(bchild,str(root),catalog));gp=ctx.Process(target=guest,args=(gchild,str(root)))
    bp.start();bchild.close();assert parent.poll(10);bmeta=parent.recv()
    gp.start();gchild.close();assert gparent.poll(15);gmeta=gparent.recv()
    nginx=None
    try:
        test=subprocess.run(['/usr/sbin/nginx','-t','-p',str(root/'nginx')+'/', '-c',str(root/'nginx.conf')],
            preexec_fn=lambda:drop(10002,10002),capture_output=True,text=True,timeout=10)
        assert test.returncode==0,test.stderr
        nginx=subprocess.Popen(['/usr/sbin/nginx','-p',str(root/'nginx')+'/', '-c',str(root/'nginx.conf'),'-g','daemon off;'],
            preexec_fn=lambda:drop(10002,10002),stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        context=ssl.create_default_context(cafile=str(cert));last=[0.0]
        def request(method,path,body=None,headers=None,pace=True):
            if pace:time.sleep(max(0,.56-(time.monotonic()-last[0])))
            last[0]=time.monotonic()
            c=http.client.HTTPSConnection('127.0.0.1',8443,context=context,timeout=8)
            c.request(method,path,body=body,headers=headers or {})
            r=c.getresponse();raw=r.read();status=r.status;c.close()
            try:value=json.loads(raw)
            except ValueError:value=None
            return status,value
        for _ in range(15):
            try:
                if request('GET','/api/mini/v1/snapshot?server=cn')[0]==401:break
            except OSError:pass
            time.sleep(.2)
        status,session=request('POST','/api/mini/v1/session',json.dumps({'code':'owned-fixture-code',
            'client_schema':1,'request_key':'owned-fixture-session'}),{'Content-Type':'application/json'})
        assert status==200
        auth={'Authorization':'Bearer '+session['token']}
        status,cn=request('GET','/api/mini/v1/snapshot?server=cn',headers=auth);assert status==200
        assert cn['identity']==session['identity'] and cn['capabilities']['map_recognition']
        for filename,record in cn['files'].items():assert digest(record['text'].encode())==record['sha256']
        status,gl=request('GET','/api/mini/v1/snapshot?server=global',headers=auth)
        assert status==200 and gl['catalog_version'] is None and not gl['capabilities']['map_recognition']
        stream=io.BytesIO();Image.new('RGB',(640,360),'red').save(stream,format='PNG');image=stream.getvalue()
        boundary='fixture-native-boundary'
        body=(('--'+boundary+'\r\nContent-Disposition: form-data; name="image"; filename="fixture.png"\r\n'+
             'Content-Type: image/png\r\n\r\n').encode()+image+('\r\n--'+boundary+'--\r\n').encode())
        query='?server=cn&catalog_version='+catalog['version']
        path='/api/mini/v1/map-recognition/jobs'+query+'&request_key=owned-fixture-upload'
        status,job=request('POST',path,body,{**auth,'Content-Type':'multipart/form-data; boundary='+boundary});assert status==202
        status,recovered=request('GET','/api/mini/v1/map-recognition/jobs/by-request'+query+'&request_key=owned-fixture-upload',headers=auth)
        assert status==200 and recovered['id']==job['id']
        status,retry=request('POST',path,body,{**auth,'Content-Type':'multipart/form-data; boundary='+boundary})
        assert status==202 and retry['id']==job['id']
        status,result=request('GET','/api/mini/v1/map-recognition/jobs/'+job['id']+query,headers=auth)
        assert status==200 and result['state']=='succeeded' and 'private' not in json.dumps(result)
        statuses={}
        # Valid static PNG padded with an ignorable ancillary chunk to exactly 8MiB.
        pad=b'\0'*(8388608-len(image)-12);chunk_type=b'npAD'
        large=image[:-12]+struct.pack('!I',len(pad))+chunk_type+pad+struct.pack('!I',zlib.crc32(chunk_type+pad)&0xffffffff)+image[-12:]
        assert len(large)==8388608
        large_body=(('--'+boundary+'\r\nContent-Disposition: form-data; name="image"; filename="fixture.png"\r\n'+
             'Content-Type: image/png\r\n\r\n').encode()+large+('\r\n--'+boundary+'--\r\n').encode())
        statuses['maximum_image']=request('POST','/api/mini/v1/map-recognition/jobs'+query+'&request_key=owned-maximum-image',
            large_body,{**auth,'Content-Type':'multipart/form-data; boundary='+boundary})[0]
        assert statuses['maximum_image']==202,statuses
        for label,method,route,headers in [('cookie','GET','/api/mini/v1/snapshot?server=cn',{'Cookie':'x=y'}),
            ('origin','GET','/api/mini/v1/snapshot?server=cn',{'Origin':'https://evil.test'}),
            ('accounts','GET','/api/mini/account/v1/me',{}),('global_ocr','GET','/api/mini/v1/map-recognition/catalog?server=global',{})]:
            statuses[label]=request(method,route,headers={**auth,**headers})[0]
        assert statuses=={'maximum_image':202,'cookie':403,'origin':403,'accounts':404,'global_ocr':403},statuses
        statuses['session_oversize']=request('POST','/api/mini/v1/session',headers={'Content-Length':'4097'})[0]
        statuses['upload_oversize']=request('POST',path,headers={**auth,'Content-Length':'8454145'})[0]
        assert statuses['session_oversize']==413 and statuses['upload_oversize']==413
        parent.send('disable');assert parent.poll(3);stats=parent.recv();assert stats['reviews']==2
        status,manual=request('GET','/api/mini/v1/snapshot?server=cn',headers=auth)
        assert status==200 and not manual['capabilities']['map_recognition']
        status,cancelled=request('DELETE','/api/mini/v1/map-recognition/jobs/'+job['id']+query,headers=auth)
        assert status==200 and cancelled['state']=='cancelled'
        return {'passed':True,'broker':bmeta,'guest':gmeta,'tls':'verified isolated CA and IP SAN, not public TLS',
            'nginx':'Ubuntu1.24.0 real -t and HTTPS proxy','cn_version':cn['version'],'global_version':gl['version'],
            'catalog_version':catalog['version'],'catalog_maps_sha256':digest(json.dumps(catalog['maps'],ensure_ascii=False,sort_keys=True).encode()),
            'edge_statuses':statuses,'same_key_supplier_reviews':1,'total_reviews_including_second_large_image':stats['reviews'],
            'maximum_image_bytes':len(large),'disabled_snapshot_manual':True,
            'supplier_transport':'mock only','worker':'one synthetic claim/finish thread, no OCR model'}
    finally:
        if nginx:
            nginx.terminate()
            try:nginx.wait(timeout=5)
            except subprocess.TimeoutExpired:nginx.kill();nginx.wait()
        if gp.is_alive():gp.terminate()
        gp.join(5)
        if bp.is_alive():parent.send('stop')
        bp.join(8)
        if bp.is_alive():bp.kill();bp.join()
        parent.close();gparent.close()


def main():
    print(json.dumps({'platform':Path('/usr/lib/os-release').read_text(),'python':sys.version,
        'pid':os.getpid(),'host_business_visible':Path('/var/lib/racepick').exists(),
        'network_namespace':os.readlink('/proc/self/ns/net')}),flush=True)
    integration=split_http();print('INTEGRATION='+json.dumps(integration,ensure_ascii=False),flush=True)
    drop(10001,10001)
    resource.setrlimit(resource.RLIMIT_AS,(1024*1024*1024,1024*1024*1024))
    resource.setrlimit(resource.RLIMIT_CORE,(0,0));resource.setrlimit(resource.RLIMIT_NOFILE,(128,128))
    names=['backend.test_mini_ocr_guest_service','backend.test_mini_guest_service','backend.test_mini_api',
        'backend.test_mini_production','backend.test_map_recognition','backend.test_map_ocr_production',
        'backend.test_image_safety_aliyun','backend.test_image_safety_sdk','backend.test_ocr_queue_bridge','tests.test_mini_ocr_release']
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromNames(names))
    print('UNIT_SUMMARY='+json.dumps({'tests':result.testsRun,'failures':len(result.failures),
        'errors':len(result.errors),'skips':len(result.skipped),'model_loaded':'backend.map_ocr_engine' in sys.modules}),flush=True)
    sys.exit(not result.wasSuccessful())


if __name__=='__main__':main()
