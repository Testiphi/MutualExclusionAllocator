"""Explicitly provisioned native guest state. Never opens the website account DB."""
from contextlib import contextmanager
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, build_opener, HTTPRedirectHandler
import hashlib
import hmac
import json
import os
import re
import secrets
import sqlite3
import stat
import time

KIND = 'racepick-mini-guests-v1'
TOKEN_TTL = 3600


class MiniError(Exception):
    def __init__(self, status, code, message, retry=None):
        self.status, self.code, self.message, self.retry = status, code, message, retry
        super().__init__(message)


def fail(status, code, message, retry=None):
    raise MiniError(status, code, message, retry)


def request_key(value):
    if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9_-]{16,80}', value):
        fail(400, 'INVALID_REQUEST_KEY', '请求编号无效')
    return value


def provision(root):
    root = Path(root).absolute()
    if root.resolve() != root or root.is_relative_to(Path(__file__).resolve().parents[1]) or root.exists():
        raise ValueError('原生会话只允许显式新建发布目录之外的独立目录')
    root.mkdir(mode=0o700)
    (root/'state.json').write_text(json.dumps({'kind': KIND, 'schema': 1}), encoding='utf-8')
    (root/'token.key').write_bytes(secrets.token_bytes(32))
    for name in ('state.json', 'token.key'):
        (root/name).chmod(0o600)
    store = GuestStore(root, initialize=True)
    store.path.chmod(0o600)
    return root


