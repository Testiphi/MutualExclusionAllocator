"""Opt-in LOCAL screenshot jobs. Separate files/database; no score writes."""
from contextlib import contextmanager,asynccontextmanager
from pathlib import Path
import hashlib
import io
import json
import os
import secrets
import sqlite3
import subprocess
import sys
import time
import shutil

MAX_BYTES=8*1024*1024
MAX_PIXELS=16_000_000
TTL=3600
MIMES={'PNG':'image/png','JPEG':'image/jpeg','WEBP':'image/webp'}


class RecognitionError(Exception):
    def __init__(self,status,message):self.status=status;self.message=message;super().__init__(message)


def digest(raw):return hashlib.sha256(raw).hexdigest()


def validate_image(raw,mime):
    from PIL import Image,UnidentifiedImageError
    if not raw or len(raw)>MAX_BYTES:raise RecognitionError(413,'图片不能为空，且不得超过8MB')
    try:
        with Image.open(io.BytesIO(raw)) as image:
            width,height=image.size
            if image.format not in MIMES or MIMES[image.format]!=mime:
                raise RecognitionError(422,'请选择真实的PNG、JPEG或WebP图片')
            if width*height>MAX_PIXELS or width<1 or height<1 or getattr(image,'n_frames',1)!=1:
                raise RecognitionError(422,'图片像素过大或为动画，请改用静态截图')
            if width<600 or height<300 or not 1.30<=width/height<=2.20:
                raise RecognitionError(422,'请上传完整的横屏游戏截图')
            image.verify()
    except RecognitionError:raise
    except Exception as exc:raise RecognitionError(422,'图片无法解码，请重新选择原始截图') from exc
    return width,height


