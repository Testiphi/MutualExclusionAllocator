"""Restricted AF_UNIX queue bridge. No HTTP routes, model startup or business DB.

Schema preparation is explicit. Instantiation never initializes a queue/schema.
"""
from concurrent.futures import ThreadPoolExecutor
import ipaddress
import json
import os
from pathlib import Path
import re
import socket
import socketserver
import stat
import struct
import threading
import time

from backend.image_safety_aliyun import SafetyError
from backend.map_recognition import digest, validate_image, MAX_BYTES, RecognitionError

ERRORS = {'IMAGE_SAFETY_REJECTED', 'IMAGE_SAFETY_TIMEOUT', 'IMAGE_SAFETY_UNAVAILABLE'}


def binding(owner, key=None):
    if not isinstance(owner, str) or not re.fullmatch(r'mini-v1:[a-f0-9]{64}', owner):
        raise SafetyError('JOB_FORBIDDEN')
    if key is not None and (not isinstance(key, str) or not re.fullmatch(r'[A-Za-z0-9_-]{16,80}', key)):
        raise SafetyError('INVALID_QUERY')


class QueueBridgeCore:
    def __init__(self, store, reviewer, catalog, *, uploads_enabled=False, worker_health=None):
        if (not store.production or not isinstance(catalog, dict) or set(catalog) != {'server','version','maps'}
                or catalog['server'] != 'cn' or not re.fullmatch(r'[a-f0-9]{64}', catalog['version'])
                or not isinstance(catalog['maps'], list) or not catalog['maps']):
            raise ValueError('Explicit production-shaped queue and fixed CN catalog required')
        for row in catalog['maps']:
            if (not isinstance(row, dict) or set(row) != {'big', 'small'}
                    or any(not isinstance(v, str) or not 1 <= len(v) <= 100 for v in row.values())):
                raise ValueError('Invalid fixed catalog')
        with store.connect() as db:
            if [r[0] for r in db.execute('SELECT version FROM safety_schema')] != [1]:
                raise ValueError('Safety schema was not explicitly prepared')
        self.store, self.reviewer = store, reviewer
        self.catalog = json.loads(json.dumps(catalog))
        self.uploads_enabled = uploads_enabled is True
        self.worker_health=worker_health or self._worker_health
        self.executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix='safety-review')
        self.futures = set();self.lock = threading.Lock()
        self.review_slots=threading.BoundedSemaphore(8)

    def _worker_health(self):
        try:
            supervisor=json.loads((self.store.root/'supervisor-state.json').read_bytes())
            worker=json.loads((self.store.root/'worker-state.json').read_bytes())
            return ('ready' if 0<=time.time()-supervisor['updated']<5
                    and supervisor['state']=='running' and worker['state'] in ('ready','working')
                    and worker['run_id']==supervisor['run_id'] else 'unavailable')
        except (OSError,ValueError,KeyError,TypeError):return 'unavailable'

    def close(self):
        self.uploads_enabled = False
        # Only this bridge's mini admissions are terminalized. Website tasks are untouched.
        with self.store.connect() as db:
            ids = [r[0] for r in db.execute("SELECT id FROM jobs WHERE state='checking' AND owner LIKE 'mini-v1:%'")]
        for job in ids:self.store.complete_safety(job, False, 'IMAGE_SAFETY_UNAVAILABLE')
        self.executor.shutdown(wait=True, cancel_futures=True)

    def _row(self, owner, job_id):
        if not isinstance(job_id, str) or not re.fullmatch(r'[a-f0-9]{32}', job_id):
            raise SafetyError('JOB_NOT_FOUND')
        row = self.store.get(owner, job_id, 'cn')
        if row['version'] != self.catalog['version']:
            raise SafetyError('CATALOG_CHANGED')
        # Internal checking state is exposed as the existing queued state.
        state = 'queued' if row['state'] == 'checking' else row['state']
        error_code = row['error'] if row['error'] in ERRORS else None
        error = '图片安全处理未通过，请继续手动选图' if error_code else row['error']
        # Reuse the existing strict map-only sanitizer. No arbitrary OCR text leaves the bridge.
        result = None
        if row['result'] is not None:
            from backend.mini_result import native_result
            result = native_result(row['result'], self.catalog)
        return {'id': row['id'], 'server': 'cn', 'catalog_version': row['version'],
                'state': state, 'result': result, 'error': error, 'error_code': error_code,
                'expires_at': int(row['expires'])}

    def _review(self, job_id, image, mime):
        self.store.cleanup()
        with self.store.connect() as db:
            row = db.execute("SELECT state FROM jobs WHERE id=?",(job_id,)).fetchone()
        if not row or row['state'] != 'checking':return
        try:
            verdict = self.reviewer.review(image, mime)
            if verdict != {'approved': True, 'provider': 'aliyun', 'service': 'baselineCheck',
                           'policy_version': 'baseline-none-v1', 'image_sha256': digest(image)}:
                raise SafetyError('IMAGE_SAFETY_UNAVAILABLE')
            self.store.complete_safety(job_id, True)
        except BaseException as error:
            code = error.code if isinstance(error, SafetyError) and error.code in ERRORS else 'IMAGE_SAFETY_UNAVAILABLE'
            self.store.complete_safety(job_id, False, code)

    def dispatch(self, message, image=b''):
        if not isinstance(message, dict) or message.get('op') not in {'create','recover','get','cancel','catalog','preflight'}:
            raise SafetyError('INVALID_QUERY')
        op = message['op']
        fields = {'op','owner','server','catalog_version'}
        fields |= {'key','ip','mime'} if op == 'create' else ({'key','ip'} if op=='preflight' else ({'key'} if op == 'recover' else ({'id'} if op in {'get','cancel'} else set())))
        if set(message) != fields or (image and op != 'create'):
            raise SafetyError('INVALID_QUERY')
        binding(message['owner'], message.get('key'))
        if message['server'] != 'cn':raise SafetyError('RECOGNITION_SERVER_DISABLED')
        if message['catalog_version'] != self.catalog['version']:raise SafetyError('CATALOG_CHANGED')
        if op == 'catalog':
            if not self.uploads_enabled:raise SafetyError('RECOGNITION_DISABLED')
            if self.worker_health()!='ready':raise SafetyError('OCR_UNAVAILABLE')
            return self.catalog
        owner = message['owner']
        if op == 'recover':
            self.store.cleanup()
            with self.store.connect() as db:
                row = db.execute('SELECT id FROM jobs WHERE owner=? AND request_key=?',(owner,message['key'])).fetchone()
            if not row:return {'recovery':'not_found','retry_same_key':True}
            return {'recovery':'found',**self._row(owner,row['id'])}
        if op in {'get','cancel'}:
            self._row(owner,message['id'])
            if op == 'cancel':self.store.cancel(owner,message['id'],'cn')
            return self._row(owner,message['id'])
        if not self.uploads_enabled:raise SafetyError('RECOGNITION_DISABLED')
        try:ip = str(ipaddress.ip_address(message['ip']))
        except (ValueError,TypeError):raise SafetyError('TRUSTED_PROXY_REQUIRED') from None
        if op=='preflight':
            self.store.cleanup()
            with self.store.connect() as db:
                existing=db.execute('SELECT id FROM jobs WHERE owner=? AND request_key=?',(owner,message['key'])).fetchone()
                if existing:return {'existing':True}
                if self.worker_health()!='ready':raise SafetyError('OCR_UNAVAILABLE')
                client=digest(('ocr-client:'+ip).encode())
                if (db.execute("SELECT count(*) FROM jobs WHERE state IN ('checking','queued','running')").fetchone()[0]>=8
                        or db.execute("SELECT count(*) FROM jobs WHERE owner=? AND state IN ('checking','queued','running')",(owner,)).fetchone()[0]>=2
                        or db.execute('SELECT count(*) FROM jobs WHERE client=? AND created>?',(client,time.time()-600)).fetchone()[0]>=20
                        or db.execute('SELECT count(*) FROM jobs WHERE owner=? AND created>?',(owner,time.time()-600)).fetchone()[0]>=20):
                    raise SafetyError('OCR_LIMITED')
            return {'existing':False}
        if self.worker_health()!='ready':raise SafetyError('OCR_UNAVAILABLE')
        validate_image(image, message['mime'])
        with self.store.connect() as db:
            existing=db.execute('SELECT id FROM jobs WHERE owner=? AND request_key=?',(owner,message['key'])).fetchone()
        reserved=self.review_slots.acquire(blocking=False)
        if not reserved:
            if existing:
                row=self.store.get(owner,existing['id'],'cn')
                if (row['version'],row['image_sha'])!=(self.catalog['version'],digest(image)):
                    raise RecognitionError(409,'同一请求编号不能用于不同截图或服别')
                return self._row(owner,existing['id'])
            raise RecognitionError(429,'图片安全处理容量已满')
        try:
            job_id, new = self.store.create_for_safety(owner,message['key'],'cn',self.catalog['version'],
                image,message['mime'],catalog=self.catalog,client=digest(('ocr-client:'+ip).encode()))
        except BaseException:
            if reserved:self.review_slots.release()
            raise
        if not new and reserved:self.review_slots.release()
        if new:
            future=self.executor.submit(self._review,job_id,image,message['mime'])
            with self.lock:self.futures.add(future)
            def done(future):
                with self.lock:self.futures.discard(future)
                self.review_slots.release()
            future.add_done_callback(done)
        return self._row(owner,job_id)


