"""Exact-prefix native adapter. Delegates to the existing snapshot writers/OCR store."""
import asyncio
import hashlib
import ipaddress
import json
import re
import secrets
import sqlite3
import time
from email.message import Message
from urllib.parse import urlsplit

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool
from starlette.requests import ClientDisconnect
from starlette.exceptions import HTTPException as StarletteHTTPException
from backend.mini_auth import MiniError, fail, request_key

PREFIX = '/api/mini/v1'
ACCOUNT_PREFIX = '/api/mini/account/v1'


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def error_response(error):
    return JSONResponse({'schema_version': 1, 'code': error.code, 'detail': error.message}, status_code=error.status,
                        headers={'Retry-After': str(error.retry)} if error.retry else None)


async def limited_body(request, maximum):
    async def collect():
        body = bytearray()
        async for chunk in request.stream():
            if len(body)+len(chunk) > maximum:
                fail(413, 'BODY_TOO_LARGE', '请求体超过允许大小')
            body.extend(chunk)
        return bytes(body)
    try:
        return await asyncio.wait_for(collect(), 20)
    except (TimeoutError, asyncio.TimeoutError):
        fail(503, 'READ_TIMEOUT', '读取上传超时；请按原请求编号恢复', 2)
    except ClientDisconnect:
        fail(503, 'UPLOAD_INTERRUPTED', '上传连接中断；请按原请求编号恢复', 2)


def multipart_image(raw, content_type, max_bytes):
    message = Message()
    message['content-type'] = content_type
    params = message.get_params(header='content-type') or []
    if message.get_content_type() != 'multipart/form-data' or len(params) != 2 or params[1][0].lower() != 'boundary':
        fail(415, 'MULTIPART_REQUIRED', '需要单文件multipart上传')
    boundary = message.get_param('boundary')
    if not isinstance(boundary, str) or not re.fullmatch(r"[A-Za-z0-9'()+_,./:=?-]{1,70}", boundary):
        fail(400, 'INVALID_MULTIPART', 'multipart边界无效')
    marker = b'--' + boundary.encode('ascii')
    if not raw.startswith(marker+b'\r\n'):
        fail(400, 'INVALID_MULTIPART', 'multipart结构无效')
    end = b'\r\n'+marker+b'--'
    trimmed = raw[:-2] if raw.endswith(b'\r\n') else raw
    if not trimmed.endswith(end):
        fail(400, 'INVALID_MULTIPART', 'multipart未完整读取')
    part = trimmed[len(marker)+2:-len(end)]
    index = part.find(b'\r\n\r\n')
    if index < 0 or index > 8192:
        fail(400, 'INVALID_MULTIPART', '文件头超过限制或无效')
    headers, image = part[:index], part[index+4:]
    if b'\r\n'+marker in part:
        fail(400, 'ONE_IMAGE_ONLY', '只允许一个image文件，不接收其他表单字段')
    parsed = {}
    for line in headers.split(b'\r\n'):
        name, sep, value = line.partition(b':')
        if not sep or name.lower() not in (b'content-disposition', b'content-type') or name.lower() in parsed:
            fail(400, 'INVALID_MULTIPART', '文件头不支持或重复')
        parsed[name.lower()] = value.strip().decode('latin1')
    disposition = Message()
    disposition['content-disposition'] = parsed.get(b'content-disposition', '')
    parameters = disposition.get_params(header='content-disposition') or []
    if (disposition.get_content_disposition() != 'form-data' or disposition.get_param('name', header='content-disposition') != 'image'
            or len(parameters) != 3 or {p[0].lower() for p in parameters[1:]} != {'name', 'filename'}):
        fail(400, 'ONE_IMAGE_ONLY', '只允许名为image的单文件')
    filename = disposition.get_filename()
    if not isinstance(filename, str) or not 1 <= len(filename) <= 255 or any(ord(c) < 32 for c in filename):
        fail(400, 'INVALID_MULTIPART', '文件名无效')
    mime = parsed.get(b'content-type', '').lower()
    # wx.uploadFile does not expose per-part MIME control on every client.
    # Generic binary parts still require a recognized signature and full decoder validation.
    if mime in ('', 'application/octet-stream'):
        mime = ('image/png' if image.startswith(b'\x89PNG\r\n\x1a\n') else
                'image/jpeg' if image.startswith(b'\xff\xd8\xff') else
                'image/webp' if image.startswith(b'RIFF') and image[8:12] == b'WEBP' else '')
    if mime not in ('image/png', 'image/jpeg', 'image/webp'):
        fail(415, 'IMAGE_TYPE_UNSUPPORTED', '仅支持PNG、JPEG或WebP')
    if len(image) > max_bytes:
        fail(413, 'IMAGE_TOO_LARGE', '单图不得超过8MiB')
    return image, mime


