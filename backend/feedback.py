"""Private text feedback; production requires an explicit offline migration."""
import hashlib
import json
import secrets
import time
from typing import Literal

from fastapi import HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, Field, StrictInt, field_validator

Status = Literal['pending', 'processing', 'needs_info', 'resolved', 'closed']
Filter = Literal['all', 'pending', 'processing', 'needs_info', 'resolved', 'closed']


TABLES = ('feedback_schema','feedback_tickets','feedback_events','feedback_requests')


def state(db):
    present = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    owned = present.intersection(TABLES)
    if not owned: return {'feedback_schema': 0, 'feedback_counts': {}}
    if owned != set(TABLES): raise ValueError('反馈表不完整，保留现场，不自动重建')
    rows = db.execute('SELECT version FROM feedback_schema').fetchall()
    if len(rows) != 1 or rows[0][0] != 1: raise ValueError('反馈版本不兼容')
    return {'feedback_schema': 1, 'feedback_counts': {n:db.execute('SELECT count(*) FROM '+n).fetchone()[0] for n in TABLES[1:]}}


def migrate(db):
    if state(db)['feedback_schema']==1: return
    for sql in (
        'CREATE TABLE feedback_schema(version INTEGER PRIMARY KEY)',
        '''CREATE TABLE feedback_tickets(id TEXT PRIMARY KEY, owner_id TEXT NOT NULL REFERENCES users(id),
            category TEXT NOT NULL, title TEXT NOT NULL, description TEXT NOT NULL,
            steps TEXT NOT NULL, expected TEXT NOT NULL, actual TEXT NOT NULL,
            source_page TEXT NOT NULL, app_version TEXT NOT NULL,
            status TEXT NOT NULL CHECK(status IN ('pending','processing','needs_info','resolved','closed')),
            revision INTEGER NOT NULL, created_at INTEGER NOT NULL, updated_at INTEGER NOT NULL)''',
        '''CREATE TABLE feedback_events(id INTEGER PRIMARY KEY, ticket_id TEXT NOT NULL REFERENCES feedback_tickets(id),
            actor_id TEXT NOT NULL REFERENCES users(id), actor_role TEXT NOT NULL, message TEXT NOT NULL,
            from_status TEXT, to_status TEXT NOT NULL, revision INTEGER NOT NULL, created_at INTEGER NOT NULL,
            UNIQUE(ticket_id,revision))''',
        '''CREATE TABLE feedback_requests(user_id TEXT NOT NULL REFERENCES users(id), request_key TEXT NOT NULL,
            fingerprint TEXT NOT NULL, result TEXT NOT NULL, PRIMARY KEY(user_id,request_key))''',
        'CREATE INDEX feedback_owner_updated ON feedback_tickets(owner_id,updated_at)',
        'CREATE INDEX feedback_status_updated ON feedback_tickets(status,updated_at)',
        'CREATE INDEX feedback_events_actor_time ON feedback_events(actor_id,created_at)',
    ):
        db.execute(sql)
    db.execute('INSERT INTO feedback_schema VALUES(1)')


class Create(BaseModel):
    model_config = ConfigDict(extra='forbid')
    request_key: str = Field(pattern=r'^[a-zA-Z0-9_-]{16,80}$')
    category: Literal['bug', 'data', 'suggestion', 'other']
    title: str = Field(min_length=1, max_length=100)
    description: str = Field(min_length=1, max_length=6000)
    steps: str = Field(default='', max_length=3000)
    expected: str = Field(default='', max_length=2000)
    actual: str = Field(default='', max_length=2000)
    source_page: str = Field(default='/', pattern=r'^/(?:[a-z0-9_-]+)?$', max_length=100)

    @field_validator('title', 'description')
    @classmethod
    def nonempty(cls, value):
        if not value.strip(): raise ValueError('标题和描述不能为空')
        return value.strip()


class Reply(BaseModel):
    model_config = ConfigDict(extra='forbid')
    request_key: str = Field(pattern=r'^[a-zA-Z0-9_-]{16,80}$')
    revision: StrictInt = Field(ge=1)
    message: str = Field(min_length=1, max_length=4000)

    @field_validator('message')
    @classmethod
    def nonempty(cls, value):
        if not value.strip(): raise ValueError('请填写回复或处理说明')
        return value.strip()


