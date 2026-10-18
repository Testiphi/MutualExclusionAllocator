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


class EmailInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    email: str = Field(max_length=254)


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
    def __init__(self, directory):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.path = self.directory / 'accounts.sqlite3'
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
            if db.execute('SELECT max(version) FROM schema_version').fetchone()[0] != 1:
                raise RuntimeError('不支持的数据库版本')

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=10)
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


def create_app(data_dir=None, origin='http://127.0.0.1:8000'):
    parsed = urlsplit(origin)
    if parsed.scheme != 'http' or parsed.hostname not in ('127.0.0.1', 'localhost') or parsed.path or parsed.query or parsed.fragment or parsed.username:
        raise ValueError('本地开发仅允许 localhost/127.0.0.1 HTTP origin')
    store = Store(data_dir or ROOT / '.local-accounts')
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
    app.state.store = store
    catalog = json.loads((ROOT/'cars.json').read_text(encoding='utf-8'))
    known = {c['nickname'] for c in catalog['cars'] if c.get('nickname') and c.get('zones')}

    def session(request, required=True):
        token = request.cookies.get(COOKIE, '')
        with store.connect() as db:
            row = db.execute('SELECT * FROM sessions WHERE token_hash=? AND expires_at>?', (digest(token), int(time.time()))).fetchone()
        if not row and required:
            raise HTTPException(401, '会话已过期，请刷新并重新登录')
        return row

    def user(request):
        row = session(request)
        if not row['user_id']:
            raise HTTPException(401, '请先登录')
        with store.connect() as db:
            result = db.execute('SELECT id,email,verified,role FROM users WHERE id=?', (row['user_id'],)).fetchone()
        if not result:
            raise HTTPException(401, '账号不存在')
        return dict(result)

    def new_session(response, user_id=None, transaction=None):
        raw, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
        duration = 604800 if user_id else 3600
        def insert(db):
            db.execute('DELETE FROM sessions WHERE expires_at<=?', (int(time.time()),))
            db.execute('INSERT INTO sessions VALUES (?,?,?,?)', (digest(raw), user_id, csrf, int(time.time())+duration))
        if transaction is None:
            with store.connect() as db: insert(db)
        else: insert(transaction)
        response.set_cookie(COOKIE, raw, httponly=True, samesite='strict', secure=False, max_age=duration, path='/')
        return csrf

    def mail(db, uid, email, purpose):
        raw = secrets.token_urlsafe(32)
        db.execute('DELETE FROM auth_tokens WHERE user_id=? AND purpose=?', (uid,purpose))
        db.execute('INSERT INTO auth_tokens VALUES (?,?,?,?)', (digest(raw),uid,purpose,int(time.time())+1800))
        outbox=store.directory/'outbox'
        outbox.mkdir(exist_ok=True)
        # Explicit local-only file transport; never available over HTTP.
        payload={'to':email,'purpose':purpose,'url':f'{origin}/#action={purpose}&token={raw}', 'expires_in_seconds':1800}
        (outbox/f'{time.time_ns()}-{secrets.token_hex(4)}.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8')

    @app.middleware('http')
    async def boundary(request, call_next):
        if request.headers.get('host') != parsed.netloc:
            return JSONResponse({'detail':'无效 Host'},status_code=400)
        if request.url.path.startswith('/api/') and request.method not in ('GET','HEAD','OPTIONS'):
            if request.headers.get('origin') != origin or request.headers.get('content-type','').split(';')[0] != 'application/json':
                return JSONResponse({'detail':'请求来源或内容类型不正确'},status_code=403)
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
                if total>65536:
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
            return {'user':None,'csrf':new_session(response)}
        return {'user':user(request) if current['user_id'] else None,'csrf':current['csrf']}

    @app.post('/api/auth/register')
    def register(data:Credentials, request:Request):
        store.throttle('register:'+request.client.host,20)
        hashed=HASHER.hash(data.password)
        with store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            exists=db.execute('SELECT id FROM users WHERE email=?',(data.email,)).fetchone()
            if not exists:
                uid=secrets.token_hex(16)
                db.execute('INSERT INTO users(id,email,password_hash,created_at) VALUES (?,?,?,?)',(uid,data.email,hashed,int(time.time())))
                mail(db,uid,data.email,'verify')
        return {'message':'如可注册，验证邮件已写入本地测试收件箱；已有账号请登录或重置密码。'}

    @app.post('/api/auth/login')
    def login(data:Credentials, request:Request, response:Response):
        store.throttle('login-ip:'+request.client.host,40)
        store.throttle('login-email:'+digest(data.email),10)
        with store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row=db.execute('SELECT * FROM users WHERE email=?',(data.email,)).fetchone()
            try:
                HASHER.verify(row['password_hash'] if row else DUMMY,data.password)
            except (VerificationError,InvalidHashError):
                raise HTTPException(401,'邮箱或密码不正确')
            if not row: raise HTTPException(401,'邮箱或密码不正确')
            if not row['verified']: raise HTTPException(403,'请先通过本地测试邮件验证邮箱')
            if HASHER.check_needs_rehash(row['password_hash']):
                db.execute('UPDATE users SET password_hash=? WHERE id=?',(HASHER.hash(data.password),row['id']))
            db.execute('DELETE FROM sessions WHERE token_hash=?',(digest(request.cookies.get(COOKIE,'')),))
            csrf=new_session(response,row['id'],db)
        return {'csrf':csrf,'user':{'id':row['id'],'email':row['email'],'role':row['role'],'verified':True}}

    @app.post('/api/auth/logout')
    def logout(request:Request,response:Response):
        with store.connect() as db:
            db.execute('DELETE FROM sessions WHERE token_hash=?',(digest(request.cookies.get(COOKIE,'')),))
        response.delete_cookie(COOKIE,path='/')
        return {'message':'已退出'}

    @app.post('/api/auth/resend-verification')
    def resend(data:EmailInput,request:Request):
        store.throttle('resend:'+request.client.host,10)
        with store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row=db.execute('SELECT id FROM users WHERE email=? AND verified=0',(data.email.strip().lower(),)).fetchone()
            if row: mail(db,row['id'],data.email.strip().lower(),'verify')
        return {'message':'如果账号尚未验证，新验证邮件已写入本地测试收件箱。'}

    @app.post('/api/auth/forgot-password')
    def forgot(data:EmailInput,request:Request):
        store.throttle('forgot:'+request.client.host,10)
        with store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row=db.execute('SELECT id FROM users WHERE email=?',(data.email.strip().lower(),)).fetchone()
            if row: mail(db,row['id'],data.email.strip().lower(),'reset')
        return {'message':'如果账号存在，重置邮件已写入本地测试收件箱。'}

    def consume(token,purpose,password=None):
        with store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row=db.execute('SELECT user_id FROM auth_tokens WHERE token_hash=? AND purpose=? AND expires_at>?',(digest(token),purpose,int(time.time()))).fetchone()
            if not row: raise HTTPException(400,'链接无效、已使用或已过期')
            if purpose=='verify':
                db.execute('UPDATE users SET verified=1 WHERE id=?',(row['user_id'],))
                db.execute('DELETE FROM auth_tokens WHERE token_hash=?',(digest(token),))
            else:
                db.execute('UPDATE users SET password_hash=?,verified=1 WHERE id=?',(HASHER.hash(password),row['user_id']))
                db.execute('DELETE FROM sessions WHERE user_id=?',(row['user_id'],))
                db.execute('DELETE FROM auth_tokens WHERE user_id=?',(row['user_id'],))
        return {'message':'邮箱已验证，请登录' if purpose=='verify' else '密码已重置，原会话已退出，请重新登录'}

    @app.post('/api/auth/verify-email')
    def verify(data:TokenInput,request:Request):
        store.throttle('verify:'+request.client.host,30)
        return consume(data.token,'verify')

    @app.post('/api/auth/reset-password')
    def reset(data:ResetInput,request:Request):
        store.throttle('reset:'+request.client.host,20)
        return consume(data.token,'reset',data.password)

    @app.get('/api/me/profile')
    def get_profile(request:Request):
        owner=user(request)
        if request.headers.get('x-account-id') != owner['id']:
            raise HTTPException(401,'账号已在其他窗口切换，请刷新后重新确认身份')
        with store.connect() as db:
            row=db.execute('SELECT * FROM profiles WHERE user_id=?',(owner['id'],)).fetchone()
        if not row: return {'revision':0,'profile':None}
        return {'revision':row['revision'],'profile':{'cars':json.loads(row['cars']),'stars':json.loads(row['stars'])}}

    @app.put('/api/me/profile')
    def put_profile(data:ProfileInput,request:Request):
        owner=user(request)
        if request.headers.get('x-account-id') != owner['id']:
            raise HTTPException(401,'账号已在其他窗口切换，请刷新后重新确认身份')
        if len(set(data.cars))!=len(data.cars) or any(c not in known for c in data.cars) or any(c not in known or s<1 or s>6 for c,s in data.stars.items()):
            raise HTTPException(422,'车辆或星级无效；星级保存原始1–6值，分区显示仍沿用现有规则')
        with store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row=db.execute('SELECT revision FROM profiles WHERE user_id=?',(owner['id'],)).fetchone()
            revision=row['revision'] if row else 0
            if data.revision!=revision: raise HTTPException(409,'账号资料已在其他窗口更新，请重新加载或明确覆盖')
            revision+=1
            db.execute('INSERT INTO profiles VALUES (?,?,?,?,?) ON CONFLICT(user_id) DO UPDATE SET cars=excluded.cars,stars=excluded.stars,revision=excluded.revision,updated_at=excluded.updated_at',
                (owner['id'],json.dumps(data.cars,ensure_ascii=False),json.dumps(data.stars,ensure_ascii=False),revision,int(time.time())))
        return {'revision':revision}

    @app.get('/')
    def index():
        html=(ROOT/'index.html').read_text(encoding='utf-8')
        html=html.replace('</head>','<script src="/profile_store.js"></script><script src="/auth.js"></script><link rel="stylesheet" href="/accounts.css">\n</head>')
        return HTMLResponse(html)

    assets={'styles.css','config.js','api.js','app_state.js','allocator.js','race_scores.js','cars.json','gauntlet_data.json','auth.js','profile_store.js','accounts.css'}
    @app.get('/{name}')
    def asset(name:str):
        if name not in assets: raise HTTPException(404)
        return FileResponse(ROOT/name)
    return app


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port',type=int,default=8000)
    parser.add_argument('--data-dir',type=Path,default=ROOT/'.local-accounts')
    args=parser.parse_args()
    import uvicorn
    uvicorn.run(create_app(args.data_dir,f'http://127.0.0.1:{args.port}'),host='127.0.0.1',port=args.port,proxy_headers=False)

if __name__=='__main__': main()
