"""Opt-in local contribution ledger. Hooks share review/publication transactions."""
import json
import re
import time
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictInt
from backend.submissions import identity, packed

CST = timezone(timedelta(hours=8))


class Quality(BaseModel):
    model_config = ConfigDict(extra='forbid')
    completeness: StrictInt = Field(ge=0, le=3)
    evidence: StrictInt = Field(ge=0, le=4)
    value: StrictInt = Field(ge=0, le=3)
    reason: str = Field(min_length=1, max_length=1000)


class Rating(BaseModel):
    model_config = ConfigDict(extra='forbid')
    revision: StrictInt = Field(ge=1)
    quality: Quality


class Preferences(BaseModel):
    model_config = ConfigDict(extra='forbid')
    revision: StrictInt = Field(ge=0)
    nickname: str = Field(max_length=30)
    anonymous: StrictBool


def month(now=None):
    return datetime.fromtimestamp(time.time() if now is None else now, CST).strftime('%Y-%m')


def available(db):
    return bool(db.execute("SELECT 1 FROM sqlite_master WHERE name='contribution_rules'").fetchone())


def migrate(db):
    if available(db):
        if db.execute('SELECT version FROM contribution_rules').fetchone()[0] != 1:
            raise ValueError('不支持的贡献规则版本')
        return
    for sql in (
        'CREATE TABLE contribution_rules(version INTEGER PRIMARY KEY, enabled_at INTEGER NOT NULL)',
        '''CREATE TABLE contributions(id INTEGER PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id),
            target_key TEXT NOT NULL, quality TEXT, quality_points INTEGER NOT NULL DEFAULT 0,
            quality_month TEXT, quality_sid TEXT, bonus INTEGER NOT NULL DEFAULT 0, bonus_month TEXT,
            UNIQUE(user_id,target_key))''',
        '''CREATE TABLE contribution_sources(submission_id TEXT PRIMARY KEY REFERENCES submissions(id),
            contribution_id INTEGER REFERENCES contributions(id))''',
        '''CREATE TABLE contribution_events(id INTEGER PRIMARY KEY, contribution_id INTEGER NOT NULL REFERENCES contributions(id),
            submission_id TEXT, actor_id TEXT, action TEXT NOT NULL, snapshot TEXT NOT NULL, created_at INTEGER NOT NULL)''',
        '''CREATE TABLE contribution_preferences(user_id TEXT PRIMARY KEY REFERENCES users(id),
            nickname TEXT NOT NULL, anonymous INTEGER NOT NULL, revision INTEGER NOT NULL)''',
    ):
        db.execute(sql)
    db.execute('INSERT INTO contribution_rules VALUES(1,?)', (int(time.time()),))
    # No historical enrolment: even drafts created before activation remain excluded.


def enroll(db, sid):
    db.execute('INSERT INTO contribution_sources VALUES(?,NULL)', (sid,))


def eligible(db, sid):
    return available(db) and bool(db.execute('SELECT 1 FROM contribution_sources WHERE submission_id=?', (sid,)).fetchone())


def bind(db, row):
    source = db.execute('SELECT * FROM contribution_sources WHERE submission_id=?', (row['id'],)).fetchone()
    if source is None:
        return None
    payload = json.loads(row['accepted_payload'] or row['payload'])
    if not all(payload.get(k) for k in ('big', 'small', 'car')):
        raise HTTPException(422, '计贡献前请要求投稿人补全地图和车辆，确保同目标去重')
    key = identity(payload) or packed([payload[k] for k in ('big','small','zone','tier','car','stars','route')])
    if source['contribution_id'] is not None:
        item = db.execute('SELECT * FROM contributions WHERE id=?', (source['contribution_id'],)).fetchone()
        if item['target_key'] != key:
            raise HTTPException(409, '已结算贡献不能改成其他目标，请新建投稿；原贡献保留审计记录')
        return item['id']
    db.execute('INSERT OR IGNORE INTO contributions(user_id,target_key) VALUES(?,?)', (row['owner_id'], key))
    cid = db.execute('SELECT id FROM contributions WHERE user_id=? AND target_key=?', (row['owner_id'], key)).fetchone()[0]
    db.execute('UPDATE contribution_sources SET contribution_id=? WHERE submission_id=?', (cid, row['id']))
    return cid


def audit(db, cid, sid, actor, action, reason=''):
    item = dict(db.execute('SELECT * FROM contributions WHERE id=?', (cid,)).fetchone())
    item['reason'] = reason
    db.execute('INSERT INTO contribution_events(contribution_id,submission_id,actor_id,action,snapshot,created_at) VALUES(?,?,?,?,?,?)',
               (cid, sid, actor, action, packed(item), int(time.time())))


