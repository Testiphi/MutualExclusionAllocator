"""Explicit offline/production international-state provisioning. Never run at startup."""
import argparse
from contextlib import closing
import json
import os
from pathlib import Path
import sqlite3
from backend.global_scores import FILES, GlobalScoreWriter, GlobalVersions, initialize, validate_root, validate_contents
from backend.app import Store

TABLES=('global_score_current','global_score_batches','global_score_control')

def state(db):
    present={r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")} & set(TABLES)
    if not present:return {'global_score_schema':0}
    if present!=set(TABLES):raise ValueError('国际成绩状态表不完整')
    if db.execute('SELECT count(*) FROM global_score_control WHERE slot=1').fetchone()[0]!=1 or db.execute('SELECT count(*) FROM global_score_current WHERE slot=1').fetchone()[0]!=1:raise ValueError('国际成绩状态指针不完整')
    return {'global_score_schema':1,'global_score_version':db.execute('SELECT version FROM global_score_current WHERE slot=1').fetchone()[0],'global_pending_batches':db.execute("SELECT count(*) FROM global_score_batches WHERE state IN ('applying','rolling_back','recovery_required')").fetchone()[0]}

def preflight(config):
    from backend.coverage_production import preflight as coverage_preflight
    from backend.production import require_database
    result=coverage_preflight(config);path=require_database(config)
    with closing(sqlite3.connect((path/'accounts.sqlite3').as_uri()+'?mode=ro',uri=True)) as db:
        result.update(state(db))
        if result['global_score_schema']:
            root,marker=validate_root(path/'global-score-state',path,True)
            binding,enabled=db.execute('SELECT binding,enabled FROM global_score_control WHERE slot=1').fetchone()
            if binding!=marker['binding']:raise ValueError('国际成绩账号绑定不一致')
            versions=GlobalVersions(root,lambda p:validate_root(p,path,True));_,raw=versions.read(result['global_score_version'])
            if json.loads(raw[FILES[0]])['_meta']['catalog_payload_sha256']!=marker['catalog_payload_sha256']:raise ValueError('国际车辆规则变化')
            result['global_writes_enabled']=bool(enabled)
    return result

def migrate(config,source,expected_dataset,expected_cn_version):
    from backend.production import require_database,service_lock,backup
    from backend.score_production import existing_fingerprints,verify_backup
    path=require_database(config);source=Path(source).absolute()
    raw={n:(source/n).read_bytes() for n in FILES};_,_,manifest=validate_contents(raw)
    if manifest['_meta']['dataset_version']!=expected_dataset:raise ValueError('国际运行数据版本与批准基线不一致')
    with service_lock(path):
        before=preflight(config)
        if before['coverage_schema']!=2 or before['score_version']!=expected_cn_version or before['pending_batches'] or before.get('global_pending_batches',0):raise ValueError('双服权限、国服版本或未完成批次前置不符合')
        if before['global_score_schema']:return {**before,'already_migrated':True,'existing_rows_preserved':True}
        saved=backup(config);verify_backup(saved)
        with closing(sqlite3.connect(path/'accounts.sqlite3')) as db:
            names=[r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")];fingerprints=existing_fingerprints(db,names)
        root=path/'global-score-state'
        if root.exists():
            _,marker=validate_root(root,path,True)
            from backend.score_repository import digest
            if marker['seed_hashes']!={n:digest(raw[n]) for n in FILES}:raise ValueError('已有国际状态使用不同种子，禁止覆盖')
        def verify_existing(db):
            if fingerprints!=existing_fingerprints(db,names):raise ValueError('已有业务行变化，请保留现场核对')
        initialize(root,Store(path),source,True,verify_existing=verify_existing)
        return {**preflight(config),'already_migrated':False,'backup':str(saved),'existing_rows_preserved':True,'default_writes':False}

def main():
    from backend.production import settings
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('action',choices=['preflight','migrate','enable','disable']);parser.add_argument('--config',type=Path,default=Path('/etc/racepick/production.json'));parser.add_argument('--source',type=Path);parser.add_argument('--expected-dataset');parser.add_argument('--expected-cn-version')
    args=parser.parse_args();config=settings(args.config)
    if args.action=='preflight':result=preflight(config)
    elif args.action=='migrate':
        if not all((args.source,args.expected_dataset,args.expected_cn_version)):parser.error('迁移需指定来源、国际版本和现场国服版本')
        os.umask(0o077);result=migrate(config,args.source,args.expected_dataset,args.expected_cn_version)
    else:
        from backend.production import require_database,service_lock
        path=require_database(config)
        with service_lock(path):
            writer=GlobalScoreWriter(path/'global-score-state',Store(path),True)
            with writer.versions.lock(),writer.store.connect() as db:
                writer.idle(db);db.execute('UPDATE global_score_control SET enabled=? WHERE slot=1',(int(args.action=='enable'),))
        result={'global_writes_enabled':args.action=='enable'}
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
