"""Offline feedback migration on the existing production account and score state."""
import argparse
from contextlib import closing
import json
import os
from pathlib import Path
import sqlite3

from backend.feedback import state, migrate as migrate_tables
from backend.score_repository import Versions, validate_production_root


def preflight(config):
    from backend.production import require_database
    from backend.contribution_production import preflight as contribution_preflight
    result = contribution_preflight(config)
    if result['contribution_schema'] != 1:
        raise ValueError('需要现有贡献schema1；本工具不执行旧迁移')
    path = require_database(config)
    with closing(sqlite3.connect((path/'accounts.sqlite3').as_uri()+'?mode=ro', uri=True)) as db:
        result.update(state(db))
    return result


def migrate(config, expected_version):
    from backend.production import require_database, service_lock, backup
    from backend.score_production import existing_fingerprints, verify_backup
    path = require_database(config)
    with service_lock(path):
        before = preflight(config)
        if before['score_version'] != expected_version:
            raise ValueError('活动成绩版本变化，请重新核对')
        if before['pending_batches']:
            raise ValueError('存在未完成成绩批次，请先按原流程处理')
        if before['feedback_schema'] == 1:
            return {**before, 'already_migrated': True, 'existing_rows_preserved': True}
        saved = backup(config)
        verify_backup(saved)
        versions = Versions(path/'score-state', lambda p: validate_production_root(p, path))
        with versions.lock(), closing(sqlite3.connect(path/'accounts.sqlite3')) as db, db:
            db.execute('PRAGMA foreign_keys=ON'); db.execute('BEGIN IMMEDIATE')
            if db.execute('SELECT version FROM score_current WHERE slot=1').fetchone()[0] != expected_version:
                raise ValueError('执行前成绩版本变化，停止迁移')
            if state(db)['feedback_schema'] != 0:
                raise ValueError('反馈表状态变化，请重新检查')
            names = [r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
            fingerprints = existing_fingerprints(db, names)
            migrate_tables(db)
            if fingerprints != existing_fingerprints(db, names):
                raise ValueError('已有业务行发生变化，事务已取消')
            if any(state(db)['feedback_counts'].values()):
                raise ValueError('反馈新表必须为空，不导入本地测试反馈')
        return {**preflight(config), 'already_migrated': False, 'backup': str(saved),
                'existing_rows_preserved': True, 'test_feedback_imported': 0}


def main():
    from backend.production import settings
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['preflight', 'migrate'])
    parser.add_argument('--config', type=Path, default=Path('/etc/racepick/production.json'))
    parser.add_argument('--expected-version')
    args = parser.parse_args()
    if args.action == 'migrate' and not args.expected_version:
        parser.error('migrate必须指定当前核验的--expected-version')
    if args.action == 'migrate': os.umask(0o077)
    try:
        config = settings(args.config)
        result = preflight(config) if args.action == 'preflight' else migrate(config, args.expected_version)
    except (ValueError, OSError, sqlite3.Error) as error:
        parser.exit(1, str(error)+'\n')
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__': main()