def _receive(connection, size, deadline):
    result=bytearray()
    while len(result)<size:
        remaining=deadline-time.monotonic()
        if remaining<=0:raise TimeoutError()
        connection.settimeout(remaining)
        part=connection.recv(min(65536,size-len(result)))
        if not part:raise ValueError('Truncated frame')
        result.extend(part)
    return bytes(result)


def _unique(pairs):
    result={}
    for key,value in pairs:
        if key in result:raise ValueError('Duplicate header field')
        result[key]=value
    return result


class QueueBridgeServer(socketserver.ThreadingMixIn, getattr(socketserver,'UnixStreamServer',socketserver.TCPServer)):
    daemon_threads=True
    block_on_close=True
    allow_reuse_address=False

    def __init__(self, path, core, *, allowed_uid, socket_gid=None):
        if not hasattr(socket,'SO_PEERCRED'):raise ValueError('Linux SO_PEERCRED required')
        path=Path(path).absolute()
        meta=path.parent.stat()
        if (path.exists() or path.is_symlink() or path.parent.resolve()!=path.parent
                or meta.st_uid!=os.geteuid() or stat.S_IMODE(meta.st_mode)&0o007
                or type(allowed_uid) is not int or allowed_uid<0):
            raise ValueError('Use a new socket in a private owned directory')
        self.core,self.allowed_uid=core,allowed_uid
        self.slots=threading.BoundedSemaphore(8)
        class Handler(socketserver.BaseRequestHandler):
            def handle(handler):
                response=None
                try:
                    _,uid,_=struct.unpack('3i',handler.request.getsockopt(socket.SOL_SOCKET,socket.SO_PEERCRED,12))
                    if uid!=handler.server.allowed_uid:raise SafetyError('BRIDGE_PEER_FORBIDDEN')
                    deadline=time.monotonic()+20
                    header_size,image_size=struct.unpack('!II',_receive(handler.request,8,deadline))
                    if not 1<=header_size<=8192 or image_size>MAX_BYTES:raise ValueError('Oversized frame')
                    header=_receive(handler.request,header_size,deadline)
                    image=_receive(handler.request,image_size,deadline)
                    handler.request.settimeout(max(.001,deadline-time.monotonic()))
                    if handler.request.recv(1):raise ValueError('Trailing frame')
                    message=json.loads(header,object_pairs_hook=_unique)
                    response={'ok':handler.server.core.dispatch(message,image)}
                except SafetyError as error:response={'error':error.code}
                except RecognitionError as error:
                    response={'error':{429:'OCR_LIMITED',410:'JOB_EXPIRED',404:'JOB_NOT_FOUND',409:'REQUEST_KEY_CONFLICT'}.get(error.status,'OCR_UNAVAILABLE')}
                except Exception:response={'error':'BRIDGE_INVALID_REQUEST'}
                raw=json.dumps(response,ensure_ascii=False,separators=(',',':')).encode()
                try:
                    handler.request.settimeout(3)
                    handler.request.sendall(struct.pack('!I',len(raw))+raw)
                except OSError:pass
        super().__init__(str(path),Handler)
        os.chmod(path,0o660)
        if socket_gid is not None:os.chown(path,os.geteuid(),socket_gid)
        self.path=path;self.inode=path.stat().st_ino

    def process_request(self,request,client_address):
        if not self.slots.acquire(blocking=False):
            request.close();return
        try:super().process_request(request,client_address)
        except BaseException:self.slots.release();raise

    def process_request_thread(self,request,client_address):
        try:super().process_request_thread(request,client_address)
        finally:self.slots.release()

    def server_close(self):
        super().server_close()
        if self.path.is_socket() and self.path.stat().st_ino==self.inode:self.path.unlink()


