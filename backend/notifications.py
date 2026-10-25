"""Per-account unread cursors. Events contain references, never message bodies."""
from typing import Literal
from fastapi import HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field, StrictInt

TABLES = ('notification_schema', 'notification_events', 'notification_reads')
Channel = Literal['review', 'submissions', 'feedback_admin', 'feedback']


def state(db):
    present = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    owned = present.intersection(TABLES)
    if not owned:
        return {'notification_schema': 0, 'notification_counts': {}}
    if owned != set(TABLES):
        raise ValueError('未读标记表不完整，保留现场')
    rows = db.execute('SELECT version FROM notification_schema').fetchall()
    if len(rows) != 1 or rows[0][0] != 1:
        raise ValueError('未读标记版本不兼容')
    return {'notification_schema': 1, 'notification_counts': {
        n: db.execute('SELECT count(*) FROM '+n).fetchone()[0] for n in TABLES[1:]}}


def migrate(db):
    if state(db)['notification_schema'] == 1:
        return
    for sql in (
        'CREATE TABLE notification_schema(version INTEGER PRIMARY KEY)',
        '''CREATE TABLE notification_events(id INTEGER PRIMARY KEY AUTOINCREMENT,
            channel TEXT NOT NULL CHECK(channel IN ('review','submissions','feedback_admin','feedback')),
            item_id TEXT NOT NULL, owner_id TEXT NOT NULL REFERENCES users(id),
            actor_id TEXT NOT NULL REFERENCES users(id), revision INTEGER NOT NULL CHECK(revision>0),
            UNIQUE(channel,item_id,revision))''',
        '''CREATE TABLE notification_reads(user_id TEXT NOT NULL REFERENCES users(id),
            channel TEXT NOT NULL, item_id TEXT NOT NULL, event_id INTEGER NOT NULL,
            PRIMARY KEY(user_id,channel,item_id))''',
        'CREATE INDEX notification_channel_item ON notification_events(channel,item_id,id)',
        'CREATE INDEX notification_owner ON notification_events(owner_id,channel,id)',
    ):
        db.execute(sql)
    db.execute('INSERT INTO notification_schema VALUES(1)')


def emit(db, channel, item_id, owner_id, actor_id, revision):
    db.execute('INSERT INTO notification_events(channel,item_id,owner_id,actor_id,revision) VALUES(?,?,?,?,?)',
               (channel, item_id, owner_id, actor_id, revision))


def channels(user, feedback):
    result = ['submissions']
    if user['role'] in ('admin', 'superadmin'):
        result.append('review')
    if feedback:
        result.append('feedback')
        if user['role'] == 'superadmin':
            result.append('feedback_admin')
    return result


def unread(db, user, channel, item_id=None, revision=None):
    """Return latest unseen relevant event per item; handled review work stops alerting."""
    source = 'submissions' if channel in ('review', 'submissions') else 'feedback_tickets'
    conditions = ['e.channel=?', 'e.actor_id!=?', 'e.id>COALESCE(r.event_id,0)']
    args = [user['id'], channel, user['id']]
    if channel in ('submissions', 'feedback'):
        conditions.append('e.owner_id=?'); args.append(user['id'])
    if channel == 'review':
        conditions.append("s.status='pending'")
    if item_id is not None:
        conditions.append('e.item_id=?'); args.append(item_id)
    if revision is not None:
        conditions.append('e.revision<=?'); args.append(revision)
    return {r[0]: r[1] for r in db.execute(
        f'''SELECT e.item_id,MAX(e.id) FROM notification_events e
            JOIN {source} s ON s.id=e.item_id
            LEFT JOIN notification_reads r ON r.user_id=? AND r.channel=e.channel AND r.item_id=e.item_id
            WHERE {' AND '.join(conditions)} GROUP BY e.item_id''', args)}


def decorate(db, app, user, items, channel):
    if not app.state.notifications:
        return
    events = unread(db, user, channel)
    for item in items:
        item['unread'] = item['id'] in events


def cursors(db, app, user, item):
    if not app.state.notifications:
        return
    source = ('feedback', 'feedback_admin') if 'title' in item else ('submissions', 'review')
    item['notification_cursors'] = {c: unread(db, user, c, item['id'], item['revision']).get(item['id'], 0)
        for c in source if c in channels(user, app.state.feedback)}


class Read(BaseModel):
    model_config = ConfigDict(extra='forbid')
    channel: Channel
    item_id: str = Field(pattern=r'^[a-f0-9]{32}$')
    event_id: StrictInt = Field(gt=0)


def install(app, store, user):
    def actor(request, db=None):
        current = user(request)
        if request.headers.get('x-account-id') != current['id']:
            raise HTTPException(401, '账号已切换，请刷新')
        if not current['verified']:
            raise HTTPException(403, '请先验证邮箱')
        if db is not None:
            app.state.require_active_session(request, db)
            # Re-evaluate role inside the same transaction, including singleton owner.
            from backend.roles import effective_role
            row = db.execute('SELECT role FROM users WHERE id=?', (current['id'],)).fetchone()
            current = {**current, 'role': effective_role(db, current['id'], row['role'])}
        return current

    @app.get('/api/notifications')
    def summary(request: Request):
        with store.connect() as db:
            db.execute('BEGIN')
            current = actor(request, db)
            items = {c: list(unread(db, current, c)) for c in channels(current, app.state.feedback)}
            result = {c: len(ids) for c, ids in items.items()}
            pending = db.execute("SELECT count(*) FROM feedback_tickets WHERE status='pending'").fetchone()[0] if app.state.feedback and current['role']=='superadmin' else None
        return {'user_id': current['id'], 'role': current['role'], 'counts': result, 'items': items, 'feedback_pending': pending}

    @app.post('/api/notifications/read')
    def read(body: Read, request: Request):
        with store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            current = actor(request, db)
            if body.channel not in channels(current, app.state.feedback):
                raise HTTPException(403, '无此提醒的权限')
            event = db.execute('SELECT * FROM notification_events WHERE id=? AND channel=? AND item_id=?',
                               (body.event_id, body.channel, body.item_id)).fetchone()
            if not event or (body.channel in ('submissions', 'feedback') and event['owner_id'] != current['id']):
                raise HTTPException(404, '提醒不存在')
            db.execute('''INSERT INTO notification_reads VALUES(?,?,?,?)
                ON CONFLICT(user_id,channel,item_id) DO UPDATE SET event_id=MAX(event_id,excluded.event_id)''',
                (current['id'], body.channel, body.item_id, body.event_id))
        return {'read': True}
