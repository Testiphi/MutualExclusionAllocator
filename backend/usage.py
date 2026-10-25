"""First-party usage counters, separate from account and score transactions."""
import base64
from contextlib import contextmanager, closing
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import json
from pathlib import Path
import secrets
import sqlite3
import time
from typing import Literal

from fastapi import HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, ConfigDict, Field

BJ = timezone(timedelta(hours=8), 'Asia/Shanghai')
PAGES = ('home', 'submissions', 'feedback', 'leaderboard')
FEATURES = ('generate', 'server_switch', 'garage_save_account', 'garage_save_local', 'submission_submit', 'feedback_submit')
RESULTS = ('success', 'empty', 'failed')
TABLES = {'usage_schema', 'usage_people', 'usage_events', 'usage_minutes', 'usage_daily', 'usage_hourly', 'usage_features'}


def day_at(stamp):
    return datetime.fromtimestamp(stamp, BJ).date().isoformat()


def schema(db):
    tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    if not tables.intersection(TABLES):
        return 0
    if not TABLES <= tables:
        raise ValueError('统计库不完整，保留现场')
    rows = db.execute('SELECT version FROM usage_schema').fetchall()
    if len(rows) != 1 or rows[0][0] != 1:
        raise ValueError('统计库版本不兼容')
    return 1


