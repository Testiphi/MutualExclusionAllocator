"""Preview or apply an approved route-video update plan."""
import argparse
from contextlib import closing, nullcontext
from hashlib import sha256
import json
from pathlib import Path
import sqlite3

from backend.route_video_release import KEYS, VALUES, inspect, merge, seed_rows


KEY_WHERE = ' AND '.join(f'{field}=?' for field in KEYS)
OLD_WHERE = ' AND '.join(f'{field} IS ?' for field in VALUES)


def load_plan(plan_raw, baseline_raw, candidate_raw, expected_sha256):
    if sha256(plan_raw).hexdigest() != expected_sha256:
        raise ValueError('更新计划 SHA256 与审核值不一致')
    plan = json.loads(plan_raw)
    for name, raw in [('baseline', baseline_raw), ('candidate', candidate_raw)]:
        if sha256(raw).hexdigest() != plan[name + '_seed_sha256']:
            raise ValueError(f'{name} 种子 SHA256 与计划不一致')
    baseline = seed_rows(baseline_raw)
    candidate = seed_rows(candidate_raw)
    if baseline.keys() - candidate.keys():
        raise ValueError('更新计划不允许删除既有绑定')
    updates = {
        key: ({f: row[f] for f in VALUES}, {f: candidate[key][f] for f in VALUES})
        for key, row in baseline.items() if row != candidate[key]
    }
    additions = {key: row for key, row in candidate.items() if key not in baseline}
    declared_updates = {
        tuple(item['key'][field] for field in KEYS): (item['before'], item['after'])
        for item in plan['updates']
    }
    declared_additions = {tuple(row[field] for field in KEYS): row for row in plan['additions']}
    counts = {'update': len(updates), 'insert': len(additions), 'unchanged': len(baseline) - len(updates)}
    if (updates != declared_updates or len(updates) != len(plan['updates'])
            or additions != declared_additions or len(additions) != len(plan['additions'])
            or counts != plan['expected_counts']):
        raise ValueError('计划明细与两个种子的逐项差异不一致')
    return updates, additions


def preview(db, updates, additions):
    present, _, _, _ = inspect(db, {})
    if not present:
        raise ValueError('需要已初始化的跑法表')
    pending_updates = []
    pending_additions = []
    conflicts = []
    for keys, targets in ((updates, pending_updates), (additions, pending_additions)):
        for key in keys:
            row = db.execute('SELECT * FROM route_videos WHERE ' + KEY_WHERE, key).fetchone()
            current = {f: row[f] for f in VALUES} if row else None
            if key in updates:
                before, after = updates[key]
            else:
                before, after = None, {f: additions[key][f] for f in VALUES}
            if row is None and before is None:
                targets.append(key)
            elif row is None or row['active'] != 1 or current not in (before, after):
                conflicts.append({'key': dict(zip(KEYS, key)), 'current': current,
                                  'active': row['active'] if row else None})
            elif current != after:
                targets.append(key)
    return {'updates': pending_updates, 'additions': pending_additions, 'conflicts': conflicts}


def apply(db, updates, additions, expected_preview):
    with db:
        db.execute('BEGIN IMMEDIATE')
        current = preview(db, updates, additions)
        if current != expected_preview or current['conflicts']:
            raise ValueError('预检后目标状态变化或存在冲突，整批停止')
        for key in current['updates']:
            before, after = updates[key]
            fields = [f for f in VALUES if before[f] != after[f]]
            assignment = ','.join(f'{f}=?' for f in fields)
            args = [*(after[f] for f in fields), *key, *(before[f] for f in VALUES)]
            cursor = db.execute(f'UPDATE route_videos SET {assignment} WHERE {KEY_WHERE} AND active=1 AND {OLD_WHERE}', args)
            if cursor.rowcount != 1:
                raise ValueError('既有绑定更新数量不符')
        if current['additions']:
            inserted = merge(db, {key: additions[key] for key in current['additions']}, apply=True)
            if inserted['new'] != len(current['additions']):
                raise ValueError('新增绑定数量不符')
        if any(preview(db, updates, additions).values()):
            raise ValueError('事务内读回复核失败')
    return {'updated': len(current['updates']), 'inserted': len(current['additions'])}


def main():
    from backend.production import backup, require_database, service_lock, settings
    from backend.coverage import state

    parser = argparse.ArgumentParser(description=__doc__)
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument('--config', type=Path)
    target.add_argument('--isolated-db', type=Path)
    parser.add_argument('--isolated-backup', type=Path)
    for flag in ('plan', 'baseline', 'candidate'):
        parser.add_argument('--' + flag, required=True, type=Path)
    parser.add_argument('--expect-plan-sha256', required=True)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    if bool(args.isolated_backup) != bool(args.apply and args.isolated_db):
        parser.error('--isolated-backup 仅用于隔离库写入，并且为必填项')
    updates, additions = load_plan(args.plan.read_bytes(), args.baseline.read_bytes(),
                                   args.candidate.read_bytes(), args.expect_plan_sha256)
    config = settings(args.config) if args.config else None
    data_dir = require_database(config) if config else None
    path = data_dir / 'accounts.sqlite3' if config else args.isolated_db
    if path.is_symlink() or (config and not (data_dir / 'score-state').is_dir()):
        raise ValueError('数据库路径无效')
    uri = path.resolve(strict=True).as_uri()
    with closing(sqlite3.connect(uri + '?mode=ro', uri=True)) as db:
        db.execute('BEGIN')
        if config and state(db)['coverage_schema'] not in (1, 2):
            raise ValueError('必须先具备成绩表能力')
        result = preview(db, updates, additions)
    receipt = {'plan_sha256': args.expect_plan_sha256, 'pending_updates': len(result['updates']),
               'pending_additions': len(result['additions']), 'conflicts': result['conflicts']}
    if not result['conflicts'] and args.apply:
        receipt.update(updated=0, inserted=0)
        if result['updates'] or result['additions']:
            with service_lock(data_dir) if config else nullcontext():
                if config:
                    backup_path = backup(config)
                else:
                    backup_path = args.isolated_backup
                    with backup_path.open('xb'):
                        pass
                    with closing(sqlite3.connect(uri + '?mode=ro', uri=True)) as source:
                        with closing(sqlite3.connect(backup_path)) as dest:
                            source.backup(dest)
                with closing(sqlite3.connect(uri + '?mode=rw', uri=True)) as db:
                    receipt.update(apply(db, updates, additions, result), backup=str(backup_path))
    print(json.dumps(receipt, ensure_ascii=False, indent=2))
    return 2 if result['conflicts'] else 0


if __name__ == '__main__':
    raise SystemExit(main())
