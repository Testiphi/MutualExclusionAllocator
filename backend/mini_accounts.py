"""Batch A native account sessions. Reuses website handlers through a private server context."""
from contextlib import contextmanager
from pathlib import Path
import hashlib
import hmac
import json
import os
import re
import secrets
import sqlite3
import stat
import time

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import Response, JSONResponse
from pydantic import ValidationError
from starlette.concurrency import run_in_threadpool
from starlette.exceptions import HTTPException as StarletteHTTPException
from backend.mini_auth import MiniError, fail, request_key
from backend.mini_api import limited_body, error_response

PREFIX = '/api/mini/account/v1'
KIND = 'racepick-native-accounts-v1'


def account_error(error, credentials=False):
    detail=str(error.detail)
    code={400:'ACCOUNT_INPUT_REJECTED',401:'CREDENTIALS_REJECTED' if credentials else 'ACCOUNT_SESSION_REVOKED',
          403:'ACCOUNT_DISABLED' if '停用' in detail else 'EMAIL_NOT_VERIFIED' if '验证' in detail else 'ACCOUNT_FORBIDDEN',
          409:'ACCOUNT_CONFLICT',422:'ACCOUNT_INPUT_REJECTED',429:'ACCOUNT_RATE_LIMITED',503:'ACCOUNT_DELIVERY_OR_SERVICE_UNCERTAIN'}.get(error.status_code,'ACCOUNT_REJECTED')
    return MiniError(error.status_code,code,detail,60 if error.status_code==429 else None)


def provision(root):
    root = Path(root).absolute()
    if root.resolve() != root or root.is_relative_to(Path(__file__).resolve().parents[1]) or root.exists():
        raise ValueError('账号原生状态只允许显式新建发布目录之外的独立目录')
    root.mkdir(mode=0o700)
    (root/'state.json').write_text(json.dumps({'kind':KIND,'schema':1}),encoding='utf-8')
    (root/'token.key').write_bytes(secrets.token_bytes(32))
    for name in ('state.json','token.key'): (root/name).chmod(0o600)
    store = AccountStore(root, initialize=True)
    store.path.chmod(0o600)
    return root


