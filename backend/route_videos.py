"""Local-only route video references, independent of score revisions."""
import json
import re
import sqlite3
from contextlib import closing
from time import monotonic
from typing import Literal
from urllib.error import URLError
from urllib.parse import parse_qs, urlencode, urljoin, urlsplit
from urllib.request import HTTPRedirectHandler, Request as URLRequest, build_opener

from fastapi import HTTPException, Request
from pydantic import BaseModel, Field

VIDEO_ID = r'(?:BV[0-9A-Za-z]{10}|av[1-9][0-9]{0,17})'
HOSTS = {'b23.tv', 'www.bilibili.com', 'bilibili.com', 'm.bilibili.com'}
TIERS = Literal['', '理论', '高手', '普通', '自动']


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def request(url, timeout):
    return build_opener(NoRedirect()).open(
        URLRequest(url, headers={'User-Agent': 'Mozilla/5.0', 'Accept': 'application/json,*/*'}), timeout=timeout)


def allowed(url):
    parts = urlsplit(url)
    if parts.scheme != 'https' or parts.netloc.lower() not in HOSTS:
        raise ValueError('请使用 B 站 HTTPS 视频链接或 b23.tv 分享链接')
    return parts


def normalize(raw):
    raw = raw.strip()
    if re.fullmatch(VIDEO_ID, raw):
        raw = f'https://www.bilibili.com/video/{raw}/'
    urls = re.findall(r'https://[^\s<>「」【】（）。，；]+', raw)
    if len(urls) != 1:
        raise ValueError('请粘贴一条 B 站视频链接或 BV/AV 号')
    url = urls[0].rstrip('),.;')
    deadline = monotonic() + 5
    position = {}
    for _ in range(4):
        parts = allowed(url)
        query = parse_qs(parts.query, keep_blank_values=True, max_num_fields=80)
        for key in ('p', 't'):
            if key not in query or key in position:
                continue
            values = query[key]
            if len(values) != 1 or not re.fullmatch(r'[0-9]{1,6}', values[0]):
                raise ValueError('分 P 或起点格式无效，请核对链接')
            position[key] = int(values[0])
        if parts.hostname != 'b23.tv':
            break
        remaining = deadline - monotonic()
        if remaining <= 0:
            raise ValueError('短链解析超时，请粘贴 B 站视频页地址')
        try:
            with request(url, remaining):
                raise ValueError('短链未跳转到视频页，请粘贴长链接')
        except URLError as error:
            location = getattr(error, 'headers', {}).get('Location') if getattr(error, 'headers', None) else None
            if getattr(error, 'code', None) not in (301, 302, 303, 307, 308) or not location:
                raise ValueError('短链暂时无法解析，请粘贴 B 站视频页地址') from error
            url = urljoin(url, location)
            error.close()
        except OSError as error:
            raise ValueError('短链暂时无法解析，请粘贴 B 站视频页地址') from error
    match = re.fullmatch(rf'/video/({VIDEO_ID})(?:/p([1-9][0-9]{{0,5}}))?/?', parts.path)
    if parts.hostname == 'b23.tv' or not match:
        raise ValueError('链接没有指向可识别的 B 站视频页')
    part = int(match[2]) if match[2] else 1
    part = position.get('p', part)
    if part < 1 or (match[2] and part != int(match[2])):
        raise ValueError('链接中的分 P 不一致，请核对')
    return match[1], part, position.get('t', 0)


def video_url(video_id, part, start):
    params = {}
    if part > 1:
        params['p'] = part
    if start:
        params['t'] = start
    return f'https://www.bilibili.com/video/{video_id}/' + ('?' + urlencode(params) if params else '')


def metadata(video_id, part):
    # Public metadata is best effort. A typed title remains usable when Bilibili limits access.
    query = {'bvid': video_id} if video_id.startswith('BV') else {'aid': video_id[2:]}
    try:
        with request('https://api.bilibili.com/x/web-interface/view?' + urlencode(query), 4) as response:
            raw = response.read(512 * 1024 + 1)
        if len(raw) > 512 * 1024:
            return '', ''
        result = json.loads(raw)
        if result.get('code') != 0:
            return '', ''
        data = result['data']
        if part == 1:
            return str(data['title'])[:200], ''
        page = next((page for page in data.get('pages', []) if page['page'] == part), None)
        return str(data['title'])[:200], str(page.get('part', ''))[:200] if page else ''
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return '', ''


class Paste(BaseModel):
    raw: str = Field(min_length=1, max_length=2500)


class Target(BaseModel):
    server: Literal['cn', 'global']
    big: str = Field(min_length=1, max_length=80)
    small: str = Field(min_length=1, max_length=80)
    car: str = Field(min_length=1, max_length=80)


class Binding(Target):
    video_id: str = Field(pattern=f'^{VIDEO_ID}$')
    part: int = Field(ge=1, le=999999)
    start: int = Field(ge=0, le=999999)
    title: str = Field(min_length=1, max_length=200)
    tier: TIERS = ''
    zone: Literal['', '四区', '五区'] = ''
    lap: float | None = Field(default=None, gt=0, le=3600)


class Visibility(Target):
    id: int = Field(gt=0)
    active: bool


