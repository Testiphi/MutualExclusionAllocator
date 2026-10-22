"""Explicit offline contribution migration; never imports historical submissions."""
import argparse
from contextlib import closing
import json
import os
from pathlib import Path
import sqlite3

from backend.contributions import available, migrate as migrate_tables
from backend.score_repository import Versions, validate_production_root

TABLES = ('contribution_rules', 'contributions', 'contribution_sources',
          'contribution_events', 'contribution_preferences')


def state(db):
    present = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    owned = present.intersection(TABLES)
    if not owned:
        return {'contribution_schema': 0, 'enabled_at': None, 'contribution_counts': {}}
    if owned != set(TABLES):
        raise ValueError('贡献表不完整，保留现场，禁止自动重建')
    rows = db.execute('SELECT version,enabled_at FROM contribution_rules').fetchall()
    if len(rows) != 1 or rows[0][0] != 1:
        raise ValueError('贡献规则版本不兼容')
    return {'contribution_schema': 1, 'enabled_at': rows[0][1],
            'contribution_counts': {n: db.execute('SELECT count(*) FROM '+n).fetchone()[0] for n in TABLES[1:]}}


def preflight(config):
    from backend.production import require_database
    path = require_database(config)
    root, marker = validate_production_root(path/'score-state', path)
    with closing(sqlite3.connect((path/'accounts.sqlite3').as_uri()+'?mode=ro', uri=True)) as db:
        if db.execute('PRAGMA integrity_check').fetchone()[0] != 'ok' or db.execute('PRAGMA foreign_key_check').fetchall():
            raise ValueError('数据库完整性或外键校验失败')
        version = db.execute('SELECT version FROM score_current WHERE slot=1').fetchone()[0]
        control = db.execute('SELECT binding,enabled FROM score_control WHERE slot=1').fetchone()
        if not control or control[0] != marker['binding']:
            raise ValueError('成绩与账号库绑定不一致')
        pending = db.execute("SELECT count(*) FROM score_batches WHERE state IN ('applying','rolling_back','recovery_required')").fetchone()[0]
        counts = {n: db.execute('SELECT count(*) FROM '+n).fetchone()[0] for n in ('users','profiles','submissions')}
        result = state(db)
    info, _ = Versions(root, lambda p: validate_production_root(p, path)).read(version)
    result.update(score_version=version, score_writes=bool(control[1]), pending_batches=pending,
                  counts=counts, active_files=info['files'])
    return result


def migrate(config, expected_version):
    from backend.production import require_database, service_lock, backup
    from backend.score_production import existing_fingerprints, verify_backup
    path = require_database(config)
    with service_lock(path):
        before = preflight(config)
        if before['score_version'] != expected_version:
            raise ValueError('活动成绩版本已变化，请重新核对，不覆盖或跳过检查')
        if before['pending_batches']:
            raise ValueError('存在未完成成绩批次，请先按原流程处理')
        if before['contribution_schema'] == 1:
            return {**before, 'already_migrated': True, 'existing_rows_preserved': True}
        saved = backup(config)  # Complete SQLite + immutable score versions, never SQLite alone.
        verify_backup(saved)
        versions = Versions(path/'score-state', lambda p: validate_production_root(p, path))
        with versions.lock(), closing(sqlite3.connect(path/'accounts.sqlite3')) as db, db:
            db.execute('PRAGMA foreign_keys=ON'); db.execute('BEGIN IMMEDIATE')
            if db.execute('SELECT version FROM score_current WHERE slot=1').fetchone()[0] != expected_version:
                raise ValueError('迁移前版本变化，停止')
            if state(db)['contribution_schema'] != 0:
                raise ValueError('贡献状态已变化，请重新核对')
            names = [r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
            fingerprints = existing_fingerprints(db, names)
            migrate_tables(db)
            if fingerprints != existing_fingerprints(db, names):
                raise ValueError('已有业务行发生变化，迁移事务已取消')
            if any(state(db)['contribution_counts'].values()):
                raise ValueError('新贡献表必须为空，不导入历史数据')
        return {**preflight(config), 'already_migrated': False, 'backup': str(saved),
                'existing_rows_preserved': True, 'historical_submissions_enrolled': 0}


def main():
    from backend.production import settings
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['preflight','migrate'])
    parser.add_argument('--config', type=Path, default=Path('/etc/racepick/production.json'))
    parser.add_argument('--expected-version')
    args = parser.parse_args()
    if args.action == 'migrate' and not args.expected_version:
        parser.error('migrate必须指定刚核验的--expected-version')
    if args.action == 'migrate': os.umask(0o077)
    try:
        config = settings(args.config)
        result = preflight(config) if args.action == 'preflight' else migrate(config, args.expected_version)
    except (ValueError, OSError, sqlite3.Error) as error:
        parser.exit(1, str(error)+'\n')
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__': main()
