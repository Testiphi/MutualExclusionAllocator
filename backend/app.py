"""RacePick local account service. Not a production deployment entry point."""
import argparse
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import secrets
import sqlite3
import time
from urllib.parse import urlsplit

from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, InvalidHashError
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response
from pydantic import BaseModel, ConfigDict, Field, StrictInt, field_validator

ROOT = Path(__file__).resolve().parents[1]
COOKIE = 'racepick_local_session'
HASHER = PasswordHasher()
DUMMY = HASHER.hash('dummy-password-not-a-real-user')


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


class Credentials(BaseModel):
    model_config = ConfigDict(extra='forbid')
    email: str = Field(max_length=254)
    password: str = Field(min_length=12, max_length=128)

    @field_validator('email')
    @classmethod
    def email_valid(cls, value):
        value = value.strip().lower()
        import re
        if not re.fullmatch(r'[a-z0-9.!#$%&\'*+/=?^_`{|}~-]+@[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?\.[a-z]{2,}', value):
            raise ValueError('邮箱格式不正确')
        return value


class Registration(Credentials):
    invite_code: str = Field(default='',max_length=128)


class EmailInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    email: str = Field(max_length=254)

    @field_validator('email')
    @classmethod
    def email_valid(cls,value):return Credentials.email_valid(value)


class TokenInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    token: str = Field(min_length=20, max_length=128)


class ResetInput(TokenInput):
    password: str = Field(min_length=12, max_length=128)


class ProfileInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    revision: StrictInt = Field(ge=0)
    cars: list[str] = Field(max_length=500)
    stars: dict[str, StrictInt] = Field(max_length=500)


class Store:
    def __init__(self, directory, initialize=True):
        self.directory = Path(directory)
        self.initialize = initialize
        self.path = self.directory / 'accounts.sqlite3'
        if not initialize:
            if not self.directory.is_dir() or not self.path.is_file():
                raise ValueError('Account state must be explicitly provisioned before startup')
            return
        self.directory.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.executescript('''
            CREATE TABLE IF NOT EXISTS schema_version(version INTEGER PRIMARY KEY);
            INSERT OR IGNORE INTO schema_version VALUES (1);
            CREATE TABLE IF NOT EXISTS users(
                id TEXT PRIMARY KEY, email TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL,
                verified INTEGER NOT NULL DEFAULT 0, role TEXT NOT NULL DEFAULT 'player'
                CHECK(role IN ('player','admin')), created_at INTEGER NOT NULL);
            CREATE TABLE IF NOT EXISTS sessions(
                token_hash TEXT PRIMARY KEY, user_id TEXT REFERENCES users(id),
                csrf TEXT NOT NULL, expires_at INTEGER NOT NULL);
            CREATE TABLE IF NOT EXISTS profiles(
                user_id TEXT PRIMARY KEY REFERENCES users(id), cars TEXT NOT NULL,
                stars TEXT NOT NULL, revision INTEGER NOT NULL, updated_at INTEGER NOT NULL);
            CREATE TABLE IF NOT EXISTS auth_tokens(
                token_hash TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id),
                purpose TEXT NOT NULL, expires_at INTEGER NOT NULL);
            CREATE TABLE IF NOT EXISTS attempts(bucket TEXT PRIMARY KEY, count INTEGER NOT NULL, expires_at INTEGER NOT NULL);
            ''')
            from backend.submissions import migrate
            migrate(db)
            from backend.mailing import migrate_mail
            migrate_mail(db)
            from backend.roles import migrate_roles
            migrate_roles(db)
            from backend.previews import migrate_previews
            migrate_previews(db)
            from backend.community import migrate as migrate_community
            migrate_community(db)

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path if self.initialize else self.path.absolute().as_uri()+'?mode=rw',
                             uri=not self.initialize, timeout=10)
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA foreign_keys=ON')
        try:
            with db:
                yield db
        finally:
            db.close()

    def throttle(self, key, limit=10):
        now = int(time.time())
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            db.execute('DELETE FROM attempts WHERE expires_at <= ?', (now,))
            row = db.execute('SELECT count FROM attempts WHERE bucket=?', (key,)).fetchone()
            if row and row['count'] >= limit:
                raise HTTPException(429, '尝试过于频繁，请十分钟后重试')
            db.execute('INSERT INTO attempts VALUES (?,1,?) ON CONFLICT(bucket) DO UPDATE SET count=count+1', (key, now+600))