def parameters(request, names):
    pairs = list(request.query_params.multi_items())
    if len(pairs) != len(names) or {k for k, _ in pairs} != set(names):
        fail(400, 'INVALID_QUERY', '查询字段缺失、重复或不受支持')
    values = dict(pairs)
    if values.get('server') not in ('cn', 'global'):
        fail(400, 'INVALID_SERVER', '服别无效')
    if 'catalog_version' in values and not re.fullmatch('[a-f0-9]{64}', values['catalog_version']):
        fail(400, 'INVALID_CATALOG_VERSION', '目录版本无效')
    if 'request_key' in values:
        request_key(values['request_key'])
    return values


from backend.mini_result import native_result

def make_native(config, source, service):
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None, redirect_slashes=False)
    store, verifier = config['store'], config['verifier']
    remote=getattr(service,'is_bridge',False)
    # Releases without the optional OCR component must still boot with native disabled
    # or with guest/snapshot-only native support. Keep image rules in their owning module.
    if service is not None:
        from backend.map_recognition import MAX_BYTES, MAX_PIXELS, TTL, RecognitionError, validate_image
        MAX_ENVELOPE = MAX_BYTES + 65536
    else:
        RecognitionError = None

    def snapshot(server):
        writer = getattr(source, 'score_versions' if server == 'cn' else 'global_score_versions', None)
        if writer is None:
            fail(503, 'SNAPSHOT_UNAVAILABLE', '当前服别活动快照尚未配置', 5)
        try:
            return writer.current()
        except (OSError, ValueError, sqlite3.Error):
            fail(503, 'SNAPSHOT_UNAVAILABLE', '当前服别活动快照暂不可用', 5)

    def catalog(require_upload=True):
        policy_ok=(config['image_policy']=='aliyun_baseline' if remote else config['image_policy']=='private_unmoderated')
        if not policy_ok or service is None:
            fail(503, 'RECOGNITION_DISABLED', '原生识图尚未启用，手动选图仍可使用')
        info, contents = snapshot('cn')
        current = service.catalog('cn') if require_upload or not remote else service.fixed_catalog
        raw = contents['gauntlet_data.json']
        expected = digest((info['id']+':').encode()+raw) if getattr(service, 'production', False) else digest(raw)
        if current['version'] != expected:
            fail(409, 'CATALOG_CHANGED', '识图目录与活动快照不同，请刷新')
        return current

    async def cn_binding(request, with_key=False, require_upload=False):
        params = parameters(request, ['server', 'catalog_version'] + (['request_key'] if with_key else []))
        if params['server'] != 'cn':
            fail(403, 'RECOGNITION_SERVER_DISABLED', '国际服识图尚未开放')
        current = await run_in_threadpool(catalog,require_upload) if remote else catalog(require_upload)
        if params['catalog_version'] != current['version']:
            fail(409, 'CATALOG_CHANGED', '地图目录版本已变化，请刷新；不要自动重传')
        return params, current

    def lookup(owner, job_id):
        if not re.fullmatch('[a-f0-9]{32}', job_id):
            fail(404, 'JOB_NOT_FOUND', '任务不存在')
        if remote:return service.get(owner,job_id)
        service.store.cleanup()
        with service.store.connect() as db:
            row = db.execute('SELECT * FROM jobs WHERE id=?', (job_id,)).fetchone()
        if row is None:
            fail(404, 'JOB_NOT_FOUND', '任务不存在或元数据已清理')
        if row['owner'] != owner or row['server'] != 'cn':
            fail(403, 'JOB_FORBIDDEN', '任务不属于当前会话或服别')
        if row['state'] == 'expired' or row['expires'] <= time.time():
            fail(410, 'JOB_EXPIRED', '图片与识别结果已到期；不要自动重传')
        return dict(row)

    async def owned(owner,job_id):
        return await run_in_threadpool(lookup,owner,job_id) if remote else lookup(owner,job_id)

    def response_for(row, current):
        if remote:
            if (not isinstance(row,dict) or row.get('server')!='cn' or row.get('catalog_version')!=current['version']
                    or row.get('state') not in ('queued','running','succeeded','failed','cancelled')
                    or type(row.get('expires_at')) is not int or not re.fullmatch('[a-f0-9]{32}',row.get('id',''))):
                fail(503,'RESULT_INVALID','队列响应绑定无效')
            result=native_result(json.dumps(row['result']) if row.get('result') is not None else None,current)
            return {k:row.get(k) for k in ('id','server','catalog_version','state','error','expires_at','error_code')}|{'result':result}
        if row['version'] != current['version']:
            fail(409, 'CATALOG_CHANGED', '任务目录版本已变化')
        return {'id': row['id'], 'server': 'cn', 'catalog_version': row['version'], 'state': row['state'],
                'result': native_result(row['result'], current), 'error': row['error'], 'expires_at': int(row['expires'])}

    @app.exception_handler(MiniError)
    async def mini_error(request, error):
        return error_response(error)

    @app.exception_handler(StarletteHTTPException)
    async def route_error(request, error):
        return error_response(MiniError(error.status_code, 'ROUTE_NOT_AVAILABLE', '原生路径或方法不受支持'))

    async def recognition_error(request, error):
        code = {409: 'CATALOG_CHANGED', 410: 'JOB_EXPIRED', 429: 'OCR_LIMITED', 503: 'OCR_UNAVAILABLE'}.get(error.status, 'IMAGE_INVALID')
        if error.status == 409 and '同一请求编号' in error.message:
            code = 'REQUEST_KEY_CONFLICT'
        return error_response(MiniError(error.status, code, error.message, 5 if error.status in (429, 503) else None))
    if RecognitionError is not None:
        app.add_exception_handler(RecognitionError, recognition_error)

    @app.middleware('http')
    async def authentication(request, call_next):
        try:
            if request.method == 'OPTIONS' or request.headers.get('origin') or request.headers.get('cookie'):
                fail(403, 'NATIVE_ONLY', '原生接口不接受网页Origin或Cookie身份')
            ip = request.scope['mini_ip']
            client = store.hashed('ip:'+ip)
            request.state.mini_client = client
            store.budget('all:'+client, 300, 60)
            if not (request.method == 'POST' and request.url.path == PREFIX+'/session'):
                request.state.guest = store.authenticate(request.headers.get('authorization'))
                store.budget('session:'+request.state.guest['sid'], 120, 60)
            return await call_next(request)
        except MiniError as error:
            return error_response(error)
        except (OSError, ValueError, sqlite3.Error):
            return error_response(MiniError(503, 'NATIVE_STATE_UNAVAILABLE', '原生服务状态暂不可用', 5))

    @app.post(PREFIX+'/session')
    async def session(request: Request):
        if request.query_params or request.headers.get('content-type', '').split(';')[0] != 'application/json':
            fail(415, 'JSON_REQUIRED', '会话入口需要JSON正文')
        store.budget('exchange-ip:'+request.state.mini_client, 10, 600)
        store.budget('exchange-global', 100, 600)
        try:
            body = json.loads(await limited_body(request, 4096))
        except (ValueError, UnicodeError):
            fail(400, 'INVALID_SESSION_BODY', '会话正文无效')
        if (not isinstance(body, dict) or set(body) != {'code', 'client_schema', 'request_key'} or type(body['client_schema']) is not int
                or body['client_schema'] != 1 or not isinstance(body['code'], str) or not re.fullmatch(r'[!-~]{1,256}', body['code'])):
            fail(400, 'INVALID_SESSION_BODY', '会话字段无效')
        key = request_key(body['request_key'])
        return await run_in_threadpool(store.exchange, body['code'], key, verifier)

    @app.delete(PREFIX+'/session')
    async def revoke(request: Request):
        if request.query_params:
            fail(400, 'INVALID_QUERY', '撤销会话不接受查询参数')
        with store.connect() as db:
            db.execute('UPDATE sessions SET revoked=1 WHERE sid=?', (request.state.guest['sid'],))
        return {'revoked': True}

    @app.get(PREFIX+'/snapshot')
    async def read_snapshot(request: Request):
        server = parameters(request, ['server'])['server']
        info, contents = snapshot(server)
        names = ('cars.json', 'gauntlet_data.json') if server == 'cn' else ('cars.global.json', 'gauntlet_data.global.json', 'global-data-manifest.json')
        version = None
        if server == 'cn' and service is not None and config['image_policy'] in ('private_unmoderated','aliyun_baseline'):
            try:current = await run_in_threadpool(catalog) if remote else catalog()
            except MiniError:
                if not remote:raise
                current=None
            raw = contents['gauntlet_data.json']
            expected = digest((info['id']+':').encode()+raw) if getattr(service, 'production', False) else digest(raw)
            if current is not None and current['version'] != expected:
                fail(409, 'CATALOG_CHANGED', '读取期间活动目录变化，请重试')
            version = current['version'] if current is not None else None
        return {'schema_version': 1, 'server': server, 'version': info['id'], 'catalog_version': version,
                'identity': request.state.guest['identity'],
                'capabilities': {'zones': ['zone5'] if server == 'global' else ['zone5', 'zone4'],
                                 'tiers': ['理论'] if server == 'global' else ['理论', '高手', '普通', '自动'],
                                 'map_recognition': version is not None},
                'files': {n: {'text': contents[n].decode('utf-8'), 'sha256': digest(contents[n]), 'bytes': len(contents[n])} for n in names}}

    @app.get(PREFIX+'/map-recognition/catalog')
    async def read_catalog(request: Request):
        if parameters(request, ['server'])['server'] != 'cn':
            fail(403, 'RECOGNITION_SERVER_DISABLED', '国际服识图尚未开放')
        current = await run_in_threadpool(catalog) if remote else catalog()
        return {**current, 'catalog_version': current['version'], 'identity': request.state.guest['identity'],
                'max_bytes': MAX_BYTES, 'max_pixels': MAX_PIXELS, 'max_envelope_bytes': MAX_ENVELOPE,
                'worker': service.health(), 'retention_seconds': TTL, 'metadata_grace_seconds': 600,
                'content_safety': 'required_approval' if remote else 'not_integrated'}

    @app.get(PREFIX+'/map-recognition/jobs/by-request')
    async def recover(request: Request):
        params, current = await cn_binding(request, True)
        owner, key = request.state.guest['owner'], params['request_key']
        if remote:
            recovered=await run_in_threadpool(service.recover,owner,key)
            if recovered.get('recovery')=='found':return {'recovery':'found',**response_for(recovered,current)}
        else:
            service.store.cleanup()
            with service.store.connect() as db:
                row = db.execute('SELECT * FROM jobs WHERE owner=? AND request_key=?', (owner, key)).fetchone()
            if row:return {'recovery': 'found', **response_for(lookup(owner, row['id']), current)}
        with store.connect() as db:
            row = db.execute('SELECT version,state,updated FROM uploads WHERE owner=? AND request_key=?', (owner, key)).fetchone()
        if row and row[0] != current['version']:
            fail(409, 'CATALOG_CHANGED', '原上传目录版本不同')
        if row and row[1] == 'committed':
            fail(410, 'JOB_EXPIRED', '原任务元数据已清理，不要自动重传')
        reading = row and row[1] == 'reading' and time.time()-row[2] < 30
        return JSONResponse({'recovery': 'reading' if reading else ('interrupted' if row else 'not_found'),
                             'retry_same_key': not reading}, headers={'Retry-After': '2'} if reading else None)

    @app.post(PREFIX+'/map-recognition/jobs', status_code=202)
    async def upload(request: Request):
        params, current = await cn_binding(request, True, require_upload=True)
        owner, key = request.state.guest['owner'], params['request_key']
        if not remote:service.store.cleanup()
        lease = secrets.token_hex(16)
        with store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            old = db.execute('SELECT version,state,updated FROM uploads WHERE owner=? AND request_key=?', (owner, key)).fetchone()
            if old and old[0] != current['version']:
                fail(409, 'REQUEST_KEY_CONFLICT', '同请求编号不能用于不同目录')
            if old and old[1] == 'reading' and time.time()-old[2] < 30:
                fail(409, 'UPLOAD_READING', '原上传仍在读取，请按原编号查询', 2)
            if old is None and db.execute('SELECT count(*) FROM uploads').fetchone()[0] >= 10000:
                fail(503, 'SESSION_CAPACITY', '上传恢复状态暂不可用', 30)
            if (db.execute("SELECT count(*) FROM uploads WHERE state='reading' AND updated>?", (time.time()-30,)).fetchone()[0] >= 8
                    or db.execute("SELECT count(*) FROM uploads WHERE owner=? AND state='reading' AND updated>?", (owner, time.time()-30)).fetchone()[0] >= 2):
                fail(429, 'UPLOAD_READ_LIMITED', '上传读取繁忙，请稍后查询或重试', 5)
            db.execute('INSERT INTO uploads VALUES (?,?,?,?,?,?) ON CONFLICT(owner,request_key) DO UPDATE SET state=excluded.state,lease=excluded.lease,updated=excluded.updated',
                       (owner, key, current['version'], 'reading', lease, time.time()))
        try:
            if remote:
                preflight=await run_in_threadpool(service.preflight,owner,key,request.scope['mini_ip'])
                existing=preflight['existing']
            else:
                with service.store.connect() as db:
                    existing = db.execute('SELECT id FROM jobs WHERE owner=? AND request_key=?', (owner, key)).fetchone()
                    if not existing:
                        if service.health() not in ('ready', 'working'):
                            fail(503, 'OCR_UNAVAILABLE', '识别服务暂不可用', 5)
                        if db.execute("SELECT count(*) FROM jobs WHERE state IN ('queued','running')").fetchone()[0] >= 8:
                            fail(429, 'OCR_LIMITED', '识别队列已满', 5)
                        if db.execute("SELECT count(*) FROM jobs WHERE owner=? AND state IN ('queued','running')", (owner,)).fetchone()[0] >= 2:
                            fail(429, 'OCR_LIMITED', '已有识别正在进行', 5)
                        if db.execute('SELECT count(*) FROM jobs WHERE owner=? AND created>?', (owner, time.time()-600)).fetchone()[0] >= 20:
                            fail(429, 'OCR_LIMITED', '截图提交过于频繁', 5)
                        if getattr(service, 'production', False):
                            client = digest(('ocr-client:'+request.scope['mini_ip']).encode())
                            if db.execute('SELECT count(*) FROM jobs WHERE client=? AND created>?', (client, time.time()-600)).fetchone()[0] >= 20:
                                fail(429, 'OCR_LIMITED', '当前网络截图提交过于频繁', 5)
            if not existing:
                store.budget('upload-owner:'+owner, 20, 600)
                store.budget('upload-ip:'+request.state.mini_client, 20, 600)
            raw = await limited_body(request, MAX_ENVELOPE)
            image, mime = multipart_image(raw, request.headers.get('content-type', ''), MAX_BYTES)
            await run_in_threadpool(validate_image, image, mime)
            # Recheck after reading/decoding; old tasks never cross a publication boundary.
            latest=await run_in_threadpool(catalog) if remote else catalog()
            if latest['version'] != current['version']:
                fail(409, 'CATALOG_CHANGED', '读取期间目录版本变化')
            with store.connect() as db:
                claim = db.execute('SELECT lease FROM uploads WHERE owner=? AND request_key=?', (owner, key)).fetchone()
            if not claim or claim[0] != lease:
                fail(409, 'UPLOAD_REPLACED', '上传读取已失效，请查询原编号')
            options = {'catalog': current, 'client': digest(('ocr-client:'+request.scope['mini_ip']).encode())} if getattr(service, 'production', False) else {}
            if remote:
                remote_row=await run_in_threadpool(service.submit,owner,key,request.scope['mini_ip'],image,mime)
                job_id=remote_row['id']
            else:job_id = service.store.create(owner, key, 'cn', current['version'], image, mime, **options)
            with store.connect() as db:
                db.execute("UPDATE uploads SET state='committed',updated=? WHERE owner=? AND request_key=? AND lease=?", (time.time(), owner, key, lease))
            return response_for(await owned(owner, job_id), current)
        finally:
            # A disconnect is recoverable with the same key; committed jobs are found in the shared queue first.
            with store.connect() as db:
                db.execute("UPDATE uploads SET state='interrupted',updated=? WHERE owner=? AND request_key=? AND lease=? AND state='reading'", (time.time(), owner, key, lease))

    @app.get(PREFIX+'/map-recognition/jobs/{job_id}')
    async def query(job_id: str, request: Request):
        _, current = await cn_binding(request)
        service.health()
        return response_for(await owned(request.state.guest['owner'], job_id), current)

    @app.delete(PREFIX+'/map-recognition/jobs/{job_id}')
    async def cancel(job_id: str, request: Request):
        _, current = await cn_binding(request)
        owner = request.state.guest['owner']
        row = await owned(owner, job_id)
        response_for(row, current)
        if remote:await run_in_threadpool(service.cancel,owner,job_id)
        else:service.store.cancel(owner, job_id, 'cn')
        return response_for(await owned(owner, job_id), current)

    return app