class Handle(Reply):
    status: Status


def install(app, store, root, user):
    # Only an allowlisted release label is attached, never environment/configuration or cookies.
    version = 'local-feedback-v1'
    if getattr(getattr(app.state,'score_versions',None),'production',False):
        version='production-source'
        manifest=root/'manifest.json'
        if manifest.is_file():
            import re
            version=json.loads(manifest.read_text(encoding='utf-8')).get('id','')
            if not re.fullmatch('[a-f0-9]{24}',version): raise ValueError('发布清单版本无效')

    def actor(request, admin=False, db=None):
        current = user(request)
        if request.headers.get('x-account-id') != current['id']:
            raise HTTPException(401, '账号已切换，请刷新后重试')
        if not current['verified']:
            raise HTTPException(403, '请先验证邮箱')
        if admin and current['role'] != 'superadmin':
            raise HTTPException(403, '仅站长可查看和处理全部反馈')
        if db is not None:
            app.state.require_active_session(request, db)
            if admin and not db.execute('SELECT 1 FROM super_admins WHERE user_id=?', (current['id'],)).fetchone():
                raise HTTPException(403, '管理权限已变化，请刷新')
        return current

    def get_ticket(db, tid, current, admin=False):
        row = db.execute('SELECT * FROM feedback_tickets WHERE id=?', (tid,)).fetchone()
        if not row or (not admin and row['owner_id'] != current['id']):
            raise HTTPException(404, '反馈不存在')
        return row

    def idempotency(db, current, body, target):
        raw = json.dumps([target, body.model_dump()], ensure_ascii=False, sort_keys=True)
        fingerprint = hashlib.sha256(raw.encode()).hexdigest()
        previous = db.execute('SELECT * FROM feedback_requests WHERE user_id=? AND request_key=?',
                              (current['id'], body.request_key)).fetchone()
        if previous:
            if previous['fingerprint'] != fingerprint: raise HTTPException(409, '提交标识已用于其他内容，请刷新')
            return fingerprint, json.loads(previous['result'])
        return fingerprint, None

    def remember(db, current, body, fingerprint, result):
        db.execute('INSERT INTO feedback_requests VALUES(?,?,?,?)',
                   (current['id'], body.request_key, fingerprint, json.dumps(result)))
        return result

    @app.get('/feedback')
    @app.get('/admin-feedback')
    def page(): return FileResponse(root/'feedback.html')

    @app.get('/api/feedback/context')
    def context(request: Request):
        actor(request)
        return {'app_version': version, 'privacy': '仅你和站长可查看。附带账号、提交时间、页面路径和应用版本；不收集日志、车库或浏览器信息。'}

    @app.post('/api/feedback')
    def create(body: Create, request: Request):
        with store.connect() as db:
            db.execute('BEGIN IMMEDIATE'); current = actor(request, db=db)
            fingerprint, previous = idempotency(db, current, body, 'create')
            if previous is not None: return previous
            now = int(time.time())
            count = db.execute('SELECT count(*) FROM feedback_tickets WHERE owner_id=? AND created_at>?',
                               (current['id'], now-86400)).fetchone()[0]
            if count >= 10: raise HTTPException(429, '每天最多新建10条反馈；已有问题请在原反馈中补充')
            tid = secrets.token_hex(16)
            db.execute('INSERT INTO feedback_tickets VALUES(?,?,?,?,?,?,?,?,?,?,?,1,?,?)',
                       (tid, current['id'], body.category, body.title, body.description, body.steps.strip(),
                        body.expected.strip(), body.actual.strip(), body.source_page, version, 'pending', now, now))
            db.execute('INSERT INTO feedback_events(ticket_id,actor_id,actor_role,message,from_status,to_status,revision,created_at) VALUES(?,?,?,?,NULL,?,1,?)',
                       (tid, current['id'], 'owner', '', 'pending', now))
            return remember(db, current, body, fingerprint, {'id': tid, 'revision': 1, 'status': 'pending'})

    def listing(request, status, offset, q, admin):
        current = actor(request, admin)
        if offset < 0 or len(q) > 100: raise HTTPException(422, '查询参数不正确')
        conditions = ['1=1'] if admin else ['owner_id=?']; args = [] if admin else [current['id']]
        if status != 'all': conditions.append('status=?'); args.append(status)
        if q:
            conditions.append("title LIKE ? ESCAPE '\\'")
            args.append('%'+q.replace('\\','\\\\').replace('%','\\%').replace('_','\\_')+'%')
        where = ' AND '.join(conditions)
        with store.connect() as db:
            total = db.execute('SELECT count(*) FROM feedback_tickets WHERE '+where, args).fetchone()[0]
            items = [dict(r) for r in db.execute('SELECT id,title,category,status,revision,created_at,updated_at FROM feedback_tickets WHERE '+where+' ORDER BY updated_at DESC,id LIMIT 30 OFFSET ?', args+[offset])]
        return {'items': items, 'total': total}

    @app.get('/api/feedback')
    def mine(request: Request, status: Filter = 'all', offset: int = 0, q: str = ''):
        return listing(request, status, offset, q, False)

    @app.get('/api/admin/feedback')
    def all_feedback(request: Request, status: Filter = 'all', offset: int = 0, q: str = ''):
        return listing(request, status, offset, q, True)

    @app.get('/api/admin/feedback/summary')
    def summary(request: Request):
        actor(request, True)
        with store.connect() as db:
            counts = dict(db.execute('SELECT status,count(*) FROM feedback_tickets GROUP BY status'))
        return {'pending': counts.get('pending', 0), 'counts': counts}

    def detail(tid, request, admin):
        current = actor(request, admin)
        with store.connect() as db:
            row = get_ticket(db, tid, current, admin); result = dict(row)
            result.pop('owner_id')
            result['events'] = [dict(r) for r in db.execute('SELECT actor_role,message,from_status,to_status,created_at,revision FROM feedback_events WHERE ticket_id=? ORDER BY revision', (tid,))]
            if admin:
                identity = db.execute('SELECT email FROM users WHERE id=?', (row['owner_id'],)).fetchone()
                result['owner_email'] = identity['email']
                nickname = db.execute('SELECT nickname FROM contribution_preferences WHERE user_id=?', (row['owner_id'],)).fetchone()
                result['owner_nickname'] = nickname['nickname'] if nickname else ''
        return result

    @app.get('/api/feedback/{tid}')
    def my_detail(tid: str, request: Request): return detail(tid, request, False)

    @app.get('/api/admin/feedback/{tid}')
    def admin_detail(tid: str, request: Request): return detail(tid, request, True)

    def update(tid, body, request, admin):
        with store.connect() as db:
            db.execute('BEGIN IMMEDIATE'); current = actor(request, admin, db)
            row = get_ticket(db, tid, current, admin)
            fingerprint, previous = idempotency(db, current, body, ('admin:' if admin else 'owner:')+tid)
            if previous is not None: return previous
            if row['revision'] != body.revision: raise HTTPException(409, '反馈已被更新，请刷新详情后重试')
            if not admin and row['status'] == 'closed': raise HTTPException(409, '反馈已关闭，请新建反馈引用此编号')
            now = int(time.time())
            if db.execute('SELECT count(*) FROM feedback_events WHERE actor_id=? AND created_at>?', (current['id'], now-3600)).fetchone()[0] >= 30:
                raise HTTPException(429, '回复过于频繁，请稍后重试')
            status = body.status if admin else ('pending' if row['status'] in ('needs_info','resolved') else row['status'])
            revision = row['revision']+1
            db.execute('UPDATE feedback_tickets SET status=?,revision=?,updated_at=? WHERE id=?', (status, revision, now, tid))
            db.execute('INSERT INTO feedback_events(ticket_id,actor_id,actor_role,message,from_status,to_status,revision,created_at) VALUES(?,?,?,?,?,?,?,?)',
                       (tid, current['id'], 'superadmin' if admin else 'owner', body.message, row['status'], status, revision, now))
            return remember(db, current, body, fingerprint, {'revision': revision, 'status': status, 'id': tid})

    @app.post('/api/feedback/{tid}/reply')
    def reply(tid: str, body: Reply, request: Request): return update(tid, body, request, False)

    @app.post('/api/admin/feedback/{tid}/handle')
    def handle(tid: str, body: Handle, request: Request): return update(tid, body, request, True)