def check_reviewer(db, row, actor):
    if eligible(db, row['id']) and row['owner_id'] == actor:
        raise HTTPException(403, '排行榜投稿不能由本人审核或评分，请交由其他管理员')


def settle_review(db, sid, actor, quality):
    row = db.execute('SELECT * FROM submissions WHERE id=?', (sid,)).fetchone()
    if not eligible(db, sid):
        if quality is not None:
            raise HTTPException(422, '历史投稿不参与新规则评分')
        return
    if row['status'] not in ('accepted', 'ignored'):
        source = db.execute('SELECT contribution_id FROM contribution_sources WHERE submission_id=?', (sid,)).fetchone()
        if source[0] is not None:
            item = db.execute('SELECT * FROM contributions WHERE id=?', (source[0],)).fetchone()
            if item['quality_sid'] == sid:
                db.execute('UPDATE contributions SET quality_points=0 WHERE id=?', (item['id'],))
                audit(db, item['id'], sid, actor, 'quality_suspended', row['decision_reason'])
        return
    if quality is None:
        return
    cid = bind(db, row)
    if not quality.reason.strip():
        raise HTTPException(422, '请填写质量评分依据')
    points = quality.completeness + quality.evidence + quality.value
    # A new duplicate with zero value must not earn completeness/evidence points.
    if quality.value == 0 and points != 0:
        raise HTTPException(422, '没有新增参考价值时总质量分应为0，请将三项均设为0')
    db.execute('UPDATE contributions SET quality=?,quality_points=?,quality_month=COALESCE(quality_month,?),quality_sid=? WHERE id=?',
               (packed(quality.model_dump()), points, month(), sid, cid))
    audit(db, cid, sid, actor, 'quality_set', quality.reason.strip())


def publication(db, sid, actor):
    if not eligible(db, sid):
        return
    row = db.execute('SELECT * FROM submissions WHERE id=?', (sid,)).fetchone()
    cid = bind(db, row)
    active = db.execute("SELECT 1 FROM contribution_sources s JOIN write_receipts r ON r.submission_id=s.submission_id WHERE s.contribution_id=? AND r.state='applied'", (cid,)).fetchone()
    old = db.execute('SELECT bonus FROM contributions WHERE id=?', (cid,)).fetchone()[0]
    bonus = 10 if active else 0
    if bonus == old:
        return
    db.execute('UPDATE contributions SET bonus=?,bonus_month=CASE WHEN ?=10 THEN COALESCE(bonus_month,?) ELSE bonus_month END WHERE id=?', (bonus, bonus, month(), cid))
    audit(db, cid, sid, actor, 'adopted' if bonus else 'adoption_revoked')


def info(db, sid):
    source = db.execute('SELECT contribution_id FROM contribution_sources WHERE submission_id=?', (sid,)).fetchone()
    if source is None:
        return {'eligible': False}
    item = db.execute('SELECT * FROM contributions WHERE id=?', (source[0],)).fetchone() if source[0] else None
    events = [dict(r) for r in db.execute('SELECT action,snapshot,created_at FROM contribution_events WHERE contribution_id=? ORDER BY id', (source[0],))] if item else []
    return {'eligible': True, 'contribution': dict(item) if item else None, 'events': events}


def ranked(db, period):
    rows = db.execute('''SELECT c.*,p.nickname,COALESCE(p.anonymous,1) AS anonymous FROM contributions c
        JOIN users u ON u.id=c.user_id LEFT JOIN contribution_preferences p ON p.user_id=u.id
        LEFT JOIN account_controls a ON a.user_id=u.id WHERE COALESCE(a.disabled,0)=0''').fetchall()
    totals = {}
    for r in rows:
        q = r['quality_points'] if period == 'all' or r['quality_month'] == period else 0
        b = r['bonus'] if period == 'all' or r['bonus_month'] == period else 0
        if q + b <= 0:
            continue
        result = totals.setdefault(r['user_id'], {'nickname': '匿名贡献者' if r['anonymous'] else r['nickname'],
                'quality': 0, 'adoption': 0, 'effective_count': 0, 'adopted_count': 0})
        result['quality'] += q; result['adoption'] += b
        result['effective_count'] += 1; result['adopted_count'] += int(b > 0)
    ordered = sorted(totals.items(), key=lambda pair: (-(pair[1]['quality'] + pair[1]['adoption']), pair[0]))
    previous = None; rank = 0
    for index, (uid, item) in enumerate(ordered, 1):
        item['total'] = item['quality'] + item['adoption']
        if item['total'] != previous:
            rank = index; previous = item['total']
        item['rank'] = rank
    return ordered