def create_app(data_dir=None, origin='http://127.0.0.1:8000', reference_dir=None, mail_config=None, preview_source=None, writeback_lab=None, production=False, score_version_lab=None, score_state=None, contributions=False, feedback=False, notifications=False, usage=False, coverage=False, map_recognition=None, mini_config=None, isolated_account_root=None):
    isolated = isolated_account_root is not None
    frozen = None
    if isolated:
        # An explicit, marked, new isolation root is the ONLY file-mail HTTPS exception.
        # Validate before Store, mini config, credentials, or any migration can open state.
        from backend.mini_account_isolation import preflight
        from backend.mini_snapshot import load_snapshot
        preflight(isolated_account_root, origin)
        if (not production or Path(data_dir).absolute()!=Path(isolated_account_root).absolute()/'accounts'
                or reference_dir is not None or any((preview_source,writeback_lab,score_version_lab,score_state,
                    contributions,feedback,notifications,usage,coverage,map_recognition,mini_config))
                or mail_config is None or mail_config.mode!='file' or mail_config.production):
            raise ValueError('Isolated HTTPS accounts require file mail and no other business components')
        frozen,_=load_snapshot(Path(isolated_account_root)/'snapshot')
    if mini_config is not None:
        from backend.mini_auth import load_config
        if isinstance(mini_config, (str, Path)):
            mini_config=load_config(mini_config)
        if production and mini_config.get('fixture'):
            raise ValueError('生产禁止使用fixture微信验证')
    recognition_service=None
    if map_recognition is not None:
        if production:
            from backend.map_ocr_production import ProductionRecognitionService,settings as ocr_settings
            if score_state is None or ocr_settings(map_recognition)!=Path(data_dir).absolute()/'map-recognition':
                raise ValueError('生产识图必须绑定现有成绩环境下独立的map-recognition目录')
            recognition_service=ProductionRecognitionService(map_recognition)
        elif score_state is not None or writeback_lab is not None or preview_source is not None or reference_dir is not None:
            raise ValueError('截图识图demo只能运行在独立本地环境，不能混用正式库或写回实验室')
        else:
            from backend.map_recognition import RecognitionService
            recognition_service=RecognitionService(map_recognition)
            if Path(data_dir or '').resolve()!=recognition_service.root/'accounts':
                raise ValueError('截图识图demo必须使用自身隔离账号目录')
        if not production and score_version_lab is not None:
            from backend.score_repository import validate_lab
            lab,_=validate_lab(score_version_lab,data_dir)
            if lab!=recognition_service.root:
                raise ValueError('整合预览必须使用同一隔离目录，不得连接其他成绩实验室')
    if feedback and (not contributions or (production and score_state is None) or (not production and score_version_lab is None)):
        raise ValueError("问题反馈需要已绑定成绩及贡献环境")
    if contributions and ((production and score_state is None) or (not production and score_version_lab is None)):
        raise ValueError("排行榜需要已绑定的成绩版本环境")
    parsed = urlsplit(origin)
    if production:
        if parsed.scheme!='https' or not parsed.hostname or parsed.hostname in ('127.0.0.1','localhost') or parsed.port not in (None,443) or parsed.path or parsed.query or parsed.fragment or parsed.username or parsed.password:
            raise ValueError('生产环境需要精确HTTPS域名来源')
        if score_version_lab is not None or writeback_lab is not None or preview_source is not None:raise ValueError('生产环境禁止启用预览及写回实验室')
        if not isolated and (not data_dir or mail_config is None or not mail_config.production):raise ValueError('生产环境需独立数据目录和正式SMTP配置')
    elif parsed.scheme != 'http' or parsed.hostname not in ('127.0.0.1', 'localhost') or parsed.path or parsed.query or parsed.fragment or parsed.username:
        raise ValueError('本地开发仅允许 localhost/127.0.0.1 HTTP origin')
    cookie_name = '__Host-racepick_session' if production else (COOKIE if parsed.port in (None,8000) else COOKIE+'_'+str(parsed.port))
    if writeback_lab is not None:
        from backend.writeback_lab import validate_lab
        validate_lab(writeback_lab, data_dir or ROOT/'.local-accounts', preview_source)
        if preview_source is None: raise ValueError('测试写回必须显式指定测试来源')
        reference_dir=preview_source
        if mail_config is not None and mail_config.mode!='file': raise ValueError('测试写回仅使用本地文件邮件')
    if score_version_lab is not None:
        from backend.score_repository import validate_lab
        validate_lab(score_version_lab,data_dir or ROOT/'.local-accounts')
        if preview_source is not None or writeback_lab is not None or reference_dir is not None:raise ValueError('数据版本实验室不能混用其他来源')
        if mail_config is not None and mail_config.mode!='file':raise ValueError('数据版本实验室仅使用文件邮件')
    if score_state is not None and (not production or score_version_lab is not None):raise ValueError('score_state仅供独立生产入口使用')
    versioned_scores=score_version_lab is not None or score_state is not None
    if coverage and not production and data_dir and (Path(data_dir)/"production.json").exists():raise ValueError("正式库禁止通过本地coverage入口迁移")
    fresh_accounts=not (Path(data_dir or ROOT / '.local-accounts')/'accounts.sqlite3').exists()
    store = Store(data_dir or ROOT / '.local-accounts', initialize=not isolated)
    from backend.global_profiles import state as global_profile_state,migrate as migrate_global_profiles,GlobalProfileInput
    if fresh_accounts and not production:migrate_global_profiles(store)
    with store.connect() as db:global_profiles_ready=global_profile_state(db)['global_profile_schema']==1
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None, redirect_slashes=not production)
    app.state.production = production
    app.state.store = store
    app.state.global_profiles=global_profiles_ready
    app.state.contributions = contributions
    app.state.feedback = feedback
    app.state.notifications = notifications
    app.state.coverage = coverage
    if coverage and (not contributions or not versioned_scores):raise ValueError("成绩表需要贡献账本和版本化成绩")
    from backend.coverage import state as coverage_state, migrate as migrate_coverage
    with store.connect() as db:
        ready=coverage_state(db)["coverage_schema"]
        if ready and not coverage:raise ValueError("成绩表权限已启用，必须带coverage启动")
        if coverage:
            if production and ready!=2:raise ValueError("成绩表权限尚未显式迁移至双服schema2")
            if not production:db.execute("BEGIN IMMEDIATE");migrate_coverage(db)
    from backend.usage import UsageStore
    usage_path = store.directory / "usage.sqlite3"
    if usage_path.exists() and not usage:
        raise ValueError("此环境已启用使用统计，启动须带 --usage")
    if usage and not usage_path.exists():
        if production: raise ValueError("统计库尚未显式初始化，生产启动不创建")
        UsageStore.initialize(usage_path)
    app.state.usage = UsageStore(usage_path) if usage else None
    app.state.record_usage = lambda *args: None
    def usage_html(html):
        return html.replace("</head>", '<script>globalThis.RACEPICK_USAGE_ENABLED=true;</script><script defer src="/usage.js"></script></head>') if usage else html
    app.state.usage_html = usage_html
    with store.connect() as db:
        present=db.execute("SELECT 1 FROM sqlite_master WHERE name='feedback_schema'").fetchone()
        if present and not feedback: raise ValueError("此数据库已启用反馈，启动必须启用反馈功能")
        if feedback:
            from backend.feedback import migrate as migrate_feedback
            if production:
                from backend.feedback import state as feedback_state
                if feedback_state(db)["feedback_schema"]!=1: raise ValueError("反馈迁移尚未完成，生产启动不自动迁移")
            else:
                db.execute("BEGIN IMMEDIATE"); migrate_feedback(db)
    with store.connect() as db:
        from backend.contributions import available, migrate
        if available(db) and not contributions:
            raise ValueError("此环境已启用排行榜，必须带 --contributions 启动")
        if contributions:
            if production:
                from backend.contribution_production import state
                if state(db)["contribution_schema"]!=1: raise ValueError("贡献迁移尚未完成，生产启动不自动迁移")
            else:
                db.execute("BEGIN IMMEDIATE"); migrate(db)
    with store.connect() as db:
        from backend.notifications import state as notification_state, migrate as migrate_notifications
        ready = notification_state(db)["notification_schema"]
        if ready and not notifications:
            raise ValueError("此数据库已启用未读提醒，启动须启用 notifications")
        if notifications:
            if production:
                if ready != 1: raise ValueError("未读提醒迁移未完成，生产启动不自动迁移")
            else:
                db.execute("BEGIN IMMEDIATE"); migrate_notifications(db)
    if versioned_scores:
        from backend.score_versions import ScoreWriter
        app.state.score_versions=ScoreWriter(score_state or score_version_lab,store,production=production)
        app.state.writeback=app.state.score_versions
        reference_dir=app.state.score_versions.current_dir
        if coverage:
            from backend.global_scores import initialize, GlobalScoreWriter
            global_root=(store.directory if production else Path(score_version_lab))/'global-score-state'
            app.state.global_score_versions=(GlobalScoreWriter(global_root,store,True) if production else initialize(global_root,store,recognition_service.reference if recognition_service else ROOT))
    if recognition_service and production:
        def active_map_catalog(server):
            from backend.map_recognition import digest
            writer=app.state.score_versions if server=='cn' else getattr(app.state,'global_score_versions',None)
            if writer is None:raise HTTPException(503,'当前服别尚未绑定活动成绩')
            info,contents=writer.current()
            name='gauntlet_data.global.json' if server=='global' else 'gauntlet_data.json'
            data=json.loads(contents[name])
            return {'server':server,'version':digest((info['id']+':').encode()+contents[name]),
                    'maps':[{'big':row['大地图'],'small':row['小地图']} for row in data['tracks']]}
        recognition_service.provider=active_map_catalog
    from backend.mailing import MailConfig, MailService
    mail_service = MailService(store,origin,mail_config or MailConfig())
    app.state.mail_service = mail_service
    catalog_root=(Path(isolated_account_root)/'snapshot' if isolated else
                  recognition_service.reference if recognition_service and not production else (reference_dir() if versioned_scores else ROOT))
    catalog = json.loads((catalog_root/'cars.json').read_text(encoding='utf-8'))
    known = {c['nickname'] for c in catalog['cars'] if c.get('nickname') and c.get('zones')}

    native_account_marker=object()
    def session_hash(request):
        if request.scope.get('racepick.native.account_marker') is native_account_marker:
            return request.scope['racepick.native.anchor_hash']
        return digest(request.cookies.get(cookie_name,''))

    def session(request, required=True):
        with store.connect() as db:
            row = db.execute('SELECT * FROM sessions WHERE token_hash=? AND expires_at>?', (session_hash(request), int(time.time()))).fetchone()
        if not row and required:
            raise HTTPException(401, '会话已过期，请刷新并重新登录')
        return row

    def user(request):
        row = session(request)
        if not row['user_id']:
            raise HTTPException(401, '请先登录')
        with store.connect() as db:
            result = db.execute('SELECT id,email,verified,role FROM users WHERE id=?', (row['user_id'],)).fetchone()
            from backend.community import disabled
            if result and disabled(db,result['id']):raise HTTPException(403,'账号已停用，请联系站长')
        if not result:
            raise HTTPException(401, '账号不存在')
        from backend.roles import effective_role
        with store.connect() as db:
            return {**dict(result),'role':effective_role(db,result['id'],result['role'])}

    def require_active_session(request,db):
        from backend.community import disabled
        current=db.execute('SELECT user_id FROM sessions WHERE token_hash=? AND expires_at>?',(session_hash(request),int(time.time()))).fetchone()
        if not current or not current['user_id']:raise HTTPException(401,'登录已失效，请重新登录')
        if disabled(db,current['user_id']):raise HTTPException(403,'账号已停用')
    app.state.require_active_session=require_active_session

    def new_session(response, user_id=None, transaction=None):
        raw, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
        duration = 604800 if user_id else 3600
        def insert(db):
            db.execute('DELETE FROM sessions WHERE expires_at<=?', (int(time.time()),))
            db.execute('INSERT INTO sessions VALUES (?,?,?,?)', (digest(raw), user_id, csrf, int(time.time())+duration))
        if transaction is None:
            with store.connect() as db: insert(db)
        else: insert(transaction)
        response.set_cookie(cookie_name, raw, httponly=True, samesite='strict', secure=production, max_age=duration, path='/')
        return csrf

    def client_ip(request):
        if production:return request.state.client_ip
        return request.client.host

    @app.middleware('http')
    async def boundary(request, call_next):
        if production:
            import ipaddress
            if request.client.host not in ('127.0.0.1','::1') or request.headers.get('x-forwarded-proto')!='https':
                return JSONResponse({'detail':'仅接受可信HTTPS反向代理'},status_code=400)
            try:request.state.client_ip=str(ipaddress.ip_address(request.headers.get('x-real-ip','')))
            except ValueError:return JSONResponse({'detail':'缺少可信客户端地址'},status_code=400)
        if request.headers.get('host') != parsed.netloc:
            return JSONResponse({'detail':'无效 Host'},status_code=400)
        if request.url.path.startswith('/api/') and request.method not in ('GET','HEAD','OPTIONS'):
            recognition_upload=recognition_service is not None and request.method=='POST' and request.url.path=='/api/map-recognition/jobs'
            content_type=request.headers.get('content-type','').split(';')[0]
            type_ok=content_type in ('image/png','image/jpeg','image/webp') if recognition_upload else content_type=='application/json'
            if request.headers.get('origin') != origin or not type_ok:
                return JSONResponse({'detail':'请求来源或内容类型不正确'},status_code=403)
            collector = usage and request.method=='POST' and request.url.path in ('/api/usage/session','/api/usage/events')
            if not collector:
                try:
                    current=session(request)
                    if not secrets.compare_digest(current['csrf'],request.headers.get('x-csrf-token','')):
                        raise HTTPException(403,'CSRF 校验失败')
                except HTTPException as error:
                    return JSONResponse({'detail':error.detail},status_code=error.status_code)
            # Bound request bodies, including chunked requests.
            total=0
            async for chunk in request.stream():
                total += len(chunk)
                limit = 8*1024*1024 if recognition_upload else (8192 if collector else (3000000 if request.url.path.endswith('/images') else 65536))
                if total>limit:
                    return JSONResponse({'detail':'请求过大'},status_code=413)
                if total==len(chunk): body=chunk
                else: body+=chunk
            request._body=body if total else b''
        response=await call_next(request)
        response.headers['Cache-Control']='no-store'
        response.headers['X-Content-Type-Options']='nosniff'
        response.headers['Referrer-Policy']='no-referrer'
        response.headers['X-Frame-Options']='DENY'
        return response

    @app.get('/api/auth/me')
    def me(request:Request, response:Response):
        current=session(request,False)
        if not current:
            return {'user':None,'csrf':new_session(response),'mail_mode':'production' if mail_service.config.production else mail_service.config.mode,'account_login_only':isolated,'admin_invites':not isolated,'readonly_previews':preview_source is not None,'writeback_lab':writeback_lab is not None,'score_versions_lab':score_version_lab is not None,'score_versions':versioned_scores,'community_controls':not isolated,'contributions':contributions,'feedback':feedback,'notifications':notifications,'usage':usage,'coverage':coverage}
        return {'user':user(request) if current['user_id'] else None,'csrf':current['csrf'],'mail_mode':'production' if mail_service.config.production else mail_service.config.mode,'account_login_only':isolated,'admin_invites':not isolated,'readonly_previews':preview_source is not None,'writeback_lab':writeback_lab is not None,'score_versions_lab':score_version_lab is not None,'score_versions':versioned_scores,'community_controls':not isolated,'contributions':contributions,'feedback':feedback,'notifications':notifications,'usage':usage,'coverage':coverage}

    @app.post('/api/auth/register')
    def register(data:Registration, request:Request):
        mail_service.check_recipient(data.email)
        store.throttle('register:'+client_ip(request),20)
        prepared = None
        hashed=HASHER.hash(data.password)
        with store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            exists=db.execute('SELECT id FROM users WHERE email=?',(data.email,)).fetchone()
            if exists and data.invite_code.strip():
                raise HTTPException(409,'该邮箱已有账号，请先验证邮箱并登录，再兑换管理员邀请码；忘记密码可先重置')
            if not exists:
                uid=secrets.token_hex(16)
                db.execute('INSERT INTO users(id,email,password_hash,created_at) VALUES (?,?,?,?)',(uid,data.email,hashed,int(time.time())))
                if data.invite_code.strip():
                    from backend.roles import reserve
                    reserve(db,data.invite_code,data.email,uid)
                prepared = mail_service.prepare(db,uid,data.email,'verify')
        mail_service.deliver(prepared)
        return {'message':mail_service.notice('register')}

    @app.post('/api/auth/login')
    def login(data:Credentials, request:Request, response:Response):
        store.throttle('login-ip:'+client_ip(request),40)
        store.throttle('login-email:'+digest(data.email),10)
        with store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row=db.execute('SELECT * FROM users WHERE email=?',(data.email,)).fetchone()
            try:
                HASHER.verify(row['password_hash'] if row else DUMMY,data.password)
            except (VerificationError,InvalidHashError):
                raise HTTPException(401,'邮箱或密码不正确')
            if not row: raise HTTPException(401,'邮箱或密码不正确')
            from backend.community import disabled
            if disabled(db,row['id']):raise HTTPException(403,'账号已停用，请联系站长')
            if not row['verified']: raise HTTPException(403,'请先完成邮箱验证，再登录')
            db.execute('INSERT INTO account_login_stats VALUES(?,?) ON CONFLICT(user_id) DO UPDATE SET last_login=excluded.last_login',(row['id'],int(time.time())))
            if HASHER.check_needs_rehash(row['password_hash']):
                db.execute('UPDATE users SET password_hash=? WHERE id=?',(HASHER.hash(data.password),row['id']))
            db.execute('DELETE FROM sessions WHERE token_hash=?',(session_hash(request),))
            csrf=new_session(response,row['id'],db)
            from backend.roles import effective_role
            login_role=effective_role(db,row['id'],row['role'])
        return {'csrf':csrf,'user':{'id':row['id'],'email':row['email'],'role':login_role,'verified':True}}

    @app.post('/api/auth/logout')
    def logout(request:Request,response:Response):
        with store.connect() as db:
            db.execute('DELETE FROM sessions WHERE token_hash=?',(session_hash(request),))
        response.delete_cookie(cookie_name,path='/',secure=production,httponly=True,samesite='strict')
        return {'message':'已退出'}

    @app.post('/api/auth/resend-verification')
    def resend(data:EmailInput,request:Request):
        mail_service.check_recipient(data.email)
        store.throttle('resend:'+client_ip(request),10)
        prepared = None
        with store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row=db.execute('SELECT id FROM users WHERE email=? AND verified=0',(data.email.strip().lower(),)).fetchone()
            from backend.community import disabled
            if row and not disabled(db,row['id']): prepared = mail_service.prepare(db,row['id'],data.email.strip().lower(),'verify')
        mail_service.deliver(prepared)
        return {'message':mail_service.notice('resend')}

    @app.post('/api/auth/forgot-password')
    def forgot(data:EmailInput,request:Request):
        mail_service.check_recipient(data.email)
        store.throttle('forgot:'+client_ip(request),10)
        prepared = None
        with store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row=db.execute('SELECT id FROM users WHERE email=?',(data.email.strip().lower(),)).fetchone()
            from backend.community import disabled
            if row and not disabled(db,row['id']): prepared = mail_service.prepare(db,row['id'],data.email.strip().lower(),'reset')
        mail_service.deliver(prepared)
        return {'message':mail_service.notice('reset')}

    def consume(token,purpose,password=None):
        with store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row=db.execute('SELECT user_id FROM auth_tokens WHERE token_hash=? AND purpose=? AND expires_at>?',(digest(token),purpose,int(time.time()))).fetchone()
            if not row: raise HTTPException(400,'链接无效、已使用或已过期')
            from backend.community import disabled
            if disabled(db,row['user_id']):raise HTTPException(403,'账号已停用')
            if purpose=='verify':
                db.execute('UPDATE users SET verified=1 WHERE id=?',(row['user_id'],))
                db.execute('DELETE FROM auth_tokens WHERE token_hash=?',(digest(token),))
            else:
                db.execute('UPDATE users SET password_hash=?,verified=1 WHERE id=?',(HASHER.hash(password),row['user_id']))
                db.execute('DELETE FROM sessions WHERE user_id=?',(row['user_id'],))
                db.execute('DELETE FROM auth_tokens WHERE user_id=?',(row['user_id'],))
            from backend.roles import complete_pending_invitation
            invite_message=complete_pending_invitation(db,row['user_id'])
        return {'message':('邮箱已验证，请登录' if purpose=='verify' else '密码已重置，原会话已退出，请重新登录')+invite_message}

    @app.post('/api/auth/verify-email')
    def verify(data:TokenInput,request:Request):
        store.throttle('verify:'+client_ip(request),30)
        return consume(data.token,'verify')

    @app.post('/api/auth/reset-password')
    def reset(data:ResetInput,request:Request):
        store.throttle('reset:'+client_ip(request),20)
        return consume(data.token,'reset',data.password)

    @app.get('/api/me/profile')
    def get_profile(request:Request,server:str='cn'):
        owner=user(request)
        if request.headers.get('x-account-id') != owner['id']:
            raise HTTPException(401,'账号已在其他窗口切换，请刷新后重新确认身份')
        if server not in ('cn','global'):raise HTTPException(422,'服别无效')
        if server=='global':
            from backend.global_profiles import get
            return get(store,owner['id'])
        with store.connect() as db:
            row=db.execute('SELECT * FROM profiles WHERE user_id=?',(owner['id'],)).fetchone()
        if not row: return {'revision':0,'profile':None}
        return {'revision':row['revision'],'profile':{'cars':json.loads(row['cars']),'stars':json.loads(row['stars'])}}

    @app.put('/api/me/profile')
    def put_profile(data:ProfileInput|GlobalProfileInput,request:Request,server:str='cn'):
        owner=user(request)
        if request.headers.get('x-profile-save')!='explicit':raise HTTPException(409,'车库已改为手动保存，请刷新页面后点击保存车库')
        if request.headers.get('x-account-id') != owner['id']:
            raise HTTPException(401,'账号已在其他窗口切换，请刷新后重新确认身份')
        if server not in ('cn','global'):raise HTTPException(422,'服别无效')
        if server=='global':
            from backend.global_profiles import put
            if frozen is not None:
                _,raw=frozen.global_score_versions.current();catalog=json.loads(raw['cars.global.json']);scores=json.loads(raw['gauntlet_data.global.json'])
            elif hasattr(app.state,'global_score_versions'):
                _,raw=app.state.global_score_versions.current();catalog=json.loads(raw['cars.global.json']);scores=json.loads(raw['gauntlet_data.global.json'])
            else:
                catalog=json.loads((ROOT/'cars.global.json').read_bytes());scores=json.loads((ROOT/'gauntlet_data.global.json').read_bytes())
            names={c['nickname'] for c in catalog['cars'] if c.get('nickname') and c.get('zones')}
            oc_names={e['cars'][0]['name'] for t in scores['tracks'] for e in t.get('五区',{}).get('理论',[]) if e.get('cars') and e['cars'][0].get('oc') is True}
            return put(store,owner['id'],GlobalProfileInput.model_validate(data.model_dump()),lambda db:require_active_session(request,db),names,oc_names)
        if isinstance(data,GlobalProfileInput):raise HTTPException(422,'国服车库不接收国际OC字段或缺失星级字段')
        if len(set(data.cars))!=len(data.cars) or any(c not in known for c in data.cars) or any(c not in known or s<1 or s>6 for c,s in data.stars.items()):
            raise HTTPException(422,'车辆或星级无效；星级保存原始1–6值，分区显示仍沿用现有规则')
        with store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            require_active_session(request,db)
            row=db.execute('SELECT revision FROM profiles WHERE user_id=?',(owner['id'],)).fetchone()
            revision=row['revision'] if row else 0
            if data.revision!=revision: raise HTTPException(409,'账号资料已在其他窗口更新，请重新加载或明确覆盖')
            revision+=1
            db.execute('INSERT INTO profiles VALUES (?,?,?,?,?) ON CONFLICT(user_id) DO UPDATE SET cars=excluded.cars,stars=excluded.stars,revision=excluded.revision,updated_at=excluded.updated_at',
                (owner['id'],json.dumps(data.cars,ensure_ascii=False),json.dumps(data.stars,ensure_ascii=False),revision,int(time.time())))
        return {'revision':revision}

    if coverage:
        from backend.coverage import install as install_coverage
        install_coverage(app,store,ROOT,user)
    if contributions:
        from backend.contributions import install as install_contributions
        install_contributions(app,store,ROOT,user)
    from backend.submissions import install
    install(app,store,ROOT,user,reference_dir,production=production)
    if usage:
        from backend.usage import install as install_usage
        install_usage(app, store, ROOT, user, session)
    if notifications:
        from backend.notifications import install as install_notifications
        install_notifications(app, store, user)
    if feedback:
        from backend.feedback import install as install_feedback
        install_feedback(app,store,ROOT,user)
    from backend.community import install as install_community
    install_community(app,store,ROOT,user)
    from backend.roles import install as install_roles
    install_roles(app,store,ROOT,user,production=production)
    from backend.previews import install as install_previews
    if not production:install_previews(app,store,ROOT,user,preview_source)

    if recognition_service:
        from backend.map_recognition import install as install_recognition
        install_recognition(app,recognition_service,session,user)
        app.state.map_recognition=recognition_service

    @app.get('/api/health')
    def health():
        with store.connect() as db:db.execute('SELECT 1').fetchone()
        result={'status':'ok','mode':'production' if production else 'local','schema':6}
        if mini_config and mini_config.get('formal_account'):
            result['mini_account']={'mode':'formal-a','enabled':True,
                                    'cloud_writes':mini_config['formal_profile_writes']}
        if isolated:result.update(mode='isolated-account-test',production_business=False)
        if recognition_service:result['map_recognition']={'enabled':True,'worker':recognition_service.health()}
        result['community_schema']=1
        result['contribution_schema']=1 if contributions else 0
        result['contributions']=contributions
        result['feedback']=feedback
        result['feedback_schema']=1 if feedback else 0
        result['notification_schema']=1 if notifications else 0
        result['notifications']=notifications
        result['usage_schema']=1 if usage else 0
        result['coverage_schema']=2 if coverage else 0
        result['global_profile_schema']=1 if global_profiles_ready else 0
        result['global_score_schema']=1 if hasattr(app.state,'global_score_versions') else 0
        if hasattr(app.state,'global_score_versions'):result['global_score_version']=app.state.global_score_versions.current()[0]['id']
        result['usage']=usage
        if versioned_scores:
            result['score_version']=app.state.score_versions.current()[0]['id']
            with store.connect() as db:result['score_writes']=app.state.score_versions.enabled(db)
        return result

    @app.api_route('/',methods=['GET','HEAD'])
    def index(request:Request):
        html=(ROOT/'index.html').read_text(encoding='utf-8')
        html=html.replace('</head>','<script src="/notifications.js"></script><script src="/profile_store.js"></script><script src="/announcements.js"></script><script src="/auth.js"></script><link rel="stylesheet" href="/accounts.css"><link rel="stylesheet" href="/ui.css">\n</head>')
        if recognition_service:
            html=html.replace('</head>','<script>globalThis.RACEPICK_MAP_RECOGNITION={enabled:true};</script><script defer src="/map_recognition.js"></script><link rel="stylesheet" href="/map_recognition.css"></head>')
            marker='<div class="map-rows" id="mapRowsContainer"></div>'
            html=html.replace(marker,'<section id="mapRecognitionHost" class="map-recognition-host"></section>'+marker,1)
        if coverage:
            global_server=request.query_params.get('server')=='global'
            table_href='/score-table?server=global' if global_server else '/score-table'
            table_description='查看各图参考成绩，补充缺失记录'
            marker='<div class="sub">帕累托最优 · 擂台选车</div>'
            entry=('<section class="coverage-entry" id="coverageEntry" aria-labelledby="coverageEntryTitle">'
                   '<div class="coverage-entry-copy"><h2 id="coverageEntryTitle">擂台成绩表 '
                   '<span class="coverage-entry-new" id="coverageEntryNew">新功能</span></h2>'
                   '<p>'+table_description+'</p></div>'
                   '<a class="ui-button coverage-entry-link" id="coverageEntryLink" href="'+table_href+'">'
                   '查看成绩表 <span aria-hidden="true">→</span></a></section>')
            html=html.replace(marker,marker+entry,1)
        if hasattr(app.state,'global_score_versions'):html=html.replace('</head>','<script>globalThis.RACEPICK_VERSIONED_GLOBAL_SCORES=true;</script></head>')
        if global_profiles_ready:html=html.replace('</head>','<script>globalThis.RACEPICK_GLOBAL_PROFILE_CLOUD=true;</script></head>')
        if versioned_scores:html=html.replace('</head>','<script>globalThis.RACEPICK_VERSIONED_SCORES=true;</script></head>')
        return HTMLResponse(usage_html(html))

    if versioned_scores:
        from backend.score_versions import install as install_score_versions
        install_score_versions(app,app.state.score_versions,ROOT,user,session)
    if writeback_lab is not None:
        from backend.writeback import install as install_writeback
        install_writeback(app,store,ROOT,user,writeback_lab,preview_source)
    assets={'styles.css','config.js','api.js','app_state.js','allocator.js','race_scores.js','selection_core.js','home_presenter.js','home_theme.json','cars.json','gauntlet_data.json','auth.js','profile_store.js','accounts.css','submissions.js','submissions.css','admin_access.js','data_previews.js','data_previews.css','writeback_lab.js','announcements.js','admin_accounts.js'}
    assets.update({'ui.css','theme.css','notifications.js'})
    if recognition_service:assets.update({'map_recognition.js','map_recognition.css'})
    assets.update({'cars.global.json','gauntlet_data.global.json','global-data-manifest.json'})
    if coverage: assets.update({'coverage.js','coverage.css'})
    if usage: assets.update({'usage.js','usage_admin.js','usage.css'})
    if feedback: assets.add('feedback.js')
    if contributions: assets.update({'leaderboard.js','leaderboard.css'})
    if versioned_scores:assets.add('score_versions.js')
    @app.api_route('/{name}',methods=['GET','HEAD'])
    def asset(name:str):
        if production and name in ('data_previews.js','data_previews.css','writeback_lab.js'):raise HTTPException(404)
        if name not in assets: raise HTTPException(404)
        if isolated and name in ('cars.json','gauntlet_data.json','cars.global.json','gauntlet_data.global.json','global-data-manifest.json'):
            return FileResponse(Path(isolated_account_root)/'snapshot'/name,headers={'Cache-Control':'no-store'})
        if recognition_service and not production and name in ('cars.json','gauntlet_data.json','cars.global.json','gauntlet_data.global.json','global-data-manifest.json'):
            return FileResponse(recognition_service.reference/name,headers={'Cache-Control':'no-store'})
        if hasattr(app.state,'global_score_versions') and name in ('cars.global.json','gauntlet_data.global.json','global-data-manifest.json'):
            info,contents=app.state.global_score_versions.current()
            return Response(contents[name],media_type='application/json',headers={'X-Global-Score-Version':info['id'],'Cache-Control':'no-store'})
        if versioned_scores and name in ('gauntlet_data.json','cars.json'):
            info,contents=app.state.score_versions.current()
            return Response(contents[name],media_type='application/json',headers={'X-Score-Version':info['id']})
        if writeback_lab is not None and name in ('gauntlet_data.json','cars.json'):
            return FileResponse(Path(preview_source)/name,headers={'Cache-Control':'no-store'})
        return FileResponse(ROOT/name)
    def native_request(request, anchor_hash=None, actor_id=None, explicit_save=False):
        # Only server-owned code can install this per-app object identity. HTTP headers cannot.
        scope=dict(request.scope)
        scope['headers']=([(b'x-account-id',actor_id.encode())] if actor_id else [])+([(b'x-profile-save',b'explicit')] if explicit_save else [])
        scope['state']={'client_ip':request.scope['mini_ip']}
        scope['racepick.native.account_marker']=native_account_marker
        scope['racepick.native.anchor_hash']=anchor_hash or digest('')
        return Request(scope)
    def native_anchor(response):
        from http.cookies import SimpleCookie
        cookie=SimpleCookie();cookie.load(response.headers.get('set-cookie',''))
        if cookie_name not in cookie:raise RuntimeError('Native login did not create a revocation anchor')
        hashed=digest(cookie[cookie_name].value)
        with store.connect() as db:
            row=db.execute('SELECT user_id,expires_at FROM sessions WHERE token_hash=?',(hashed,)).fetchone()
        if row is None:raise RuntimeError('Native login anchor missing')
        return hashed,row['user_id'],row['expires_at']
    def native_revoke(anchor_hash):
        with store.connect() as db:db.execute('DELETE FROM sessions WHERE token_hash=?',(anchor_hash,))
    from types import SimpleNamespace
    from backend.roles import Redeem
    redeem=next(route.endpoint for route in app.routes if getattr(route,'path',None)=='/api/auth/redeem-invitation')
    app.state.native_accounts=SimpleNamespace(request=native_request,anchor=native_anchor,revoke=native_revoke,user=user,
        handlers={'register':register,'login':login,'logout':logout,'resend-verification':resend,'forgot-password':forgot,
                  'verify-email':verify,'reset-password':reset,'redeem-invitation':redeem,'get-profile':get_profile,'put-profile':put_profile,
                  'get-global-profile':lambda request:get_profile(request,'global'),'put-global-profile':lambda data,request:put_profile(data,request,'global')},
        models={'register':Registration,'login':Credentials,'resend-verification':EmailInput,'forgot-password':EmailInput,
                'verify-email':TokenInput,'reset-password':ResetInput,'redeem-invitation':Redeem,'put-profile':ProfileInput,'put-global-profile':GlobalProfileInput})
    app.state.native_feature_routes={(method,route.path):route for route in app.routes if hasattr(route,"endpoint") for method in (getattr(route,"methods",None) or [])}
    from backend.mini_api import MiniGateway
    if mini_config is not None and recognition_service is not None:
        mini_root=mini_config['store'].root
        if mini_root.is_relative_to(recognition_service.root) or recognition_service.root.is_relative_to(mini_root):
            raise ValueError('原生会话与OCR队列必须使用互不包含的独立目录')
    app.add_middleware(MiniGateway,config=mini_config,source=app.state,service=recognition_service,origin=origin,production=production)

    return app


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port',type=int,default=8000)
    parser.add_argument('--data-dir',type=Path,default=ROOT/'.local-accounts')
    parser.add_argument('--preview-source',type=Path,help='正式成绩库只读预览来源；需显式指定，不接收网页路径参数')
    parser.add_argument('--writeback-lab',type=Path,help='仅允许专门创建的隔离写回测试环境')
    parser.add_argument('--usage',action='store_true',help='独立本地环境启用使用统计')
    parser.add_argument('--coverage',action='store_true',help='仅新建隔离库启用成绩覆盖表与解锁')
    parser.add_argument('--notifications',action='store_true',help='仅独立本地环境启用按账号未读提醒')
    parser.add_argument('--feedback',action='store_true',help='独立本地环境启用文字反馈')
    parser.add_argument('--contributions',action='store_true',help='仅独立本地成绩版本环境启用排行榜')
    parser.add_argument('--score-version-lab',type=Path,help='独立数据版本测试环境，不用于生产')
    parser.add_argument('--mail-mode',choices=['file','smtp'],default='file')
    parser.add_argument('--mail-to',help='SMTP本地测试唯一允许的收件邮箱')
    args=parser.parse_args()
    from backend.mailing import MailConfig, read_password
    try:
        if args.mail_mode=='smtp':
            if not args.mail_to: parser.error('SMTP模式必须提供 --mail-to')
            print('真实邮件测试：仅发送至 '+args.mail_to+'；密码仅保存在当前进程内存，不写文件。')
            config=MailConfig('smtp',args.mail_to,read_password())
        else:
            if args.mail_to: parser.error('--mail-to仅用于smtp模式')
            config=MailConfig()
    except (ValueError,KeyboardInterrupt) as error:
        parser.exit(1, ('已取消' if isinstance(error,KeyboardInterrupt) else str(error))+'\n')
    import uvicorn
    uvicorn.run(create_app(args.data_dir,f'http://127.0.0.1:{args.port}',mail_config=config,preview_source=args.preview_source,writeback_lab=args.writeback_lab,score_version_lab=args.score_version_lab,contributions=args.contributions,feedback=args.feedback,notifications=args.notifications,usage=args.usage,coverage=args.coverage),host='127.0.0.1',port=args.port,proxy_headers=False)

if __name__=='__main__': main()