def initialize_store(db):
    db.execute("""CREATE TABLE IF NOT EXISTS route_videos (
      id INTEGER PRIMARY KEY, server TEXT, big TEXT, small TEXT, car TEXT,
      video_id TEXT, part INTEGER, start INTEGER, title TEXT, tier TEXT, lap REAL,
      active INTEGER NOT NULL DEFAULT 1, editor TEXT, updated_at TEXT,
      UNIQUE(server,big,small,car,video_id,part,start))""")
    if not any(row[1] == 'zone' for row in db.execute('PRAGMA table_info(route_videos)')):
        db.execute("ALTER TABLE route_videos ADD COLUMN zone TEXT NOT NULL DEFAULT ''")

def install(app, path, user, source, *, initialize=True):
    def connect():
        db = sqlite3.connect(path)
        db.row_factory = sqlite3.Row
        return db

    with closing(connect()) as db, db:
        if initialize:
            initialize_store(db)
        elif [row[0] for row in db.execute('SELECT version FROM route_video_schema')] != [1]:
            raise ValueError('跑法参考数据库版本不兼容')

    def admin(request):
        actor = user(request)
        if not actor['verified'] or actor['role'] not in ('admin', 'superadmin') or request.headers.get('x-account-id') != actor['id']:
            raise HTTPException(403, '需要已验证的维护账号，请刷新后重试')
        return actor['id']

    def public(row):
        fields = ('id', 'car', 'title', 'tier', 'zone', 'lap', 'part', 'start')
        return {**{key: row[key] for key in fields},
                'url': video_url(row['video_id'], row['part'], row['start'])}

    @app.get('/api/route-videos')
    def listing(server: Literal['cn', 'global'], big: str, small: str):
        with closing(connect()) as db:
            rows = db.execute('SELECT * FROM route_videos WHERE server=? AND big=? AND small=? AND active=1 ORDER BY id DESC',
                              (server, big, small)).fetchall()
        return {'videos': [public(row) for row in rows]}

    @app.get('/api/route-videos/matrix')
    def matrix(server: Literal['cn', 'global'], zone: Literal['五区', '四区'] = '五区',
               tier: Literal['理论', '高手'] = '理论', route: Literal['normal', 'special'] = 'normal',
               oc: bool = False):
        from backend.coverage import COLUMN_LIMIT, ordered_score_cars
        data, catalog, _ = source(server)
        if server == 'global':
            zone, tier = '五区', '理论'
        ordered, _, _, _ = ordered_score_cars(data, catalog, zone, tier, route, oc and server == 'global')
        maps = list(dict.fromkeys((track['大地图'], track['小地图']) for track in data['tracks']))
        cars = {car['nickname']: car.get('title', '') for car in ordered}
        # Keep references outside the selected score sheet reachable at the end.
        for car in catalog['cars']:
            if car.get('nickname') and car.get('zones'):
                cars.setdefault(car['nickname'], car.get('title', ''))
        with closing(connect()) as db:
            counts = db.execute("""SELECT big,small,car,COUNT(*) FROM route_videos
                WHERE server=? AND active=1 GROUP BY big,small,car""", (server,)).fetchall()
        return {'maps': maps, 'cars': list(cars.items()), 'counts': [list(row) for row in counts],
                'column_limit': COLUMN_LIMIT}

    @app.post('/api/route-videos/cell')
    def cell(request: Request, target: Target):
        admin(request)
        with closing(connect()) as db:
            rows = db.execute('SELECT * FROM route_videos WHERE server=? AND big=? AND small=? AND car=? ORDER BY id DESC',
                              (target.server, target.big, target.small, target.car)).fetchall()
        return {'videos': [{**public(row), 'active': bool(row['active'])} for row in rows]}

    @app.post('/api/route-videos/preview')
    def preview(request: Request, value: Paste):
        admin(request)
        try:
            video_id, part, start = normalize(value.raw)
        except ValueError as error:
            raise HTTPException(422, str(error)) from error
        title, part_title = metadata(video_id, part)
        return {'video_id': video_id, 'part': part, 'start': start,
                'title': part_title if part_title and part_title != title else title,
                'url': video_url(video_id, part, start)}

    @app.post('/api/route-videos/bind')
    def bind(request: Request, value: Binding):
        editor = admin(request)
        data, catalog, _ = source(value.server)
        if not any((track['大地图'], track['小地图']) == (value.big, value.small) for track in data['tracks']) or not any(
            car.get('nickname') == value.car for car in catalog['cars']
        ):
            raise HTTPException(422, '车辆或地图已变化，请刷新成绩表')
        title = value.title.strip()
        if not title:
            raise HTTPException(422, '请填写显示标题')
        with closing(connect()) as db, db:
            db.execute("""INSERT INTO route_videos
              (server,big,small,car,video_id,part,start,title,tier,zone,lap,editor,updated_at)
              VALUES (?,?,?,?,?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP)
              ON CONFLICT(server,big,small,car,video_id,part,start) DO UPDATE SET
              title=excluded.title,tier=excluded.tier,zone=excluded.zone,lap=excluded.lap,editor=excluded.editor,updated_at=CURRENT_TIMESTAMP""",
                       (value.server, value.big, value.small, value.car, value.video_id, value.part,
                        value.start, title, value.tier, value.zone, value.lap, editor))
        return {'saved': True}

    @app.post('/api/route-videos/visibility')
    def visibility(request: Request, value: Visibility):
        editor = admin(request)
        with closing(connect()) as db, db:
            result = db.execute("""UPDATE route_videos SET active=?,editor=?,updated_at=CURRENT_TIMESTAMP
                WHERE id=? AND server=? AND big=? AND small=? AND car=?""",
                                (value.active, editor, value.id, value.server, value.big, value.small, value.car))
            if not result.rowcount:
                raise HTTPException(404, '关联已变化，请重新打开')
        return {'saved': True}
