"""Preview or explicitly merge a frozen website route-video seed."""
import argparse
from collections import Counter
from contextlib import closing
import hashlib
import json
from pathlib import Path
import sqlite3

from backend.route_videos import Binding, initialize_store, video_url

ROOT = Path(__file__).resolve().parents[1]
SEED = ROOT / 'route-video-seed.json'
KEYS = ('server', 'big', 'small', 'car', 'video_id', 'part', 'start')
VALUES = ('title', 'tier', 'zone', 'lap')
FIELDS = KEYS + VALUES


def seed_rows(raw):
    seed = json.loads(raw)
    rows = {}
    for record in seed['videos']:
        row = {field: record[field] for field in FIELDS}
        if Binding.model_validate(row).model_dump() != row:
            raise ValueError('跑法种子字段不一致')
        key = tuple(row[field] for field in KEYS)
        if key in rows or video_url(row['video_id'], row['part'], row['start']) != record['url']:
            raise ValueError('跑法种子存在重复键或非规范链接')
        rows[key] = row
    counts = Counter(key[0] for key in rows)
    totals = {server: {'videos': counts[server],
                       'cells': len({key[:4] for key in rows if key[0] == server})}
              for server in ('cn', 'global')}
    if totals != seed['totals']:
        raise ValueError('跑法种子数量不符')
    return rows


def inspect(db, rows):
    db.row_factory = sqlite3.Row
    tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    present = 'route_videos' in tables
    if present != ('route_video_schema' in tables):
        raise ValueError('跑法参考表与版本标记不一致')
    if present and [r[0] for r in db.execute('SELECT version FROM route_video_schema')] != [1]:
        raise ValueError('跑法参考数据库版本不兼容')
    existing = {tuple(row[field] for field in KEYS): row
                for row in db.execute('SELECT * FROM route_videos')} if present else {}
    additions = []
    duplicate = 0
    conflicts = []
    for key, row in rows.items():
        current = existing.get(key)
        if current is None:
            additions.append(row)
            continue
        differences = {field: {'current': current[field], 'seed': row[field]}
                       for field in VALUES if current[field] != row[field]}
        if not current['active']:
            differences['active'] = {'current': current['active'], 'seed': 1}
        if differences:
            conflicts.append({'key': dict(zip(KEYS, key)), 'fields': differences})
        else:
            duplicate += 1
    return present, additions, duplicate, conflicts


def merge(db, rows, *, apply=False):
    present, additions, duplicate, conflicts = inspect(db, rows)
    if apply:
        if not present:
            initialize_store(db)
            db.execute('CREATE TABLE route_video_schema(version INTEGER NOT NULL)')
            db.execute('INSERT INTO route_video_schema VALUES(1)')
        db.executemany(
            'INSERT INTO route_videos (' + ','.join(FIELDS) + ',editor,updated_at) VALUES ('
            + ','.join('?' for _ in FIELDS) + ",'release-seed',CURRENT_TIMESTAMP)",
            [tuple(row[field] for field in FIELDS) for row in additions])
    return {'new': len(additions), 'duplicates': duplicate, 'conflicts': conflicts}


def main():
    from backend.production import backup, require_database, service_lock, settings
    from backend.coverage import state
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--expect-sha256', required=True)
    args = parser.parse_args()
    raw = SEED.read_bytes()
    if hashlib.sha256(raw).hexdigest() != args.expect_sha256:
        raise ValueError('种子 SHA256 与审核值不一致')
    rows = seed_rows(raw)
    config = settings(args.config)
    path = require_database(config)
    db_path = path / 'accounts.sqlite3'
    if db_path.is_symlink() or not (path / 'score-state').is_dir():
        raise ValueError('需要实际版本化网站数据目录')
    with closing(sqlite3.connect(db_path.as_uri() + '?mode=ro', uri=True)) as db:
        if state(db)['coverage_schema'] not in (1, 2):
            raise ValueError('必须先具备成绩表能力')
        result = merge(db, rows)
    if args.apply:
        with service_lock(path):
            backup_path = backup(config)
            with closing(sqlite3.connect(db_path.as_uri() + '?mode=rw', uri=True)) as db, db:
                db.execute('BEGIN IMMEDIATE')
                if merge(db, rows) != result:
                    raise ValueError('目标状态已改变，请重新预览')
                result = {**merge(db, rows, apply=True), 'backup': str(backup_path)}
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