class AccountStore:
    def __init__(self, root, initialize=False):
        self.root=Path(root).absolute()
        if self.root.resolve()!=self.root or self.root.is_relative_to(Path(__file__).resolve().parents[1]):
            raise ValueError('原生账号状态路径不正确')
        if json.loads((self.root/'state.json').read_text('utf-8'))!={'kind':KIND,'schema':1}:
            raise ValueError('原生账号状态标记不正确')
        for p in [self.root,*self.root.iterdir()]:
            if p.is_symlink() or p.resolve()!=p or (p.is_file() and p.stat().st_nlink!=1): raise ValueError('原生账号状态禁止链接')
            if os.name=='posix' and (stat.S_IMODE(p.stat().st_mode)&0o077 or p.stat().st_uid!=os.geteuid()):
                raise ValueError('原生账号状态必须为运行用户私有')
        if any((self.root/n).exists() for n in ('accounts.sqlite3','guests.sqlite3','production.json','recognition.sqlite3')):
            raise ValueError('不能混用网页、访客或OCR数据库')
        self.key=(self.root/'token.key').read_bytes()
        if len(self.key)!=32: raise ValueError('账号签名密钥不正确')
        self.path=self.root/'native-accounts.sqlite3'
        if initialize:
            with self.connect() as db:
                db.executescript('''
                CREATE TABLE meta(version INTEGER NOT NULL); INSERT INTO meta VALUES(1);
                CREATE TABLE sessions(sid TEXT PRIMARY KEY,guest_sid TEXT NOT NULL,anchor TEXT NOT NULL,
                    user_id TEXT NOT NULL,role TEXT NOT NULL,expires INTEGER NOT NULL,revoked INTEGER NOT NULL DEFAULT 0,authenticated_at INTEGER NOT NULL);
                CREATE TABLE operations(scope TEXT NOT NULL,request_key TEXT NOT NULL,action TEXT NOT NULL,fingerprint TEXT NOT NULL,
                    state TEXT NOT NULL,status INTEGER,result TEXT,created INTEGER NOT NULL,PRIMARY KEY(scope,request_key));
                CREATE TABLE events(id INTEGER PRIMARY KEY,action TEXT NOT NULL,actor_id TEXT,at INTEGER NOT NULL);
                ''')
        else:
            if not self.path.is_file(): raise ValueError('账号原生状态未显式初始化')
            with self.connect() as db:
                if [r[0] for r in db.execute('SELECT version FROM meta')]!=[1]:raise ValueError('账号原生schema不兼容；不自动迁移')

    @contextmanager
    def connect(self):
        db=sqlite3.connect(self.path,timeout=10);db.row_factory=sqlite3.Row
        db.execute('PRAGMA max_page_count=8192');db.execute('PRAGMA journal_size_limit=1048576')
        try:
            with db: yield db
        finally: db.close()

    def digest(self, text): return hmac.new(self.key,text.encode(),hashlib.sha256).hexdigest()
    def token(self, sid): return 'rpa1.'+sid+'.'+self.digest('account:'+sid)

    def authenticate(self, value, guests):
        if not isinstance(value,str) or not re.fullmatch(r'Bearer rpa1\.[a-f0-9]{48}\.[a-f0-9]{64}',value):
            fail(401,'ACCOUNT_SESSION_REQUIRED','需要RacePick账号会话；微信访客不能代替账号登录')
        token=value[7:];sid=token.split('.')[1]
        if not hmac.compare_digest(token,self.token(sid)):fail(401,'ACCOUNT_SESSION_INVALID','账号会话无效')
        with self.connect() as db:row=db.execute('SELECT * FROM sessions WHERE sid=?',(sid,)).fetchone()
        if row is None or row['revoked'] or row['expires']<=time.time():fail(401,'ACCOUNT_SESSION_EXPIRED','账号会话失效，请保留草稿并重新登录')
        guests.authenticate('Bearer '+guests.token(row['guest_sid']))
        return dict(row)

    def issue(self, guest, anchor, actor, expires, source):
        now=int(time.time());sid=secrets.token_hex(24)
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            previous=db.execute('SELECT anchor FROM sessions WHERE guest_sid=? AND revoked=0',(guest['sid'],)).fetchall()
            if db.execute('SELECT count(*) FROM sessions WHERE expires>? AND revoked=0 AND guest_sid<>?',(now,guest['sid'])).fetchone()[0]>=10000:
                fail(503,'ACCOUNT_CAPACITY','账号会话暂不可用',30)
            for row in previous:source.revoke(row['anchor'])
            db.execute('UPDATE sessions SET revoked=1 WHERE guest_sid=?',(guest['sid'],))
            db.execute('INSERT INTO sessions VALUES(?,?,?,?,?,?,0,?)',(sid,guest['sid'],anchor,actor['id'],actor['role'],min(expires,now+3600),now))
            db.execute('INSERT INTO events(action,actor_id,at) VALUES(?,?,?)',('login',actor['id'],now))
            db.execute('DELETE FROM sessions WHERE expires<?',(now-86400,))
            db.execute('DELETE FROM events WHERE at<?',(now-86400,))
        return sid

    def revoke(self, row, source):
        source.revoke(row['anchor'])
        with self.connect() as db:
            db.execute('UPDATE sessions SET revoked=1 WHERE sid=?',(row['sid'],))
            db.execute('INSERT INTO events(action,actor_id,at) VALUES(?,?,?)',('logout',row['user_id'],int(time.time())))

    def operation(self, scope, key, action, body, function):
        fingerprint=self.digest(json.dumps(body,sort_keys=True,separators=(',',':'),ensure_ascii=False))
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE');db.execute('DELETE FROM operations WHERE created<?',(int(time.time())-86400,))
            row=db.execute('SELECT * FROM operations WHERE scope=? AND request_key=?',(scope,key)).fetchone()
            if row:
                if row['action']!=action or not hmac.compare_digest(row['fingerprint'],fingerprint):fail(409,'OPERATION_KEY_CONFLICT','同一请求编号不能用于不同操作或正文')
                if row['state']!='done':fail(409,'OPERATION_UNCERTAIN','操作进行中或结果不确定，请先核对，不要自动重复提交',2)
                return row['status'],json.loads(row['result'])
            if db.execute('SELECT count(*) FROM operations').fetchone()[0]>=20000:fail(503,'ACCOUNT_CAPACITY','操作恢复状态暂不可用',30)
            db.execute('INSERT INTO operations VALUES(?,?,?,?,?,NULL,NULL,?)',(scope,key,action,fingerprint,'pending',int(time.time())))
        try:
            status,result=function()
        except BaseException:
            with self.connect() as db:db.execute("UPDATE operations SET state='uncertain' WHERE scope=? AND request_key=?",(scope,key))
            raise
        with self.connect() as db:
            db.execute("UPDATE operations SET state='done',status=?,result=? WHERE scope=? AND request_key=?",
                       (status,json.dumps(result,ensure_ascii=False),scope,key))
        return status,result