class QueueBridgeClient:
    def __init__(self,path):self.path=str(path)

    def request(self,message,image=b''):
        header=json.dumps(message,ensure_ascii=False,separators=(',',':')).encode()
        if not 1<=len(header)<=8192 or len(image)>MAX_BYTES:raise ValueError('Oversized frame')
        with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as connection:
            connection.settimeout(20);connection.connect(self.path)
            connection.sendall(struct.pack('!II',len(header),len(image))+header+image)
            connection.shutdown(socket.SHUT_WR)
            deadline=time.monotonic()+20
            size=struct.unpack('!I',_receive(connection,4,deadline))[0]
            if not 1<=size<=65536:raise ValueError('Oversized response')
            response=json.loads(_receive(connection,size,deadline),object_pairs_hook=_unique)
            if 'error' in response:raise SafetyError(response['error'])
            return response['ok']


def load_bridge_config(path):
    value=json.loads(Path(path).read_text(encoding='utf-8'),object_pairs_hook=_unique)
    fields={'kind','enabled','socket_path','socket_gid','allowed_uid','queue_config',
            'snapshot_dir','safety_config'}
    if (not isinstance(value,dict) or set(value)!=fields or value['kind']!='racepick-ocr-queue-bridge-v1'
            or type(value['enabled']) is not bool):
        raise ValueError('Invalid bridge configuration')
    for key in ('socket_path','queue_config','snapshot_dir','safety_config'):
        if (not isinstance(value[key],str) or not value[key].startswith('/')
                or '..' in value[key].split('/') or '\\' in value[key]):
            raise ValueError('Explicit absolute bridge paths required')
    for key in ('allowed_uid','socket_gid'):
        if value[key] is not None and (type(value[key]) is not int or value[key]<0):
            raise ValueError('Invalid peer identity')
    if value['enabled'] and (value['allowed_uid'] is None or value['socket_gid'] is None):
        raise ValueError('Actual peer UID and socket GID must be explicitly configured')
    return value


