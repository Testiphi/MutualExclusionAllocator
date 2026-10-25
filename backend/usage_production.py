"""Explicit usage initialization/retention. Never run by application startup in production."""
import argparse
from contextlib import closing
import json
import os
from pathlib import Path
import sqlite3
from backend.usage import UsageStore, schema


def snapshot(source, destination):
    source, destination = Path(source), Path(destination)
    if source.is_symlink() or not source.is_file():
        raise ValueError('统计源必须是独立普通文件')
    with destination.open('xb'):
        pass
    with closing(sqlite3.connect(source.resolve().as_uri()+'?mode=ro',uri=True)) as original, closing(sqlite3.connect(destination)) as copy:
        if schema(original)!=1 or original.execute('PRAGMA integrity_check').fetchone()[0]!='ok':
            raise ValueError('统计源校验失败')
        original.backup(copy)
        if schema(copy)!=1 or copy.execute('PRAGMA integrity_check').fetchone()[0]!='ok':
            raise ValueError('统计快照校验失败')
    return destination


def preflight(config):
    from backend.production import require_database
    path=require_database(config)
    with closing(sqlite3.connect((path/'accounts.sqlite3').as_uri()+'?mode=ro',uri=True)) as db:
        if db.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise ValueError('账号库校验失败')
        version=db.execute('SELECT version FROM score_current WHERE slot=1').fetchone()[0]
        pending=db.execute("SELECT count(*) FROM score_batches WHERE state IN ('applying','rolling_back','recovery_required')").fetchone()[0]
    target=path/'usage.sqlite3'
    if target.exists():
        if target.is_symlink():raise ValueError('统计库不可为链接')
        with closing(sqlite3.connect(target.as_uri()+'?mode=ro',uri=True)) as db:
            if schema(db)!=1 or db.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise ValueError('统计库校验失败')
    return {'usage_schema':1 if target.exists() else 0,'score_version':version,'pending_batches':pending,
            'usage_file':str(target),'account_database_modified':False}


def initialize(config, expected_version):
    from backend.production import require_database, service_lock, backup
    from backend.score_production import verify_backup, file_hash
    path=require_database(config)
    with service_lock(path):
        before=preflight(config)
        if before['score_version']!=expected_version or before['pending_batches']:
            raise ValueError('成绩版本变化或存在未完成批次，停止')
        if before['usage_schema']==1:return {**before,'already_initialized':True}
        saved=backup(config);verify_backup(saved)
        original=file_hash(path/'accounts.sqlite3')
        target=path/'usage.sqlite3';UsageStore.initialize(target)
        if os.name=='posix':
            owner=(path/'accounts.sqlite3').stat();os.chown(target,owner.st_uid,owner.st_gid);target.chmod(0o600)
        if file_hash(path/'accounts.sqlite3')!=original:
            raise ValueError('账号库出现外部变化，保留现场，禁止继续')
        return {**preflight(config),'already_initialized':False,'backup':str(saved),'existing_accounts_preserved':True}


def prune(config, execute=False):
    from backend.production import require_database, service_lock, backup
    path=require_database(config)
    if not execute:return UsageStore(path/'usage.sqlite3').prune()
    with service_lock(path):
        before=preflight(config)
        if before['pending_batches']:raise ValueError('存在未完成批次，停止')
        saved=backup(config)
        return {**UsageStore(path/'usage.sqlite3').prune(execute=True),'backup':str(saved)}


def main():
    from backend.production import settings
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['preflight','initialize','prune-preview','prune'])
    parser.add_argument('--config',type=Path,default=Path('/etc/racepick/production.json'))
    parser.add_argument('--expected-version')
    args=parser.parse_args()
    if args.action=='initialize' and not args.expected_version:parser.error('需指定现场核对的 --expected-version')
    if args.action in ('initialize','prune'):os.umask(0o077)
    try:
        config=settings(args.config)
        result=preflight(config) if args.action=='preflight' else initialize(config,args.expected_version) if args.action=='initialize' else prune(config,args.action=='prune')
    except (OSError,ValueError,sqlite3.Error) as error:parser.exit(1,str(error)+'\n')
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