class UsageStore:
    def __init__(self, path):
        self.path = Path(path)
        if self.path.is_symlink() or not self.path.is_file():
            raise ValueError('统计库必须是已初始化的普通文件')
        with self.connect() as db:
            if schema(db) != 1:
                raise ValueError('统计库未初始化')
            self.secret = bytes.fromhex(db.execute('SELECT secret FROM usage_schema').fetchone()[0])

    @classmethod
    def initialize(cls, path):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        # Only a brand-new file; never silently upgrade or replace existing data.
        with path.open('xb'):
            pass
        with closing(sqlite3.connect(path)) as db, db:
            for statement in (
                'CREATE TABLE usage_schema(version INTEGER PRIMARY KEY,secret TEXT NOT NULL)',
                '''CREATE TABLE usage_people(actor TEXT PRIMARY KEY,kind TEXT NOT NULL,
                    first_seen INTEGER NOT NULL,last_visit INTEGER,last_interaction INTEGER)''',
                '''CREATE TABLE usage_events(id TEXT PRIMARY KEY,received_at INTEGER NOT NULL,
                    kind TEXT NOT NULL,page TEXT NOT NULL,server TEXT NOT NULL,actor TEXT NOT NULL,
                    session_id TEXT NOT NULL,feature TEXT NOT NULL,result TEXT NOT NULL,reason TEXT NOT NULL)''',
                'CREATE INDEX usage_events_time ON usage_events(received_at)',
                "CREATE UNIQUE INDEX usage_active_once ON usage_events(actor,server,(received_at/60)) WHERE kind='active'",
                'CREATE TABLE usage_minutes(actor TEXT NOT NULL,minute INTEGER NOT NULL,server TEXT NOT NULL,PRIMARY KEY(actor,minute,server))',
                '''CREATE TABLE usage_daily(day TEXT NOT NULL,actor TEXT NOT NULL,server TEXT NOT NULL,
                    visits INTEGER NOT NULL DEFAULT 0,returns INTEGER NOT NULL DEFAULT 0,active_minutes INTEGER NOT NULL DEFAULT 0,
                    PRIMARY KEY(day,actor,server))''',
                '''CREATE TABLE usage_hourly(day TEXT NOT NULL,hour INTEGER NOT NULL,actor TEXT NOT NULL,server TEXT NOT NULL,
                    active_minutes INTEGER NOT NULL,PRIMARY KEY(day,hour,actor,server))''',
                '''CREATE TABLE usage_features(day TEXT NOT NULL,actor TEXT NOT NULL,server TEXT NOT NULL,
                    feature TEXT NOT NULL,result TEXT NOT NULL,uses INTEGER NOT NULL,PRIMARY KEY(day,actor,server,feature,result))''',
            ):
                db.execute(statement)
            db.execute('INSERT INTO usage_schema VALUES(1,?)', (secrets.token_hex(32),))
        return cls(path)

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=0.15)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    def token(self, visitor, session_id, actor):
        payload = json.dumps([visitor, session_id, actor, int(time.time())+1800], separators=(',', ':')).encode()
        body = base64.urlsafe_b64encode(payload).decode().rstrip('=')
        return body+'.'+hmac.new(self.secret, body.encode(), hashlib.sha256).hexdigest()

    def verify(self, token, actor):
        try:
            body, signature = token.split('.')
            expected = hmac.new(self.secret, body.encode(), hashlib.sha256).hexdigest()
            if not hmac.compare_digest(expected, signature):
                raise ValueError()
            visitor, session_id, owner, expires = json.loads(base64.urlsafe_b64decode(body+'='*(-len(body)%4)))
            if expires < time.time() or owner != actor:
                raise ValueError()
            return visitor, session_id
        except (ValueError, TypeError, UnicodeError, KeyError):
            raise HTTPException(409, '统计会话已变化，请重新初始化') from None

    def append(self, actor, session_id, events, now=None):
        now = int(time.time() if now is None else now)
        date = datetime.fromtimestamp(now, BJ)
        day, hour, minute = date.date().isoformat(), date.hour, now//60
        accepted = 0
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            for e in events:
                cursor = db.execute('INSERT OR IGNORE INTO usage_events VALUES(?,?,?,?,?,?,?,?,?,?)',
                    (e['id'], now, e['kind'], e['page'], e['server'], actor, session_id,
                     e.get('feature', ''), e.get('result', ''), e.get('reason', '')))
                if not cursor.rowcount:
                    continue
                accepted += 1
                db.execute('INSERT OR IGNORE INTO usage_people(actor,kind,first_seen) VALUES(?,?,?)',
                           (actor, 'account' if actor.startswith('a:') else 'guest', now))
                if e['kind'] == 'visit':
                    db.execute('UPDATE usage_people SET last_visit=MAX(COALESCE(last_visit,0),?) WHERE actor=?', (now, actor))
                if e['kind'] == 'active':
                    db.execute('UPDATE usage_people SET last_interaction=MAX(COALESCE(last_interaction,0),?) WHERE actor=?', (now, actor))
                for server in ('all', e['server']):
                    db.execute('INSERT OR IGNORE INTO usage_daily(day,actor,server) VALUES(?,?,?)', (day, actor, server))
                    if e['kind'] == 'active':
                        if db.execute('INSERT OR IGNORE INTO usage_minutes VALUES(?,?,?)', (actor, minute, server)).rowcount:
                            db.execute('UPDATE usage_daily SET active_minutes=active_minutes+1 WHERE day=? AND actor=? AND server=?', (day, actor, server))
                            db.execute('''INSERT INTO usage_hourly VALUES(?,?,?,?,1) ON CONFLICT(day,hour,actor,server)
                                DO UPDATE SET active_minutes=active_minutes+1''', (day, hour, actor, server))
                    elif e['kind'] == 'visit':
                        column = 'returns' if e.get('reason') == 'resume' else 'visits'
                        db.execute(f'UPDATE usage_daily SET {column}={column}+1 WHERE day=? AND actor=? AND server=?', (day, actor, server))
                    else:
                        db.execute('''INSERT INTO usage_features VALUES(?,?,?,?,?,1) ON CONFLICT(day,actor,server,feature,result)
                            DO UPDATE SET uses=uses+1''', (day, actor, server, e['feature'], e['result']))
        return accepted

    def prune(self, now=None, execute=False):
        cutoff = int(time.time() if now is None else now)-90*86400
        with self.connect() as db:
            result = {'raw_events': db.execute('SELECT count(*) FROM usage_events WHERE received_at<?', (cutoff,)).fetchone()[0],
                      'minute_keys': db.execute('SELECT count(*) FROM usage_minutes WHERE minute<?', (cutoff//60,)).fetchone()[0]}
            if execute:
                db.execute('DELETE FROM usage_events WHERE received_at<?', (cutoff,))
                db.execute('DELETE FROM usage_minutes WHERE minute<?', (cutoff//60,))
        return {**result, 'executed': execute, 'daily_hourly_people_and_features_retained': True}

    def overview(self, start, end, server='all', now=None):
        now = int(time.time() if now is None else now)
        today = datetime.fromtimestamp(now, BJ).date()
        with self.connect() as db:
            db.execute('BEGIN')
            daily_rows = db.execute("""SELECT d.day,p.kind,
                COUNT(DISTINCT CASE WHEN visits+returns>0 THEN d.actor END) AS visitors,
                COUNT(DISTINCT CASE WHEN active_minutes>0 THEN d.actor END) AS active,
                COUNT(DISTINCT CASE WHEN visits+returns>0 AND date(first_seen,'unixepoch','+8 hours')=day THEN d.actor END) AS fresh,
                COUNT(DISTINCT CASE WHEN visits+returns>0 AND date(first_seen,'unixepoch','+8 hours')<day THEN d.actor END) AS revisitors,
                SUM(visits) AS opens,SUM(returns) AS resumes,SUM(active_minutes) AS minutes
                FROM usage_daily d JOIN usage_people p USING(actor)
                WHERE day BETWEEN ? AND ? AND server=? GROUP BY d.day,p.kind ORDER BY d.day,p.kind""", (start,end,server)).fetchall()
            hours = db.execute("""SELECT (CAST(strftime('%w',day) AS INTEGER)+6)%7 AS weekday,hour,p.kind,SUM(active_minutes) AS minutes
                FROM usage_hourly h JOIN usage_people p USING(actor)
                WHERE day BETWEEN ? AND ? AND server=? GROUP BY weekday,hour,p.kind""", (start,end,server)).fetchall()
            features = db.execute("""SELECT feature,result,p.kind,SUM(uses) AS uses,COUNT(DISTINCT actor) AS people
                FROM usage_features f JOIN usage_people p USING(actor)
                WHERE day BETWEEN ? AND ? AND server=? GROUP BY feature,result,p.kind ORDER BY feature,result,p.kind""", (start,end,server)).fetchall()
            recent = db.execute("""SELECT p.kind,
                COUNT(DISTINCT CASE WHEN day>=? THEN actor END) AS dau,
                COUNT(DISTINCT CASE WHEN day>=? THEN actor END) AS wau,
                COUNT(DISTINCT actor) AS mau FROM usage_daily d JOIN usage_people p USING(actor)
                WHERE day BETWEEN ? AND ? AND server=? AND active_minutes>0 GROUP BY p.kind""",
                (today.isoformat(),(today-timedelta(days=6)).isoformat(),(today-timedelta(days=29)).isoformat(),today.isoformat(),server)).fetchall()
            proportions = [dict(r) for r in db.execute("""SELECT server,SUM(visits) AS opens,SUM(returns) AS resumes,SUM(active_minutes) AS active_minutes
                FROM usage_daily WHERE day BETWEEN ? AND ? AND server IN ('cn','global') GROUP BY server""", (start,end))]
        # Only compact aggregates leave SQLite; no full identity/day history is loaded into Python.
        daily = {}
        zero = {'visitors':0,'active':0,'new':0,'returning':0,'opens':0,'resumes':0,'minutes':0}
        for r in daily_rows:
            group = daily.setdefault(r['day'], {'day':r['day'], 'account':dict(zero), 'guest':dict(zero)})
            group[r['kind']] = {({'fresh':'new','revisitors':'returning'}.get(k,k)):r[k] for k in ('visitors','active','fresh','revisitors','opens','resumes','minutes')}
        windows = {kind:{'dau':0,'wau':0,'mau':0} for kind in ('account','guest')}
        for r in recent:windows[r['kind']]={k:r[k] for k in ('dau','wau','mau')}
        heatmap = {kind:[[0]*24 for _ in range(7)] for kind in ('account','guest')}
        for r in hours:heatmap[r['kind']][r['weekday']][r['hour']]=r['minutes']
        groups = {}
        for r in features:
            group=groups.setdefault((r['feature'],r['result']), {'feature':r['feature'],'result':r['result'],
                'account':{'uses':0,'people':0},'guest':{'uses':0,'people':0}})
            group[r['kind']]={k:r[k] for k in ('uses','people')}
        return {'timezone':'Asia/Shanghai','start':start,'end':end,'server':server,'rolling_windows_as_of':today.isoformat(),
                'windows':windows,'daily':list(daily.values()),'heatmap':heatmap,'server_proportions':proportions,'features':list(groups.values())}

    def account_activity(self, uid, start, end, server='all', offset=0):
        actor='a:'+uid
        with self.connect() as db:
            db.execute('BEGIN')
            seen=db.execute('SELECT first_seen,last_visit,last_interaction FROM usage_people WHERE actor=?',(actor,)).fetchone()
            summary=dict(db.execute('''SELECT COUNT(*) AS observed_days,
                COALESCE(SUM(visits),0) AS opens,COALESCE(SUM(returns),0) AS resumes,
                COALESCE(SUM(active_minutes),0) AS active_minutes,
                COALESCE(SUM(active_minutes>0),0) AS active_days
                FROM usage_daily WHERE actor=? AND server=? AND day BETWEEN ? AND ?''',(actor,server,start,end)).fetchone())
            rows=[dict(r) for r in db.execute('''SELECT day,visits AS opens,returns AS resumes,active_minutes
                FROM usage_daily WHERE actor=? AND server=? AND day BETWEEN ? AND ? ORDER BY day DESC LIMIT 10 OFFSET ?''',
                (actor,server,start,end,offset))]
            for row in rows:
                row['features']=[dict(r) for r in db.execute('''SELECT feature,result,uses FROM usage_features
                    WHERE actor=? AND server=? AND day=? ORDER BY feature,result''',(actor,server,row['day']))]
        return {'first_seen':seen['first_seen'] if seen else None,'last_visit':seen['last_visit'] if seen else None,
                'last_interaction':seen['last_interaction'] if seen else None,'summary':summary,
                'items':rows,'total':summary['observed_days'],'offset':offset,'page_size':10,
                'start':start,'end':end,'server':server,'timezone':'Asia/Shanghai'}



class Bootstrap(BaseModel):
    model_config = ConfigDict(extra='forbid')
    visitor_id: str = Field(pattern=r'^[a-f0-9]{32}$')
    session_id: str = Field(pattern=r'^[a-f0-9]{32}$')


class Event(BaseModel):
    model_config = ConfigDict(extra='forbid')
    id: str = Field(pattern=r'^[a-f0-9]{32}$')
    kind: Literal['visit','active','feature']
    page: Literal['home','submissions','feedback','leaderboard']
    server: Literal['cn','global']
    feature: str = Field(default='', max_length=40)
    result: str = Field(default='', max_length=12)
    reason: Literal['','open','resume'] = ''


class Batch(BaseModel):
    model_config = ConfigDict(extra='forbid')
    events: list[Event] = Field(min_length=1, max_length=20)


def install(app, accounts, root, user, session):
    usage = app.state.usage
    def identity(request, visitor):
        current = session(request, False)
        if current and current['user_id']:
            owner = user(request)
            return 'a:'+owner['id']
        return 'v:'+visitor

    @app.post('/api/usage/session')
    def bootstrap(body: Bootstrap, request: Request):
        actor = identity(request, body.visitor_id)
        return {'token':usage.token(body.visitor_id, body.session_id, actor), 'expires_in':1800,
                'identity':hashlib.sha256(actor.encode()).hexdigest(), 'timezone':'Asia/Shanghai'}

    def token_context(request):
        token = request.headers.get('x-usage-token','')
        # Decode only to discover the anonymous visitor. verify() authenticates all fields.
        try:
            raw=token.split('.')[0];visitor=json.loads(base64.urlsafe_b64decode(raw+'='*(-len(raw)%4)))[0]
            if not isinstance(visitor,str) or len(visitor)!=32:
                raise ValueError()
        except (ValueError, TypeError, IndexError, KeyError, UnicodeError):
            raise HTTPException(409,'统计会话需要初始化') from None
        actor = identity(request, visitor)
        _, session_id = usage.verify(token, actor)
        return actor, session_id

    @app.post('/api/usage/events')
    def collect(body: Batch, request: Request):
        actor, session_id = token_context(request)
        for e in body.events:
            if e.server=='global' and e.page!='home':
                raise HTTPException(422,'该页面无国际服统计入口')
            if e.kind=='feature':
                if e.feature not in FEATURES[:4] or e.result not in RESULTS or e.page!='home' or e.reason:
                    raise HTTPException(422,'功能事件无效')
            elif e.feature or e.result or (e.kind=='visit' and not e.reason) or (e.kind=='active' and e.reason):
                raise HTTPException(422,'事件字段不匹配')
        try:
            accepted = usage.append(actor, session_id, [e.model_dump() for e in body.events])
        except sqlite3.Error:
            # Statistics are best-effort; never hold up account/score writes.
            raise HTTPException(503,'统计暂时不可用') from None
        return {'accepted':accepted}

    def business(request, owner, feature, operation):
        try:
            actor, session_id = token_context(request)
            if actor != 'a:'+owner['id']:
                return
            usage.append(actor,session_id,[{'id':hashlib.sha256((feature+':'+operation).encode()).hexdigest()[:32],
                'kind':'feature','page':'submissions' if feature=='submission_submit' else 'feedback','server':'cn',
                'feature':feature,'result':'success'}])
        except (HTTPException, ValueError, sqlite3.Error):
            pass
    app.state.record_usage = business

    def administrator(request):
        owner=user(request)
        if request.headers.get('x-account-id')!=owner['id']:
            raise HTTPException(401,'账号已切换，请刷新')
        if not owner['verified'] or owner['role']!='superadmin':
            raise HTTPException(403,'仅超级管理员可查看使用统计')
        return owner

    @app.get('/admin-usage')
    def page(request: Request):
        # API does the authenticated gate; the HTML contains no statistics.
        return HTMLResponse((root/'usage.html').read_text(encoding='utf-8'))

    def date_range(start, end):
        today=datetime.now(BJ).date()
        try:
            first=datetime.strptime(start,'%Y-%m-%d').date() if start else today-timedelta(days=29)
            last=datetime.strptime(end,'%Y-%m-%d').date() if end else today
            if not 0 <= (last-first).days <= 365 or last>today:
                raise ValueError()
        except ValueError:
            raise HTTPException(422,'日期范围应为不晚于今天的1–366天') from None
        return first,last

    @app.get('/api/admin/usage')
    def overview(request: Request, start: str='', end: str='', server: Literal['all','cn','global']='all'):
        administrator(request)
        first,last=date_range(start,end)
        result=usage.overview(first.isoformat(),last.isoformat(),server)
        with accounts.connect() as db:
            result['registrations']={r[0]:r[1] for r in db.execute('''SELECT date(created_at,'unixepoch','+8 hours'),count(*)
                FROM users WHERE date(created_at,'unixepoch','+8 hours') BETWEEN ? AND ? GROUP BY 1''',(first.isoformat(),last.isoformat()))}
        return result

    @app.get('/api/admin/usage/accounts')
    def account_times(request: Request, offset: int=0, q: str=''):
        administrator(request)
        if offset<0 or len(q)>100:
            raise HTTPException(422,'查询参数无效')
        term='%'+q.replace('\\','\\\\').replace('%','\\%').replace('_','\\_')+'%'
        with accounts.connect() as db:
            total=db.execute("SELECT count(*) FROM users WHERE email LIKE ? ESCAPE '\\'",(term,)).fetchone()[0]
            items=[dict(r) for r in db.execute("SELECT id,email,created_at FROM users WHERE email LIKE ? ESCAPE '\\' ORDER BY created_at DESC,id LIMIT 50 OFFSET ?",(term,offset))]
        with usage.connect() as db:
            for item in items:
                row=db.execute('SELECT first_seen,last_visit,last_interaction FROM usage_people WHERE actor=?',('a:'+item['id'],)).fetchone()
                item.update(dict(row) if row else {'first_seen':None,'last_visit':None,'last_interaction':None})
        return {'items':items,'total':total,'timezone':'Asia/Shanghai'}

    @app.get('/api/admin/usage/accounts/{uid}')
    def account_detail(uid: str, request: Request, start: str='', end: str='', server: Literal['all','cn','global']='all', offset: int=0):
        administrator(request)
        if offset<0:raise HTTPException(422,'分页参数无效')
        first,last=date_range(start,end)
        with accounts.connect() as db:
            item=db.execute('''SELECT u.id,u.email,u.created_at,ls.last_login FROM users u
                LEFT JOIN account_login_stats ls ON ls.user_id=u.id WHERE u.id=?''',(uid,)).fetchone()
        if not item:raise HTTPException(404,'账号不存在')
        return {'account':dict(item),**usage.account_activity(uid,first.isoformat(),last.isoformat(),server,offset)}