class GuestStore:
    def __init__(self, root, initialize=False):
        self.root = Path(root).absolute()
        if self.root.resolve() != self.root or self.root.is_relative_to(Path(__file__).resolve().parents[1]):
            raise ValueError('原生会话状态路径不正确')
        if json.loads((self.root/'state.json').read_text('utf-8')) != {'kind': KIND, 'schema': 1}:
            raise ValueError('原生会话标记不正确')
        for p in [self.root, *self.root.iterdir()]:
            if p.is_symlink() or p.resolve() != p or (p.is_file() and p.stat().st_nlink != 1):
                raise ValueError('原生会话状态不能为链接')
            if os.name == 'posix' and (stat.S_IMODE(p.stat().st_mode) & 0o077 or p.stat().st_uid != os.geteuid()):
                raise ValueError('原生会话状态必须为当前用户私有')
        if any((self.root/n).exists() for n in ('accounts.sqlite3', 'production.json', 'recognition.sqlite3')):
            raise ValueError('原生会话目录不能混用业务或识图队列')
        self.key = (self.root/'token.key').read_bytes()
        if len(self.key) != 32:
            raise ValueError('原生会话签名密钥无效')
        self.path = self.root/'guests.sqlite3'
        if initialize:
            with self.connect() as db:
                db.executescript('''
                CREATE TABLE meta(version INTEGER NOT NULL); INSERT INTO meta VALUES(1);
                CREATE TABLE sessions(sid TEXT PRIMARY KEY, subject TEXT NOT NULL, expires INTEGER NOT NULL, revoked INTEGER NOT NULL DEFAULT 0);
                CREATE TABLE codes(code_hash TEXT PRIMARY KEY, key_hash TEXT NOT NULL, state TEXT NOT NULL, sid TEXT, created INTEGER NOT NULL);
                CREATE TABLE budgets(bucket TEXT PRIMARY KEY, count INTEGER NOT NULL, expires INTEGER NOT NULL);
                CREATE TABLE uploads(owner TEXT NOT NULL, request_key TEXT NOT NULL, version TEXT NOT NULL,
                    state TEXT NOT NULL, lease TEXT NOT NULL, updated REAL NOT NULL, PRIMARY KEY(owner,request_key));
                ''')
        else:
            if not self.path.is_file():
                raise ValueError('原生会话状态未显式初始化')
            with self.connect() as db:
                if db.execute('SELECT version FROM meta').fetchall() != [(1,)]:
                    raise ValueError('原生会话schema不兼容；启动不自动迁移')

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.execute('PRAGMA max_page_count=8192')
        db.execute('PRAGMA journal_size_limit=1048576')
        try:
            with db:
                yield db
        finally:
            db.close()

    def hashed(self, value):
        return hmac.new(self.key, value.encode(), hashlib.sha256).hexdigest()

    def token(self, sid):
        return sid + '.' + self.hashed('token:' + sid)

    def budget(self, bucket, maximum, seconds):
        now = int(time.time())
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            db.execute('DELETE FROM budgets WHERE expires<=?', (now,))
            row = db.execute('SELECT count,expires FROM budgets WHERE bucket=?', (bucket,)).fetchone()
            if row is None and db.execute('SELECT count(*) FROM budgets').fetchone()[0] >= 20000:
                fail(503, 'SESSION_CAPACITY', '会话服务暂不可用', 30)
            if row and row[0] >= maximum:
                fail(429, 'RATE_LIMITED', '请求过于频繁，请稍后重试', max(1, row[1]-now))
            db.execute('INSERT INTO budgets VALUES (?,1,?) ON CONFLICT(bucket) DO UPDATE SET count=count+1', (bucket, now+seconds))

    def exchange(self, code, key, verifier):
        now = int(time.time())
        code_hash, key_hash = self.hashed('code:'+code), self.hashed('request:'+key)
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            db.execute('DELETE FROM codes WHERE created<?', (now-86400,))
            db.execute('DELETE FROM sessions WHERE expires<?', (now-600,))
            db.execute('DELETE FROM uploads WHERE updated<?', (now-4200,))
            row = db.execute('SELECT key_hash,state,sid FROM codes WHERE code_hash=?', (code_hash,)).fetchone()
            if row:
                if not hmac.compare_digest(row[0], key_hash):
                    fail(409, 'CODE_ALREADY_CLAIMED', '临时代码已用于另一请求，请重新登录')
                if row[1] == 'ready':
                    session = db.execute('SELECT expires,revoked FROM sessions WHERE sid=?', (row[2],)).fetchone()
                    if session and session[0] > now and not session[1]:
                        return self.session_result(row[2], session[0])
                    fail(401, 'SESSION_EXPIRED', '会话已失效，请重新登录；旧任务不能自动换身份重传')
                fail(409, 'CODE_EXCHANGE_UNCERTAIN', '代码交换进行中或结果不确定，请取得新的登录代码', 2)
            if db.execute('SELECT count(*) FROM codes').fetchone()[0] >= 10000:
                fail(503, 'SESSION_CAPACITY', '会话服务暂不可用', 30)
            db.execute('INSERT INTO codes VALUES (?,?,?,NULL,?)', (code_hash, key_hash, 'pending', now))
        try:
            subject = verifier(code)
            if not isinstance(subject, str) or not 1 <= len(subject) <= 256:
                fail(503, 'PLATFORM_UNAVAILABLE', '平台验证未完成', 5)
        except BaseException:
            with self.connect() as db:
                db.execute("UPDATE codes SET state='uncertain' WHERE code_hash=?", (code_hash,))
            raise
        sid = secrets.token_hex(24)
        expires = int(time.time()) + TOKEN_TTL
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            db.execute('INSERT INTO sessions(sid,subject,expires) VALUES (?,?,?)', (sid, self.hashed('subject:'+subject), expires))
            db.execute("UPDATE codes SET state='ready',sid=? WHERE code_hash=?", (sid, code_hash))
        return self.session_result(sid, expires)

    def session_result(self, sid, expires):
        return {'schema_version': 1, 'token': self.token(sid), 'token_type': 'Bearer',
                'identity': self.hashed('identity:'+sid), 'expires_at': expires, 'expires_in': max(0, expires-int(time.time()))}

    def authenticate(self, authorization):
        if not isinstance(authorization, str) or not re.fullmatch(r'Bearer [a-f0-9]{48}\.[a-f0-9]{64}', authorization):
            fail(401, 'SESSION_REQUIRED', '需要有效原生会话')
        token = authorization[7:]
        sid = token[:48]
        if not hmac.compare_digest(self.token(sid), token):
            fail(401, 'SESSION_INVALID', '原生会话无效')
        with self.connect() as db:
            row = db.execute('SELECT expires,revoked FROM sessions WHERE sid=?', (sid,)).fetchone()
        if not row or row[0] <= time.time() or row[1]:
            fail(401, 'SESSION_EXPIRED', '原生会话已失效；保留草稿，请重新登录')
        return {'sid': sid, 'owner': 'mini-v1:'+self.hashed('owner:'+sid), 'identity': self.hashed('identity:'+sid)}


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