def main():
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['check-config','serve'])
    parser.add_argument('--config',required=True,type=Path)
    parser.add_argument('--allow-live-calls',action='store_true')
    args=parser.parse_args();options=load_bridge_config(args.config)
    if args.action=='check-config':
        print(json.dumps({'enabled':options['enabled'],'credentials_loaded':False,
            'queue_opened':False,'model_started':False}));return
    if not options['enabled'] or not args.allow_live_calls:
        raise ValueError('Bridge and live-call capability must both be explicitly enabled')
    from backend.image_safety_aliyun import load_config
    from backend.image_safety_sdk import SdkProcessReviewer
    safety=load_config(options['safety_config'])
    if safety.mode!='live':raise ValueError('Explicit live safety configuration required')
    from backend.mini_snapshot import load_snapshot
    source,_=load_snapshot(options['snapshot_dir'])
    info,contents=source.score_versions.current()
    catalog={'server':'cn','version':digest((info['id']+':').encode()+contents['gauntlet_data.json']),
             'maps':[{'big':r['大地图'],'small':r['小地图']} for r in json.loads(contents['gauntlet_data.json'])['tracks']]}
    from backend.map_ocr_production import settings
    from backend.map_recognition import JobStore
    root=settings(options['queue_config'])
    import fcntl
    lock=(root/'bridge.lock').open('a+b');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    core=QueueBridgeCore(JobStore(root,production=True),
        SdkProcessReviewer(safety,allow_live_calls=True),catalog,uploads_enabled=True)
    try:
        with QueueBridgeServer(options['socket_path'],core,allowed_uid=options['allowed_uid'],
                               socket_gid=options['socket_gid']) as server:
            import signal
            def stop(*_):
                core.uploads_enabled=False
                threading.Thread(target=server.shutdown,daemon=True).start()
            signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop)
            server.serve_forever()
    finally:core.close();lock.close()


if __name__=='__main__':main()