class JobStore:
    def __init__(self,root,production=False):
        self.production=production
        self.root=Path(root).resolve();self.media=self.root/'media';self.path=self.root/'recognition.sqlite3'
        marker=self.root/('queue.json' if production else '.racepick-map-demo.json')
        expected='racepick-map-queue-v1' if production else 'racepick-local-map-recognition'
        if not marker.is_file() or marker.is_symlink() or json.loads(marker.read_text(encoding='utf-8')).get('kind')!=expected:
            raise ValueError('识图只允许显式创建的独立本地demo目录')
        if (self.root/'production.json').exists():raise ValueError('禁止使用生产目录')
        self.media.mkdir(exist_ok=True)
        if self.media.is_symlink() or self.media.resolve()!=self.media:raise ValueError('上传目录不能为符号链接')
        for path in self.root.glob('recognition.sqlite3*'):
            if path.is_symlink() or path.stat().st_nlink!=1:raise ValueError('识图数据库不能为链接')
        with self.connect() as db:
            db.execute('PRAGMA journal_mode=WAL')
            db.executescript('''CREATE TABLE IF NOT EXISTS jobs(
                id TEXT PRIMARY KEY, owner TEXT NOT NULL, request_key TEXT NOT NULL,
                server TEXT NOT NULL, version TEXT NOT NULL, image_sha TEXT NOT NULL,
                mime TEXT NOT NULL, state TEXT NOT NULL, created REAL NOT NULL, expires REAL NOT NULL,
                started REAL, finished REAL, result TEXT, error TEXT,
                UNIQUE(owner,request_key));''')
            if production:
                columns={r[1] for r in db.execute('PRAGMA table_info(jobs)')}
                for name in ('catalog','client'):
                    if name not in columns:db.execute('ALTER TABLE jobs ADD COLUMN '+name+' TEXT')
                db.execute('CREATE INDEX IF NOT EXISTS job_expiry ON jobs(expires)')
                db.execute('CREATE INDEX IF NOT EXISTS job_state ON jobs(state,created)')
                db.execute('CREATE INDEX IF NOT EXISTS job_client ON jobs(client,created)')
                db.execute('PRAGMA journal_size_limit=1048576')
                db.execute('PRAGMA max_page_count=8192')

    @contextmanager
    def connect(self):
        db=sqlite3.connect(self.path,timeout=15);db.row_factory=sqlite3.Row
        try:
            with db:yield db
        finally:db.close()

    def image_path(self,job_id):
        if len(job_id)!=32 or any(c not in '0123456789abcdef' for c in job_id):raise RecognitionError(404,'任务不存在')
        p=self.media/(job_id+'.image')
        if p.is_symlink():raise RecognitionError(409,'图片文件状态异常')
        return p

    def remove_media(self,job_id):
        p=self.image_path(job_id)
        if p.exists():p.unlink()

    def cleanup(self):
        now=time.time()
        with self.connect() as db:
            ids=[r['id'] for r in db.execute("SELECT id FROM jobs WHERE expires<=? AND state!='expired'",(now,))]
            db.execute("UPDATE jobs SET state='expired',result=NULL,error='图片与结果已到期，请重新上传' WHERE expires<=?",(now,))
            if self.production:
                db.execute("DELETE FROM jobs WHERE expires<?",(now-600,))
            else:
                # Native V1 retention also applies in explicitly isolated local integration.
                # Historical website demo rows retain their existing lifecycle.
                db.execute("DELETE FROM jobs WHERE owner LIKE 'mini-v1:%' AND expires<?",(now-600,))
        for job_id in ids:self.remove_media(job_id)

    def create(self,owner,key,server,version,raw,mime,*,catalog=None,client=None):
        self.cleanup();image_sha=digest(raw)
        if not 16<=len(key)<=80 or not all(c.isalnum() or c in '-_' for c in key):
            raise RecognitionError(422,'请求编号无效，请重新开始')
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            old=db.execute('SELECT * FROM jobs WHERE owner=? AND request_key=?',(owner,key)).fetchone()
            if old:
                if (old['image_sha'],old['server'],old['version'])!=(image_sha,server,version):
                    raise RecognitionError(409,'同一请求编号不能用于不同截图或服别')
                if old['state']=='expired':raise RecognitionError(410,'任务已到期，请重新开始')
                return old['id']
            if db.execute("SELECT count(*) FROM jobs WHERE owner=? AND state IN ('queued','running')",(owner,)).fetchone()[0]>=2:
                raise RecognitionError(429,'已有识别正在进行，请等待或取消后重试')
            if db.execute("SELECT count(*) FROM jobs WHERE state IN ('queued','running')").fetchone()[0]>=8:
                raise RecognitionError(429,'识别队列已满，请稍后重试')
            if db.execute('SELECT count(*) FROM jobs WHERE owner=? AND created>?',(owner,time.time()-600)).fetchone()[0]>=20:
                raise RecognitionError(429,'截图提交过于频繁，请稍后再试')
            if self.production:
                if not catalog or not client:raise RecognitionError(503,'识别服务配置不完整')
                if db.execute('SELECT count(*) FROM jobs WHERE client=? AND created>?',(client,time.time()-600)).fetchone()[0]>=20:
                    raise RecognitionError(429,'截图提交过于频繁，请稍后再试')
                if db.execute('SELECT count(*) FROM jobs').fetchone()[0]>=10000:
                    raise RecognitionError(503,'识别服务繁忙，请稍后再试')
                used=sum(p.stat().st_size for p in self.media.glob('*.image') if not p.is_symlink())
                if used+len(raw)>128*1024*1024 or shutil.disk_usage(self.root).free<64*1024*1024:
                    raise RecognitionError(503,'识别存储暂不可用，请稍后再试')
            job_id=secrets.token_hex(16);now=time.time();path=self.image_path(job_id)
            try:
                with path.open('xb') as f:f.write(raw)
                db.execute('INSERT INTO jobs(id,owner,request_key,server,version,image_sha,mime,state,created,expires) VALUES (?,?,?,?,?,?,?,?,?,?)',
                           (job_id,owner,key,server,version,image_sha,mime,'queued',now,now+TTL))
                if self.production:db.execute('UPDATE jobs SET catalog=?,client=? WHERE id=?',(json.dumps(catalog,ensure_ascii=False),client,job_id))
            except Exception:
                if path.exists():path.unlink()
                raise
        return job_id

    def expire_pending(self,queue_seconds=120):
        with self.connect() as db:
            ids=[r[0] for r in db.execute("SELECT id FROM jobs WHERE state='queued' AND created<?",(time.time()-queue_seconds,))]
            db.execute("UPDATE jobs SET state='failed',error='等待识别超时，请稍后重试',finished=? WHERE state='queued' AND created<?",(time.time(),time.time()-queue_seconds))
        for job_id in ids:self.remove_media(job_id)

    def fail_running(self,message):
        with self.connect() as db:
            ids=[r[0] for r in db.execute("SELECT id FROM jobs WHERE state='running'")]
            db.execute("UPDATE jobs SET state='failed',error=?,finished=? WHERE state='running'",(message,time.time()))
        for job_id in ids:self.remove_media(job_id)

    def get(self,owner,job_id,server):
        self.image_path(job_id);self.cleanup()
        with self.connect() as db:
            row=db.execute('SELECT * FROM jobs WHERE id=? AND owner=? AND server=?',(job_id,owner,server)).fetchone()
        if not row:raise RecognitionError(404,'任务不存在或不属于当前会话')
        if row['state']=='expired':raise RecognitionError(410,'图片与识别结果已到期，请重新上传')
        return dict(row)

    def cancel(self,owner,job_id,server):
        self.get(owner,job_id,server)
        with self.connect() as db:
            db.execute("UPDATE jobs SET state='cancelled',result=NULL,error=NULL,finished=? WHERE id=? AND owner=?",(time.time(),job_id,owner))
        self.remove_media(job_id)

    def fail_pending(self,message):
        with self.connect() as db:
            db.execute("UPDATE jobs SET state='failed',error=?,finished=? WHERE state IN ('queued','running')",(message,time.time()))

    def claim(self):
        self.cleanup()
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row=db.execute("SELECT * FROM jobs WHERE state='queued' ORDER BY created,id LIMIT 1").fetchone()
            if row:
                db.execute("UPDATE jobs SET state='running',started=? WHERE id=? AND state='queued'",(time.time(),row['id']))
                return dict(row)
        return None

    def finish(self,job_id,*,result=None,error=None):
        with self.connect() as db:
            # Cancelled/expired work can never publish a late result.
            db.execute("UPDATE jobs SET state=?,result=?,error=?,finished=? WHERE id=? AND state='running' AND expires>?",
                       ('failed' if error else 'succeeded',json.dumps(result,ensure_ascii=False) if result else None,error,time.time(),job_id,time.time()))


