"""Preview or apply an approved route-video update plan."""
import argparse
from contextlib import closing, nullcontext
from hashlib import sha256
import json
from pathlib import Path
import sqlite3

from backend.route_video_release import KEYS, VALUES, inspect, merge, seed_rows, video_url


KEY_WHERE = ' AND '.join(f'{field}=?' for field in KEYS)
OLD_WHERE = ' AND '.join(f'{field} IS ?' for field in VALUES)


def load_plan(plan_raw, baseline_raw, candidate_raw, expected_sha256):
    if sha256(plan_raw).hexdigest() != expected_sha256:
        raise ValueError('更新计划 SHA256 与审核值不一致')
    plan = json.loads(plan_raw)
    frozen = 'deactivations' in plan
    for name, raw in [('baseline', baseline_raw), ('candidate', candidate_raw)]:
        hash_field = name + ('_sha256' if frozen else '_seed_sha256')
        if sha256(raw).hexdigest() != plan[hash_field]:
            raise ValueError(f'{name} 种子 SHA256 与计划不一致')
    baseline = seed_rows(baseline_raw)
    candidate = seed_rows(candidate_raw)
    removed = baseline.keys() - candidate.keys()
    if removed and not frozen:
        raise ValueError('旧版更新计划不允许停用既有绑定')
    updates = {
        key: ({f: row[f] for f in VALUES}, {f: candidate[key][f] for f in VALUES})
        for key, row in baseline.items() if key in candidate and row != candidate[key]
    }
    additions = {key: row for key, row in candidate.items() if key not in baseline}
    if frozen:
        expected_updates = {}
        for key, (before, after) in updates.items():
            expected_updates[key] = {'expected_active': True, 'expected_fields': before,
                                     'changes': {f: {'old': before[f], 'new': after[f]}
                                                 for f in VALUES if before[f] != after[f]}}
        deactivations = {key: {f: baseline[key][f] for f in VALUES} for key in removed}
        expected_deactivations = {
            key: {'expected_active': True, 'target_active': False, 'expected_fields': fields,
                  'url': video_url(key[4], key[5], key[6])}
            for key, fields in deactivations.items()
        }

        def declared(items, metadata):
            result = {tuple(item['key'][f] for f in KEYS):
                      {f: v for f, v in item.items() if f not in ('key', metadata)} for item in items}
            if len(result) != len(items) or any(set(item['key']) != set(KEYS) for item in items):
                raise ValueError('冻结计划包含重复或不完整的键')
            return result

        expected_additions = {key: {**row, 'url': video_url(key[4], key[5], key[6])}
                              for key, row in additions.items()}
        declared_additions = {tuple(row[f] for f in KEYS): row for row in plan['additions']}
        if (plan['binding_key'] != list(KEYS)
                or expected_updates != declared(plan['field_updates'], 'basis')
                or expected_deactivations != declared(plan['deactivations'], 'reason')
                or expected_additions != declared_additions
                or len(declared_additions) != len(plan['additions'])
                or plan['counts_by_server'] != json.loads(candidate_raw)['totals']
                or plan['unchanged'] != len(baseline) - len(updates) - len(removed)):
            raise ValueError('冻结计划明细与两个种子的逐项差异不一致')
        unchanged = {key: {f: row[f] for f in VALUES} for key, row in baseline.items()
                     if key not in updates and key not in deactivations}
        return updates, additions, deactivations, unchanged

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
    return updates, additions, {}, None


def preview(db, updates, additions, deactivations, unchanged):
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
    pending_deactivations = []
    for key, before in deactivations.items():
        row = db.execute('SELECT * FROM route_videos WHERE ' + KEY_WHERE, key).fetchone()
        current = {f: row[f] for f in VALUES} if row else None
        if not row or row['active'] not in (0, 1) or current != before:
            conflicts.append({'key': dict(zip(KEYS, key)), 'current': current,
                              'active': row['active'] if row else None})
        elif row['active'] == 1:
            pending_deactivations.append((key, row['id']))
    if unchanged is not None:
        known = set(updates) | set(additions) | set(deactivations) | set(unchanged)
        active = {tuple(row[f] for f in KEYS): row
                  for row in db.execute('SELECT * FROM route_videos WHERE active=1 ORDER BY id')}
        for key, before in unchanged.items():
            row = active.get(key)
            if row is None or any(row[f] != before[f] for f in VALUES):
                conflicts.append({'key': dict(zip(KEYS, key)), 'reason': '冻结中未变更的启用绑定不匹配'})
        for key in active.keys() - known:
            conflicts.append({'key': dict(zip(KEYS, key)), 'reason': '存在冻结之外的启用绑定'})
    return {'updates': pending_updates, 'additions': pending_additions,
            'deactivations': pending_deactivations, 'conflicts': conflicts}


def apply(db, updates, additions, deactivations, unchanged, expected_preview):
    with db:
        db.execute('BEGIN IMMEDIATE')
        current = preview(db, updates, additions, deactivations, unchanged)
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
        for key, row_id in current['deactivations']:
            before = deactivations[key]
            cursor = db.execute(
                f'UPDATE route_videos SET active=0 WHERE id=? AND {KEY_WHERE} AND active=1 AND {OLD_WHERE}',
                (row_id, *key, *(before[f] for f in VALUES)))
            if cursor.rowcount != 1:
                raise ValueError('既有绑定停用数量不符')
        if current['additions']:
            inserted = merge(db, {key: additions[key] for key in current['additions']}, apply=True)
            if inserted['new'] != len(current['additions']):
                raise ValueError('新增绑定数量不符')
        if any(preview(db, updates, additions, deactivations, unchanged).values()):
            raise ValueError('事务内读回复核失败')
    return {'updated': len(current['updates']), 'inserted': len(current['additions']),
            'deactivated': len(current['deactivations']),
            'deactivated_rows': [{'key': dict(zip(KEYS, key)), 'id': row_id}
                                 for key, row_id in current['deactivations']]}


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
    updates, additions, deactivations, unchanged = load_plan(args.plan.read_bytes(), args.baseline.read_bytes(),
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
        result = preview(db, updates, additions, deactivations, unchanged)
    receipt = {'plan_sha256': args.expect_plan_sha256, 'pending_updates': len(result['updates']),
               'pending_additions': len(result['additions']), 'pending_deactivations': len(result['deactivations']),
               'conflicts': result['conflicts']}
    if unchanged is not None:
        total = len(updates) + len(additions) + len(deactivations)
        pending = sum(len(result[key]) for key in ('updates', 'additions', 'deactivations'))
        receipt['plan_state'] = ('conflict' if result['conflicts'] else 'baseline' if pending == total
                                 else 'target' if pending == 0 else 'partial')
        receipt['already_matched_operations'] = total - pending if not result['conflicts'] else None
    if not result['conflicts'] and args.apply:
        receipt.update(updated=0, inserted=0, deactivated=0, deactivated_rows=[])
        if any(result[key] for key in ('updates', 'additions', 'deactivations')):
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
                    receipt.update(apply(db, updates, additions, deactivations, unchanged, result), backup=str(backup_path))
    print(json.dumps(receipt, ensure_ascii=False, indent=2))
    return 2 if result['conflicts'] else 0


if __name__ == '__main__':
    raise SystemExit(main())