def install(app, store, root, user):
    def actor(request, admin=False):
        current = user(request)
        if request.headers.get('x-account-id') != current['id']:
            raise HTTPException(401, '账号已变化，请刷新')
        if not current['verified'] or (admin and current['role'] not in ('admin', 'superadmin')):
            raise HTTPException(403, '没有操作权限')
        return current

    def period_value(period):
        if period == 'month': return month()
        if period != 'all' and not re.fullmatch(r'\d{4}-(0[1-9]|1[0-2])', period):
            raise HTTPException(422, '月份格式应为YYYY-MM')
        return period

    @app.get('/leaderboard')
    def page():
        if getattr(getattr(app.state,'score_versions',None),'production',False):
            return HTMLResponse((root/'leaderboard.html').read_text(encoding='utf-8').replace('独立本地验收环境 · ',''))
        return FileResponse(root/'leaderboard.html')

    @app.get('/api/contributions/leaderboard')
    def leaderboard(period: str = 'month'):
        period = period_value(period)
        with store.connect() as db:
            entries = ranked(db, period)
            cutoff = entries[49][1]['total'] if len(entries) >= 50 else 0
            result = [item for _, item in entries if item['total'] >= cutoff]
            enabled = db.execute('SELECT enabled_at FROM contribution_rules').fetchone()[0]
        return {'period': period, 'items': result, 'enabled_at': enabled, 'as_of': int(time.time())}

    @app.get('/api/contributions/me')
    def mine(request: Request, period: str = 'month'):
        current = actor(request); period = period_value(period)
        with store.connect() as db:
            preference = db.execute('SELECT * FROM contribution_preferences WHERE user_id=?', (current['id'],)).fetchone()
            rows = [dict(r) for r in db.execute('SELECT * FROM contributions WHERE user_id=? ORDER BY id DESC', (current['id'],))]
            for item in rows:
                item['sources'] = [dict(r) for r in db.execute('''SELECT s.id,s.status,s.payload,r.state AS publication_state FROM contribution_sources cs
                    JOIN submissions s ON s.id=cs.submission_id LEFT JOIN write_receipts r ON r.submission_id=s.id WHERE cs.contribution_id=?''', (item['id'],))]
                item['events'] = [dict(r) for r in db.execute('SELECT action,snapshot,created_at FROM contribution_events WHERE contribution_id=? ORDER BY id', (item['id'],))]
            positions = {p: next((item for uid, item in ranked(db, p) if uid == current['id']), None) for p in {'all', month(), period}}
        return {'preference': dict(preference) if preference else {'nickname': '', 'anonymous': True, 'revision': 0}, 'positions': positions, 'items': rows}

    @app.put('/api/contributions/preferences')
    def preferences(body: Preferences, request: Request):
        current = actor(request)
        nickname = body.nickname.strip()
        if not body.anonymous and (not nickname or '@' in nickname or any(ord(c) < 32 for c in nickname)):
            raise HTTPException(422, '公开昵称不能为空，也不能包含邮箱或控制字符')
        with store.connect() as db:
            db.execute('BEGIN IMMEDIATE'); app.state.require_active_session(request, db)
            old = db.execute('SELECT revision FROM contribution_preferences WHERE user_id=?', (current['id'],)).fetchone()
            if body.revision != (old[0] if old else 0): raise HTTPException(409, '设置已变化，请刷新')
            db.execute('INSERT INTO contribution_preferences VALUES(?,?,?,?) ON CONFLICT(user_id) DO UPDATE SET nickname=excluded.nickname,anonymous=excluded.anonymous,revision=excluded.revision',
                       (current['id'], nickname, int(body.anonymous), body.revision + 1))
        return {'revision': body.revision + 1}

    @app.post('/api/admin/contributions/{sid}/rating')
    def rating(sid: str, body: Rating, request: Request):
        current = actor(request, True)
        with store.connect() as db:
            db.execute('BEGIN IMMEDIATE'); app.state.require_active_session(request, db)
            row = db.execute('SELECT * FROM submissions WHERE id=?', (sid,)).fetchone()
            if not row: raise HTTPException(404, '投稿不存在')
            check_reviewer(db, row, current['id'])
            if row['revision'] != body.revision: raise HTTPException(409, '投稿已变化，请刷新')
            if row['status'] not in ('accepted', 'ignored'): raise HTTPException(409, '请先完成审核')
            # Keep accepted payload and receipts unchanged. Advancing revision invalidates stale prepared batches.
            if hasattr(app.state, 'score_versions'): app.state.score_versions.idle(db)
            settle_review(db, sid, current['id'], body.quality)
            db.execute('UPDATE submissions SET revision=revision+1 WHERE id=?', (sid,))
        return {'revision': body.revision + 1}