def make_native_account(config, source):
    app=FastAPI(docs_url=None,redoc_url=None,openapi_url=None,redirect_slashes=False)
    accounts,guests,web=config['account_store'],config['store'],source.native_accounts
    a_only=config.get('account_a_only') is True
    formal=config.get('formal_account') is True
    player_registration=not formal and config.get('isolated_player_registration') is True
    app.state.native_a_only=a_only
    from backend import mini_features
    guest_actions={'register','login','resend-verification','forgot-password','verify-email','reset-password'}

    def formal_route(request):
        method, path = request.method, request.url.path
        allowed = (method, path) in {
            ('GET', PREFIX+'/session'), ('POST', PREFIX+'/auth/login'),
            ('GET', PREFIX+'/profile'), ('PUT', PREFIX+'/profile'),
        }
        if method == 'GET' and re.fullmatch(re.escape(PREFIX)+r'/operations/[A-Za-z0-9_-]{16,80}', path):
            allowed = request.query_params.get('action') in ('login', 'profile-save')
        if not allowed:
            fail(404,'ACCOUNT_ROUTE_PENDING','正式账号入口未开放该操作')
        if method == 'PUT' and not config.get('formal_profile_writes'):
            fail(503,'ACCOUNT_CLOUD_WRITE_DISABLED','正式云车库暂时只读')

    def actor_for(request,row):
        actor=web.user(web.request(request,row['anchor'],row['user_id']))
        if actor['id']!=row['user_id'] or actor['role']!=row['role']:
            fail(401,'ROLE_CHANGED','账号权限已变化，请重新登录并清理旧权限缓存')
        return {**actor,'verified':bool(actor['verified'])}

    def features():
        return {'website':{name:bool(getattr(source,name,False)) for name in ('coverage','contributions','feedback','notifications')},
                'profiles':{'cn':'account','global':'account' if getattr(source,'global_profiles',False) else 'unavailable'},
                'authentication':{'mail_mode':'production' if source.mail_service.config.production else source.mail_service.config.mode,
                                  'mail_token_ttl_seconds':1800,'persistent_wechat_binding':False,'reauth_max_age_seconds':600,
                                  'isolated_player_registration':player_registration},
                'native_batches':{'A':'ready',**dict.fromkeys(('B','C','D','E'),'pending' if a_only else 'ready')},'feature_writes':{'fixture_only':True,'enabled':not a_only and mini_features.writes_enabled(config,source)}}

    def session_result(request,sid):
        row=accounts.authenticate('Bearer '+accounts.token(sid),guests);actor=actor_for(request,row)
        return {'schema_version':1,'session_kind':'racepick_account','token_type':'Bearer','token':accounts.token(sid),
                'actor':actor,'expires_at':row['expires'],'authenticated_at':row['authenticated_at'],
                'features':features(),'association':{'kind':'session_only','persistent_binding':False,
                    'guest_identity':guests.authenticate('Bearer '+guests.token(row['guest_sid']))['identity']},
                'high_privilege_writes_ready':not a_only and mini_features.writes_enabled(config,source) and actor['role'] in ('admin','superadmin') and time.time()-row['authenticated_at']<=600}

    def expected_actor(request):
        if request.headers.get('x-account-id')!=request.state.actor['id']:
            fail(401,'ACTOR_CHANGED','账号未确认或已切换，请保留分账号草稿并刷新')

    @app.middleware('http')
    async def auth(request,call_next):
        try:
            if request.headers.get('origin') or request.headers.get('cookie') or request.method=='OPTIONS':fail(403,'NATIVE_ONLY','原生账号入口不使用网页Cookie或Origin')
            if formal:formal_route(request)
            guests.budget('account-ip:'+guests.hashed(request.scope['mini_ip']),120,60)
            path=request.url.path
            action=path.rsplit('/',1)[-1]
            recovery=path.startswith(PREFIX+'/operations/')
            guest_needed=(path.startswith(PREFIX+'/auth/') and action in guest_actions) or (recovery and request.query_params.get('action') in guest_actions|{'reauth'})
            session_guest=path==PREFIX+'/session' and request.method=='GET' and not request.headers.get('authorization','').startswith('Bearer rpa1.')
            feature=mini_features.match(request)
            public=feature is not None and feature['access']=='public'
            if public and not request.headers.get('authorization'):
                request.state.guest=None;request.state.actor=None
            elif (public and not request.headers.get('authorization','').startswith('Bearer rpa1.')) or guest_needed or session_guest:
                request.state.guest=guests.authenticate(request.headers.get('authorization'))
            else:
                row=accounts.authenticate(request.headers.get('authorization'),guests)
                request.state.account=row;request.state.actor=actor_for(request,row)
                request.state.guest=guests.authenticate('Bearer '+guests.token(row['guest_sid']))
                if path!=PREFIX+'/session':expected_actor(request)
            if feature is not None:await mini_features.guard(request,feature,config,source)
            return await call_next(request)
        except MiniError as error:return error_response(error)
        except HTTPException as error:return error_response(account_error(error))
        except (ValueError,OSError,sqlite3.Error):return error_response(MiniError(503,'ACCOUNT_STATE_UNAVAILABLE','账号服务暂不可用；原草稿保持',5))

    @app.exception_handler(MiniError)
    async def failure(request,error):return error_response(error)

    @app.exception_handler(StarletteHTTPException)
    async def http_failure(request,error):
        if error.status_code in (404,405):return error_response(MiniError(error.status_code,'ACCOUNT_ROUTE_PENDING','原生账号路径或方法尚未固定'))
        return error_response(account_error(error))

    async def body_for(request):
        if request.query_params or request.headers.get('content-type','').split(';')[0]!='application/json':fail(415,'JSON_REQUIRED','需要无query的JSON正文')
        try:body=json.loads(await limited_body(request,65536))
        except (ValueError,UnicodeError):fail(400,'INVALID_ACCOUNT_BODY','账号正文无效')
        if not isinstance(body,dict) or type(body.get('schema')) is not int or body['schema']!=1:fail(400,'INVALID_ACCOUNT_BODY','账号schema无效')
        request_key(body.get('request_key'))
        return body

    def validated(name,body):
        try:return web.models[name].model_validate(body)
        except ValidationError:fail(400,'INVALID_ACCOUNT_BODY','账号字段无效；请按契约检查，秘密不回显')

    def execute(request,action,body):
        payload={k:v for k,v in body.items() if k not in ('schema','request_key')}
        if player_registration and action in ('register','resend-verification'):
            fields={'email','password'} if action=='register' else {'email'}
            if set(payload)!=fields:fail(400,'INVALID_ACCOUNT_BODY','隔离注册仅接受普通玩家字段')
        if action=='reauth':
            if set(payload)!={'password'}:fail(400,'INVALID_ACCOUNT_BODY','再认证只接受password')
            model=validated('login',{'email':request.state.actor['email'],'password':payload['password']})
        else:model=validated(action,payload)
        if player_registration and action in ('register','resend-verification') and not model.email.endswith('.test'):
            fail(400,'INVALID_ACCOUNT_BODY','隔离收件箱仅接受 .test 邮箱')
        def invoke():
            try:
                row=getattr(request.state,'account',None)
                internal=web.request(request,row['anchor'] if row else None,request.state.actor['id'] if row else None)
                if action in ('login','reauth'):
                    captured=Response()
                    result=web.handlers['login'](model,internal,captured)
                    anchor,uid,expiry=web.anchor(captured)
                    with guests.connect() as db:guest_expiry=db.execute('SELECT expires FROM sessions WHERE sid=?',(request.state.guest['sid'],)).fetchone()[0]
                    sid=accounts.issue(request.state.guest,anchor,result['user'],min(expiry,guest_expiry),web)
                    return 200,{'account_sid':sid}
                return 200,web.handlers[action](model,internal)
            except HTTPException as error:
                mapped=account_error(error,action in ('login','reauth'))
                return error.status_code,{'schema_version':1,'code':mapped.code,'detail':mapped.message}
        status,result=accounts.operation('guest:'+request.state.guest['sid'],body['request_key'],action,payload,invoke)
        if status==200 and 'account_sid' in result:result=session_result(request,result['account_sid'])
        return JSONResponse(result,status_code=status,headers={'Retry-After':'60'} if status==429 else None)

    @app.get(PREFIX+'/session')
    async def session(request:Request):
        if request.query_params:fail(400,'INVALID_QUERY','session不接受query')
        if hasattr(request.state,'account'):
            result=session_result(request,request.state.account['sid']);result.pop('token');return result
        return {'schema_version':1,'session_kind':'wechat_guest','actor':None,'features':features(),
                'association':{'kind':'none','persistent_binding':False,'guest_identity':request.state.guest['identity']}}

    @app.delete(PREFIX+'/session')
    @app.delete(PREFIX+'/association')
    async def logout(request:Request):
        if request.query_params:fail(400,'INVALID_QUERY','退出不接受query')
        accounts.revoke(request.state.account,web)
        return {'logged_out':True,'scope':'current_native_account_session','guest_session_retained':True,'website_other_sessions_revoked':False}

    @app.post(PREFIX+'/auth/{action}')
    async def auth_action(action:str,request:Request):
        if action not in guest_actions|{'reauth','redeem-invitation'}:fail(404,'ACCOUNT_ROUTE_PENDING','账号路径尚未固定')
        return await run_in_threadpool(execute,request,action,await body_for(request))

    @app.get(PREFIX+'/operations/{key}')
    async def recover(key:str,request:Request):
        request_key(key)
        action=request.query_params.get('action')
        pairs=list(request.query_params.multi_items())
        if action not in guest_actions|{'reauth','redeem-invitation','profile-save'}:fail(400,'INVALID_QUERY','恢复必须提供固定action')
        if action=='profile-save':
            if len(pairs)!=2 or {k for k,v in pairs}!={'action','server'} or request.query_params['server'] not in ('cn','global'):fail(400,'INVALID_QUERY','车库恢复必须提供server')
        elif len(pairs)!=1:fail(400,'INVALID_QUERY','恢复query无效')
        scope=('account:'+request.state.account['sid']) if action=='profile-save' else ('guest:'+request.state.guest['sid'])
        with accounts.connect() as db:row=db.execute('SELECT * FROM operations WHERE scope=? AND request_key=?',(scope,key)).fetchone()
        if row is None:fail(404,'OPERATION_NOT_FOUND','没有保留的操作结果；不自动重复发邮件或保存')
        expected_action='profile-save:'+request.query_params['server'] if action=='profile-save' else action
        if row['action']!=expected_action:fail(409,'OPERATION_KEY_CONFLICT','操作类型不匹配')
        if row['state']!='done':fail(409,'OPERATION_UNCERTAIN','操作进行中或结果不确定，请核对',2)
        result=json.loads(row['result'])
        if row['status']==200 and 'account_sid' in result:result=session_result(request,result['account_sid'])
        if player_registration and action in ('register','resend-verification','verify-email') and 400<=row['status']<500:
            result={**result,'operation_resolved':True}
        return JSONResponse(result,status_code=row['status'])

    def server(request):
        pairs=list(request.query_params.multi_items())
        if len(pairs)!=1 or pairs[0][0]!='server' or pairs[0][1] not in ('cn','global'):fail(400,'INVALID_QUERY','必须显式选择cn或global')
        return pairs[0][1]

    @app.get(PREFIX+'/profile')
    async def profile(request:Request):
        selected=server(request)
        row=request.state.account
        value=await run_in_threadpool(web.handlers['get-global-profile' if selected=='global' else 'get-profile'],web.request(request,row['anchor'],row['user_id']))
        return {'server':selected,'storage':'account','remote_supported':True,**value}

    @app.put(PREFIX+'/profile')
    async def save_profile(request:Request):
        selected=server(request)
        if request.headers.get('content-type','').split(';')[0]!='application/json':fail(415,'JSON_REQUIRED','需要JSON正文')
        try:body=json.loads(await limited_body(request,65536))
        except (ValueError,UnicodeError):fail(400,'INVALID_PROFILE','车库正文无效')
        if not isinstance(body,dict) or type(body.get('schema')) is not int or body['schema']!=1 or body.get('explicit_save') is not True:
            fail(409,'EXPLICIT_SAVE_REQUIRED','必须由用户明确点击保存')
        key=request_key(body.get('request_key'))
        if body.get('intent') not in ('save','import_guest') or (body['intent']=='import_guest' and body.get('confirm_guest_import') is not True):
            fail(409,'IMPORT_CONFIRMATION_REQUIRED','游客导入必须显式确认')
        allowed={'schema','request_key','explicit_save','intent','confirm_guest_import','revision','cars','stars'} | ({'ocMap'} if selected=='global' else set())
        if set(body)-allowed:fail(400,'INVALID_PROFILE','存在未固定字段')
        fields=('revision','cars','stars','ocMap') if selected=='global' else ('revision','cars','stars')
        model=validated('put-global-profile' if selected=='global' else 'put-profile',{k:body[k] for k in fields if k in body})
        row=request.state.account
        internal=web.request(request,row['anchor'],row['user_id'],True)
        def invoke():
            try:return 200,{'server':selected,**web.handlers['put-global-profile' if selected=='global' else 'put-profile'](model,internal)}
            except HTTPException as error:
                result={'schema_version':1,'server':selected,'code':'PROFILE_CONFLICT' if error.status_code==409 else 'PROFILE_REJECTED','detail':str(error.detail)}
                if error.status_code==409:
                    result.update(current=web.handlers['get-global-profile' if selected=='global' else 'get-profile'](internal),submitted={'revision':model.revision,'profile':{k:v for k,v in model.model_dump().items() if k!='revision'}})
                return error.status_code,result
        status,value=await run_in_threadpool(accounts.operation,'account:'+row['sid'],key,'profile-save:'+selected,{'server':selected,**body},invoke)
        return JSONResponse(value,status_code=status)

    app.state.native_features=({'routes':[]} if a_only else mini_features.install(app,config,source))
    return app


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('command',choices=['provision','check']);parser.add_argument('--state-dir',type=Path,required=True)
    args=parser.parse_args()
    if args.command=='provision':provision(args.state_dir)
    else:AccountStore(args.state_dir)
    print(json.dumps({'schema':1,'website_database_opened':False}))
