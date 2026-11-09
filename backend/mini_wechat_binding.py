"""Explicit isolated-only WeChat binding for existing RacePick users."""
import re
import secrets
import time

from argon2.exceptions import VerifyMismatchError

from backend.community import disabled
from backend.mini_auth import MiniError, fail

ACTIONS = frozenset({'wechat-bind', 'wechat-unbind'})


def provision(store):
    with store.connect() as db:
        db.execute('''CREATE TABLE mini_wechat_bindings(
            user_id TEXT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
            subject_digest TEXT NOT NULL UNIQUE)''')


def bound(store, user_id):
    with store.connect() as db:
        return db.execute('SELECT 1 FROM mini_wechat_bindings WHERE user_id=?',
                          (user_id,)).fetchone() is not None


def validate(action, payload):
    fields = {'password', 'code'} if action == 'wechat-bind' else {'password'}
    if (set(payload) != fields or not isinstance(payload['password'], str)
            or not 1 <= len(payload['password']) <= 128):
        fail(400, 'INVALID_ACCOUNT_BODY', '请输入当前账号密码')
    if action == 'wechat-bind' and (not isinstance(payload['code'], str)
            or not re.fullmatch(r'[A-Za-z0-9_-]{1,128}', payload['code'])):
        fail(400, 'INVALID_ACCOUNT_BODY', '微信凭证格式无效')


def login(store, guests, verifier, guest, code):
    from backend.app import digest

    if not isinstance(code, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,128}', code):
        fail(400, 'INVALID_ACCOUNT_BODY', '微信凭证格式无效')
    guests.budget('wechat-login:' + guest['owner'], 8, 600)
    try:
        subject = verifier(code)
    except MiniError as error:
        if error.code == 'PLATFORM_CODE_REJECTED':
            fail(403, 'WECHAT_CODE_EXPIRED', '微信凭证已失效，请重新发起登录')
        raise
    if not isinstance(subject, str) or not 1 <= len(subject) <= 256:
        fail(503, 'PLATFORM_UNAVAILABLE', '微信身份验证未完成', 5)
    with guests.connect() as db:
        parent = db.execute('SELECT subject,expires,revoked FROM sessions WHERE sid=?',
                            (guest['sid'],)).fetchone()
    if not parent or parent[2] or parent[1] <= time.time():
        fail(401, 'SESSION_EXPIRED', '微信会话已失效，请重新登录')
    if parent[0] != guests.hashed('subject:' + subject):
        fail(403, 'WECHAT_IDENTITY_CHANGED', '微信身份已变化，请重新登录')
    anchor = digest(secrets.token_urlsafe(32))
    with store.connect() as db:
        db.execute('BEGIN IMMEDIATE')
        actor = db.execute('''SELECT u.id,u.role,u.verified FROM users u
            JOIN mini_wechat_bindings b ON b.user_id=u.id WHERE b.subject_digest=?''',
                           (guests.hashed('wechat-binding:' + subject),)).fetchone()
        if not actor or not actor['verified'] or actor['role'] != 'player' or disabled(db, actor['id']):
            fail(403, 'WECHAT_LOGIN_UNAVAILABLE', '当前微信无法快捷登录，请使用邮箱登录')
        expiry = min(parent[1], int(time.time()) + 3600)
        if expiry <= time.time():
            fail(401, 'SESSION_EXPIRED', '微信会话已失效，请重新登录')
        # This anchor is internal. No browser cookie is created or returned.
        db.execute('INSERT INTO sessions VALUES (?,?,?,?)',
                   (anchor, actor['id'], secrets.token_urlsafe(32), expiry))
    return anchor, dict(actor), expiry


def current_password_hash(db, account):
    uid = account['user_id']
    row = db.execute('''SELECT u.password_hash,u.role,u.verified FROM users u
        JOIN sessions s ON s.user_id=u.id WHERE u.id=? AND s.token_hash=? AND s.expires_at>?''',
                     (uid, account['anchor'], int(time.time()))).fetchone()
    if not row or account['expires'] <= time.time():
        fail(401, 'ACCOUNT_SESSION_EXPIRED', '账号会话已失效，请重新登录')
    if disabled(db, uid):
        fail(403, 'ACCOUNT_DISABLED', '账号已停用')
    if row['role'] != account['role'] or not row['verified']:
        fail(403, 'ACCOUNT_BINDING_FORBIDDEN', '需要已验证且权限有效的账号')
    return row['password_hash']


def change(store, guests, verifier, account, action, payload, check_session):
    from backend.app import HASHER

    uid = account['user_id']
    guests.budget('wechat-binding:' + guests.hashed(uid), 8, 600)
    with store.connect() as db:
        password_hash = current_password_hash(db, account)
    try:
        HASHER.verify(password_hash, payload['password'])
    except VerifyMismatchError:
        fail(403, 'ACCOUNT_PASSWORD_INVALID', '账号密码不正确')

    binding = action == 'wechat-bind'
    subject_digest = None
    if binding:
        try:
            subject = verifier(payload['code'])
        except MiniError as error:
            if error.code == 'PLATFORM_CODE_REJECTED':
                fail(403, 'WECHAT_CODE_EXPIRED', '微信凭证已失效，请重新发起绑定')
            raise
        if not isinstance(subject, str) or not 1 <= len(subject) <= 256:
            fail(503, 'PLATFORM_UNAVAILABLE', '微信身份验证未完成', 5)
        with guests.connect() as db:
            parent = db.execute('SELECT subject FROM sessions WHERE sid=?',
                                (account['guest_sid'],)).fetchone()
        if not parent or parent[0] != guests.hashed('subject:' + subject):
            fail(403, 'WECHAT_IDENTITY_CHANGED', '微信身份已变化，请重新登录')
        subject_digest = guests.hashed('wechat-binding:' + subject)

    check_session()
    with store.connect() as db:
        db.execute('BEGIN IMMEDIATE')
        if current_password_hash(db, account) != password_hash:
            fail(403, 'ACCOUNT_PASSWORD_CHANGED', '密码已变化，请重新操作')
        previous = db.execute('SELECT subject_digest FROM mini_wechat_bindings WHERE user_id=?',
                              (uid,)).fetchone()
        if binding:
            if previous:
                fail(409, 'WECHAT_ALREADY_BOUND', '当前账号已绑定微信')
            if db.execute('SELECT 1 FROM mini_wechat_bindings WHERE subject_digest=?',
                          (subject_digest,)).fetchone():
                fail(409, 'WECHAT_ALREADY_IN_USE', '该微信已绑定其他账号')
            db.execute('INSERT INTO mini_wechat_bindings VALUES (?,?)', (uid, subject_digest))
        elif not previous:
            fail(409, 'WECHAT_NOT_BOUND', '当前账号尚未绑定微信')
        else:
            db.execute('DELETE FROM mini_wechat_bindings WHERE user_id=?', (uid,))
    return {'actor_id': uid, 'bound': binding}