class RecognitionService:
    def __init__(self,config_path):
        self.config_path=Path(config_path).resolve();self.config=json.loads(self.config_path.read_text(encoding='utf-8'))
        self.root=Path(self.config['root']).resolve();self.reference=Path(self.config['reference']).resolve()
        if self.config_path.parent!=self.root or self.reference!=self.root/'reference':raise ValueError('demo来源目录不匹配')
        self.store=JobStore(self.root);self.process=None;self.run_id=None
        self.catalog('cn');self.catalog('global')

    def catalog(self,server):
        if server not in ('cn','global'):raise RecognitionError(422,'请选择国服或国际服')
        name='gauntlet_data.global.json' if server=='global' else 'gauntlet_data.json'
        raw=(self.reference/name).read_bytes()
        if digest(raw)!=self.config['reference_sha256'][name]:raise RecognitionError(409,'demo目录来源已变化，请重新核验后启动')
        data=json.loads(raw);maps=[{'big':x['大地图'],'small':x['小地图']} for x in data['tracks']]
        return dict(server=server,version=digest(raw),maps=maps)

    def start(self):
        self.store.fail_pending('服务已重新启动，请重新识别')
        self.run_id=secrets.token_hex(8)
        log=(self.root/'worker.log').open('ab')
        try:
            self.process=subprocess.Popen([sys.executable,'-B','-X','utf8','-m','backend.map_ocr_worker',
                '--config',str(self.config_path),'--run-id',self.run_id],cwd=Path(__file__).resolve().parents[1],
                stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
        finally:log.close()

    def health(self):
        if self.process is None:return 'starting'
        if self.process.poll() is not None:
            self.store.fail_pending('识别进程已停止，请重新启动本地demo后重试')
            return 'unavailable'
        p=self.root/'worker-state.json'
        try:
            status=json.loads(p.read_text(encoding='utf-8'))
            return status['state'] if status.get('run_id')==self.run_id else 'starting'
        except (OSError,ValueError):return 'starting'

    def stop(self):
        if self.process and self.process.poll() is None:
            (self.root/('stop-'+self.run_id)).write_text('stop',encoding='ascii')
            try:self.process.wait(timeout=8)
            except subprocess.TimeoutExpired:self.process.terminate();self.process.wait(timeout=8)
        self.store.fail_pending('服务已停止，请重新识别')


def install(app,service,session,user):
    from fastapi import Request,HTTPException,Query
    from fastapi.responses import FileResponse

    def who(request):
        current=session(request)
        if current['user_id']:user(request)
        return digest(('recognition:'+current['token_hash']+':'+str(current['user_id'])).encode())

    def guard(fn,*args,**kwargs):
        try:return fn(*args,**kwargs)
        except RecognitionError as exc:raise HTTPException(exc.status,exc.message) from exc

    previous_lifespan=app.router.lifespan_context
    @asynccontextmanager
    async def lifespan(application):
        async with previous_lifespan(application) as state:
            service.start()
            try:yield state
            finally:service.stop()
    app.router.lifespan_context=lifespan

    @app.get('/api/map-recognition/catalog')
    def catalog(request:Request,server:str='cn'):
        return {**guard(service.catalog,server),'identity':who(request),'max_bytes':MAX_BYTES,'retention_seconds':TTL,
                'worker':service.health()}

    @app.post('/api/map-recognition/jobs',status_code=202)
    async def create(request:Request,server:str=Query(max_length=12),catalog_version:str=Query(max_length=64),request_key:str=Query(max_length=80)):
        owner=who(request);catalog=guard(service.catalog,server)
        if catalog['version']!=catalog_version:raise HTTPException(409,'地图目录版本已变化，请刷新后重新识别')
        if service.health()=='unavailable' or (getattr(service,'production',False) and service.health()!='ready'):
            raise HTTPException(503,'识别服务暂不可用，手动选图仍可使用')
        raw=await request.body();mime=request.headers.get('content-type','').split(';')[0]
        guard(validate_image,raw,mime)
        options={}
        if getattr(service,'production',False):
            options={'catalog':catalog,'client':digest(('ocr-client:'+request.state.client_ip).encode())}
        try:job=guard(service.store.create,owner,request_key,server,catalog_version,raw,mime,**options)
        except (OSError,sqlite3.Error):raise HTTPException(503,'识别存储暂不可用，请稍后再试') from None
        return {'id':job,'server':server,'catalog_version':catalog_version}

    @app.get('/api/map-recognition/jobs/{job_id}')
    def status(job_id:str,request:Request,server:str='cn'):
        service.health();row=guard(service.store.get,who(request),job_id,server)
        if row['version']!=guard(service.catalog,server)['version']:raise HTTPException(409,'地图目录版本已变化，请重新识别')
        return {'id':row['id'],'server':row['server'],'catalog_version':row['version'],'state':row['state'],
                'result':json.loads(row['result']) if row['result'] else None,'error':row['error'],
                'expires_at':row['expires']}

    @app.delete('/api/map-recognition/jobs/{job_id}')
    def cancel(job_id:str,request:Request,server:str='cn'):
        guard(service.store.cancel,who(request),job_id,server);return {'state':'cancelled'}

    if getattr(service,'production',False):return

    @app.get('/api/map-recognition/examples')
    def examples(request:Request):
        who(request)
        return [{'id':k,'title':v['title']} for k,v in service.config.get('examples',{}).items()]

    @app.get('/api/map-recognition/examples/{example_id}')
    def example(example_id:str,request:Request):
        who(request);item=service.config.get('examples',{}).get(example_id)
        if not item:raise HTTPException(404,'样例不存在')
        path=service.root/'examples'/item['filename']
        if path.parent!=service.root/'examples' or path.is_symlink():raise HTTPException(404)
        from PIL import Image
        if digest(path.read_bytes())!=item['sha256']:raise HTTPException(409,'样例来源已变化')
        with Image.open(path) as image:mime=MIMES.get(image.format)
        if mime is None:raise HTTPException(422,'样例格式不支持')
        return FileResponse(path,media_type=mime,headers={'Cache-Control':'no-store'})