class MiniGateway:
    """Outer ASGI dispatch, so the website boundary is unchanged for every website path."""
    def __init__(self, app, *, config, source, service, origin, production):
        self.app, self.origin, self.production = app, urlsplit(origin), production
        if config is not None and production and config.get('fixture'):
            raise ValueError('生产禁止使用fixture微信验证')
        self.native = make_native(config, source, service) if config is not None else None
        self.account=None
        if config is not None and config.get('account_store') is not None:
            from backend.mini_accounts import make_native_account
            roots=[config['store'].root]+([service.root] if service is not None else [])
            account_root=config['account_store'].root
            if any(account_root.is_relative_to(root) or root.is_relative_to(account_root) for root in roots):
                raise ValueError('账号原生状态必须与访客/队列使用互不包含的独立目录')
            self.account=make_native_account(config,source)

    async def __call__(self, scope, receive, send):
        path = scope.get('path', '')
        is_account=path==ACCOUNT_PREFIX or path.startswith(ACCOUNT_PREFIX+'/')
        if scope['type'] != 'http' or not (is_account or path == PREFIX or path.startswith(PREFIX+'/')):
            return await self.app(scope, receive, send)
        request = Request(scope, receive)
        async def secure_send(message):
            if message['type'] == 'http.response.start':
                message['headers'] = [(k,v) for k,v in message.get('headers', []) if k.lower() not in (b'cache-control', b'access-control-allow-origin')]
                message['headers'] += [(b'cache-control', b'no-store'), (b'x-content-type-options', b'nosniff'), (b'referrer-policy', b'no-referrer')]
            await send(message)
        try:
            target=self.account if is_account else self.native
            if target is None:
                fail(404, 'NATIVE_DISABLED', '原生入口未启用')
            if request.headers.get('host') != self.origin.netloc:
                fail(400, 'INVALID_HOST', '无效Host')
            if self.production:
                if scope['client'][0] not in ('127.0.0.1', '::1') or request.headers.get('x-forwarded-proto') != 'https':
                    fail(400, 'TRUSTED_PROXY_REQUIRED', '仅接受可信HTTPS反向代理')
                try:
                    ip = str(ipaddress.ip_address(request.headers.get('x-real-ip', '')))
                except ValueError:
                    fail(400, 'TRUSTED_PROXY_REQUIRED', '缺少可信客户端地址')
            else:
                ip = scope['client'][0]
            scope['mini_ip'] = ip
            return await target(scope, receive, secure_send)
        except MiniError as error:
            return await error_response(error)(scope, receive, secure_send)