class WechatVerifier:
    def __init__(self, appid, secret):
        if not re.fullmatch(r'wx[a-fA-F0-9]{16}', appid) or not secret or len(secret) > 256:
            raise ValueError('需服务端安全配置有效的AppID和AppSecret')
        self.appid, self.secret = appid, secret

    def __call__(self, code):
        query = urlencode({'appid': self.appid, 'secret': self.secret, 'js_code': code, 'grant_type': 'authorization_code'})
        try:
            # Fixed HTTPS host, bounded body/timeout, no redirects, no URL/error logging.
            with build_opener(NoRedirect).open(Request('https://api.weixin.qq.com/sns/jscode2session?'+query), timeout=8) as response:
                raw = response.read(8193)
            if len(raw) > 8192:
                raise ValueError('response size')
            data = json.loads(raw)
        except Exception:
            fail(503, 'PLATFORM_UNAVAILABLE', '平台验证暂不可用，请稍后重新登录', 5)
        if not isinstance(data, dict):
            fail(503, 'PLATFORM_UNAVAILABLE', '平台验证暂不可用', 5)
        error = data.get('errcode', 0)
        if error in (40029, 40163, 40226):
            fail(401, 'PLATFORM_CODE_REJECTED', '登录代码无效或已使用，请重新登录')
        if error == 45011:
            fail(429, 'PLATFORM_RATE_LIMITED', '平台验证限流，请稍后重新登录', 60)
        if error != 0 or not isinstance(data.get('session_key'), str) or not data.get('openid'):
            fail(503, 'PLATFORM_UNAVAILABLE', '平台验证暂不可用', 5)
        # session_key is deliberately discarded: V1 has no encrypted profile/phone data.
        return data['openid']


def load_config(path):
    path = Path(path).absolute()
    if path.resolve() != path or path.is_symlink():
        raise ValueError('原生配置不能为链接')
    if os.name == 'posix' and (stat.S_IMODE(path.stat().st_mode) & 0o077 or path.stat().st_uid != os.geteuid()):
        raise ValueError('原生配置必须为当前用户私有')
    data = json.loads(path.read_text('utf-8'))
    if not {'kind', 'state_dir', 'appid', 'app_secret_file', 'image_policy'} <= set(data) or set(data)-{'kind', 'state_dir', 'appid', 'app_secret_file', 'image_policy','account_state_dir'} or data['kind'] != KIND:
        raise ValueError('原生配置字段不正确')
    secret_path = Path(data['app_secret_file'])
    if not secret_path.is_absolute() or secret_path.resolve() != secret_path or not secret_path.is_file() or secret_path.stat().st_nlink != 1:
        raise ValueError('AppSecret需独立的服务端凭据文件')
    if os.name == 'posix' and (stat.S_IMODE(secret_path.stat().st_mode) & 0o077 or secret_path.stat().st_uid != os.geteuid()):
        raise ValueError('AppSecret文件必须为当前用户私有')
    if data['image_policy'] not in ('disabled', 'private_unmoderated'):
        raise ValueError('图片策略必须显式选择；未接入内容安全服务')
    result={'store': GuestStore(data['state_dir']), 'verifier': WechatVerifier(data['appid'], secret_path.read_text('utf-8').strip()),
            'fixture': False, 'image_policy': data['image_policy']}
    if 'account_state_dir' in data:
        from backend.mini_accounts import AccountStore
        result['account_store']=AccountStore(data['account_state_dir'])
    return result


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=['provision', 'check'])
    parser.add_argument('--state-dir', type=Path, required=True)
    args = parser.parse_args()
    if args.command == 'provision':
        provision(args.state_dir)
    else:
        GuestStore(args.state_dir)
    print(json.dumps({'schema': 1, 'business_database_opened': False}))
