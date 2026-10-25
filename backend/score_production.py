"""Offline, hash-bound production score migration and coherent snapshot backups."""
from contextlib import closing
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import sqlite3
import zipfile
from backend.app import Store
from backend.manage import copy_database
from backend.score_repository import Versions,FILES,encode,digest,write_new,validate_production_root,sync_dir
from backend.score_versions import ScoreWriter
from validate_data import validate_data


def source_snapshot(source,expected_data=None,expected_cars=None):
    source=Path(source).resolve();contents={n:(source/n).read_bytes() for n in FILES}
    hashes={n:digest(raw) for n,raw in contents.items()}
    for name,wanted in [('gauntlet_data.json',expected_data),('cars.json',expected_cars)]:
        if wanted is not None and hashes[name]!=wanted:raise ValueError('源文件哈希不符合已确认基线：'+name)
    errors,_=validate_data(json.loads(contents['gauntlet_data.json']),json.loads(contents['cars.json']))
    if errors:raise ValueError('源数据校验失败：'+str(errors[:10]))
    return contents,hashes


def existing_fingerprints(db,names):
    result={}
    for name in names:
        hasher=hashlib.sha256()
        for row in db.execute('SELECT * FROM "'+name.replace('"','""')+'" ORDER BY rowid'):
            raw=repr(tuple(row)).encode();hasher.update(str(len(raw)).encode()+b':'+raw)
        result[name]=hasher.hexdigest()
    return result

def stream_hash(stream):
    hasher=hashlib.sha256()
    for block in iter(lambda:stream.read(1024*1024),b''):hasher.update(block)
    return hasher.hexdigest()

def file_hash(path):
    with path.open('rb') as stream:return stream_hash(stream)



def preflight(config,source,expected_data=None,expected_cars=None):
    from backend.production import require_database
    path=require_database(config);_,hashes=source_snapshot(source,expected_data,expected_cars)
    with closing(sqlite3.connect((path/'accounts.sqlite3').as_uri()+'?mode=ro',uri=True)) as db:
        if db.execute('PRAGMA integrity_check').fetchone()[0]!='ok' or db.execute('PRAGMA foreign_key_check').fetchall():raise ValueError('账号数据库校验失败')
        tables=[r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")]
        if 'write_receipts' in tables and 'score_control' not in tables:raise ValueError('已有实验室写回表，禁止导入生产')
        counts={name:db.execute('SELECT count(*) FROM '+name).fetchone()[0] for name in ('users','profiles','submissions')}
    return {'source':str(Path(source).resolve()),'hashes':hashes,'counts':counts,'score_state_exists':(path/'score-state').exists()}


def migrate(config,source,expected_data,expected_cars):
    from backend.production import require_database,service_lock,stamp,marker
    path=require_database(config)
    with service_lock(path):
        result=preflight(config,source,expected_data,expected_cars)
        contents,hashes=source_snapshot(source,expected_data,expected_cars)
        root=path/'score-state';db_path=path/'accounts.sqlite3'
        # Full database backup before adding any score-version metadata.
        backups=path/'backups';backups.mkdir(exist_ok=True)
        backup=copy_database(db_path,backups/('pre-score-migration-'+stamp()+'.sqlite3'))
        if root.exists():
            _,info=validate_production_root(root,path)
            if info['seed_hashes']!=hashes:raise ValueError('已有不同迁移基线，不覆盖')
        else:
            staging=path/('score-migration-staging-'+secrets.token_hex(12));staging.mkdir()
            for folder in ('scores/versions','backups'):(staging/folder).mkdir(parents=True)
            initial=Versions(staging).create(contents,None,'production-initial')
            info={'kind':'racepick-score-production-v1','binding':secrets.token_hex(16),'account_marker':marker(config),'initial':initial,'cars_sha256':hashes['cars.json'],'seed_hashes':hashes}
            write_new(staging/'production-scores.json',encode(info).encode());sync_dir(staging)
            os.rename(staging,root);sync_dir(path)
        store=Store(path)
        with store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            names=[r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
            before=existing_fingerprints(db,names)
            if 'score_control' in names:
                binding=db.execute('SELECT binding FROM score_control WHERE slot=1').fetchone()
                if not binding or binding[0]!=info['binding']:raise ValueError('已有版本数据库绑定不符')
            else:
                if any(n.startswith('score_') or n=='write_receipts' for n in names):raise ValueError('发现不完整或异源版本表，保留现场，不覆盖')
                ScoreWriter.initialize_tables(db,info['initial'])
                db.execute('CREATE TABLE score_control(slot INTEGER PRIMARY KEY CHECK(slot=1),binding TEXT NOT NULL,enabled INTEGER NOT NULL CHECK(enabled IN(0,1)))')
                db.execute('INSERT INTO score_control VALUES(1,?,0)',(info['binding'],))
            if before!=existing_fingerprints(db,names):raise ValueError('已有账号业务行发生变化，迁移事务已取消')
        writer=ScoreWriter(root,store,production=True)
        result.update(version=writer.current()[0]['id'],backup=str(backup),existing_rows_preserved=True)
        with store.connect() as db:result['write_enabled']=writer.enabled(db)
        return result


def toggle(config,enable):
    from backend.production import require_database,service_lock
    path=require_database(config)
    with service_lock(path):
        writer=ScoreWriter(path/'score-state',Store(path),production=True)
        with writer.versions.lock(),writer.store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            if enable:writer.idle(db)
            db.execute('UPDATE score_control SET enabled=? WHERE slot=1',(int(enable),))
    return {'write_enabled':enable,'version':writer.current()[0]['id']}


def safe_backup_name(name):
    if name in ('accounts.sqlite3','usage.sqlite3','production.json','score-state/production-scores.json'):return True
    if re.fullmatch(r'score-state/scores/versions/[a-f0-9]{32}/(gauntlet_data|cars|manifest)\.json',name):return True
    return bool(re.fullmatch(r'score-state/backups/[a-f0-9]{32}-(apply|rollback)-[a-f0-9]{12}/(gauntlet_data\.json|cars\.json|manifest\.json|accounts\.sqlite3)',name))


def backup(config):
    from backend.production import require_database,stamp
    path=require_database(config);writer=ScoreWriter(path/'score-state',Store(path),production=True)
    directory=path/'backups';directory.mkdir(exist_ok=True)
    temp_db=directory/('.snapshot-'+secrets.token_hex(8)+'.sqlite3')
    usage_snapshot=directory/('.usage-snapshot-'+secrets.token_hex(8)+'.sqlite3')
    output=directory/('scores-'+stamp()+'.zip');temporary=output.with_suffix('.partial')
    try:
        with writer.versions.lock():
            copy_database(path/'accounts.sqlite3',temp_db)
            with closing(sqlite3.connect(temp_db)) as db:version=db.execute('SELECT version FROM score_current').fetchone()[0]
            writer.versions.read(version)
            content={'accounts.sqlite3':temp_db,'production.json':path/'production.json','score-state/production-scores.json':writer.lab/'production-scores.json'}
            if (path/'usage.sqlite3').exists():
                from backend.usage_production import snapshot
                snapshot(path/'usage.sqlite3',usage_snapshot);content['usage.sqlite3']=usage_snapshot
            for folder in writer.versions.root.iterdir():
                if not re.fullmatch('[a-f0-9]{32}',folder.name):continue
                writer.versions.read(folder.name)
                for n in (*FILES,'manifest.json'):content['score-state/scores/versions/'+folder.name+'/'+n]=folder/n
            for p in (writer.lab/'backups').glob('*/*'):
                name='score-state/backups/'+p.parent.name+'/'+p.name
                if p.is_file() and safe_backup_name(name):content[name]=p
            manifest={'format':'racepick-coherent-scores-v1','current':version,'usage_schema':1 if 'usage.sqlite3' in content else 0,'files':{n:file_hash(v) for n,v in content.items()}}
            with zipfile.ZipFile(temporary,'x',zipfile.ZIP_DEFLATED) as archive:
                for n,v in content.items():archive.write(v,n)
                archive.writestr('backup-manifest.json',encode(manifest))
            verify_backup(temporary)
            with temporary.open('rb+') as stream:os.fsync(stream.fileno())
            os.replace(temporary,output);sync_dir(directory)
        return output
    finally:temp_db.unlink(missing_ok=True);usage_snapshot.unlink(missing_ok=True);temporary.unlink(missing_ok=True)


def verify_backup(source):
    with zipfile.ZipFile(source) as archive:
        names=archive.namelist()
        if len(names)!=len(set(names)) or 'backup-manifest.json' not in names or any(n!='backup-manifest.json' and not safe_backup_name(n) for n in names):raise ValueError('备份文件白名单异常')
        if sum(i.file_size for i in archive.infolist())>1024**3:raise ValueError('备份超过1GiB，需单独恢复方案')
        manifest=json.loads(archive.read('backup-manifest.json'))
        if manifest.get('format')!='racepick-coherent-scores-v1' or set(manifest['files'])!=set(names)-{'backup-manifest.json'}:raise ValueError('备份清单异常')
        if manifest.get('usage_schema',0)!=(1 if 'usage.sqlite3' in manifest['files'] else 0):raise ValueError('统计备份组件声明不匹配')
        for n,h in manifest['files'].items():
            with archive.open(n) as stream:
                if stream_hash(stream)!=h:raise ValueError('备份校验失败：'+n)
    return manifest


def drill(config,source):
    from backend.production import require_database,marker as account_marker
    path=require_database(config);manifest=verify_backup(source)
    with zipfile.ZipFile(source) as archive:
        if json.loads(archive.read('production.json'))!=account_marker(config):raise ValueError('备份站点或主账号标记不匹配')
    base=path/'restore-drills';base.mkdir(exist_ok=True);destination=base/secrets.token_hex(12);destination.mkdir()
    with zipfile.ZipFile(source) as archive:
        for name in manifest['files']:
            p=destination/name;p.parent.mkdir(parents=True,exist_ok=True)
            with archive.open(name) as reader,p.open('xb') as writer:
                for block in iter(lambda:reader.read(1024*1024),b''):writer.write(block)
                writer.flush();os.fsync(writer.fileno())
    (destination/'score-state/backups').mkdir(exist_ok=True)
    _,marker=validate_production_root(destination/'score-state',destination)
    with closing(sqlite3.connect((destination/'accounts.sqlite3').as_uri()+'?mode=ro',uri=True)) as db:
        if db.execute('PRAGMA integrity_check').fetchone()[0]!='ok' or db.execute('PRAGMA foreign_key_check').fetchall():raise ValueError('演练数据库校验失败')
        version=db.execute('SELECT version FROM score_current').fetchone()[0]
        if version!=manifest['current'] or db.execute('SELECT binding FROM score_control').fetchone()[0]!=marker['binding']:raise ValueError('演练版本/绑定不一致')
        rows=db.execute('SELECT manifest FROM score_batches').fetchall()
        pending=db.execute("SELECT count(*) FROM score_batches WHERE state IN ('applying','rolling_back','recovery_required')").fetchone()[0]
        counts={n:db.execute('SELECT count(*) FROM '+n).fetchone()[0] for n in ('users','profiles','submissions')}
        from backend.contribution_production import state as contribution_state
        contribution=contribution_state(db)
        from backend.feedback import state as feedback_state
        feedback=feedback_state(db)
        from backend.notifications import state as notification_state
        notifications=notification_state(db)
    usage_schema=0
    if (destination/'usage.sqlite3').exists():
        from backend.usage import schema
        with closing(sqlite3.connect((destination/'usage.sqlite3').as_uri()+'?mode=ro',uri=True)) as db:
            if schema(db)!=1 or db.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise ValueError('统计恢复快照校验失败')
        usage_schema=1
    versions=Versions(destination/'score-state',lambda p:validate_production_root(p,destination));versions.read(version)
    for row in rows:
        item=json.loads(row[0]);versions.read(item['base']);versions.read(item['target'])
        if item.get('rollback'):versions.read(item['rollback']['version'])
    return {'drill_directory':str(destination),'version':version,'counts':counts,'pending_batches':pending,'active_database_replaced':False,'usage_schema':usage_schema,**contribution,**feedback,**notifications}


def revert_migration(config,source):
    """Only before any batch exists: remove version metadata, preserving all account rows."""
    from backend.production import marker,service_lock
    path=Path(config['data_dir']);root=path/'score-state';journal=path/'score-migration-revert.json'
    if json.loads((path/'production.json').read_text())!=marker(config):raise ValueError('生产库标记不符')
    def record(value):
        temporary=journal.with_suffix('.tmp')
        with temporary.open('w',encoding='utf-8') as stream:stream.write(encode(value));stream.flush();os.fsync(stream.fileno())
        os.replace(temporary,journal);sync_dir(path)
    with service_lock(path):
        previous=json.loads(journal.read_text()) if journal.exists() else None
        if previous and previous['state']=='complete' and not root.exists():
            return {'versioning_removed':True,'account_rows_preserved':True,'retained_scores':str(path/previous['archive']),'backup':previous['backup'],'reused':True}
        if previous and previous['state']=='pending':info=previous
        else:
            writer=ScoreWriter(root,Store(path),production=True)
            with writer.store.connect() as db:
                if writer.enabled(db) or writer.current_id(db)!=writer.marker['initial'] or db.execute('SELECT count(*) FROM score_batches').fetchone()[0] or db.execute('SELECT count(*) FROM write_receipts').fetchone()[0]:raise ValueError('已有批次或写回已开启，禁止撤销迁移')
            source_snapshot(source,writer.marker['seed_hashes']['gauntlet_data.json'],writer.marker['seed_hashes']['cars.json'])
            snapshot=backup(config)
            info={'state':'pending','archive':'retired-score-state-'+secrets.token_hex(12),'binding':writer.marker['binding'],'seed_hashes':writer.marker['seed_hashes'],'backup':str(snapshot)}
            record(info)
        source_snapshot(source,info['seed_hashes']['gauntlet_data.json'],info['seed_hashes']['cars.json'])
        archive=path/info['archive']
        if not re.fullmatch('retired-score-state-[a-f0-9]{24}',info['archive']) or root.resolve().parent!=path.resolve() or archive.resolve().parent!=path.resolve():raise ValueError('撤销迁移路径异常')
        with closing(sqlite3.connect(path/'accounts.sqlite3')) as db, db:
            db.execute('BEGIN IMMEDIATE')
            tables=[r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
            owned=('score_current','score_batches','write_receipts','score_reauth','score_control')
            before=existing_fingerprints(db,[n for n in tables if n not in owned])
            if 'score_control' in tables:
                if db.execute('SELECT binding FROM score_control').fetchone()[0]!=info['binding']:raise ValueError('撤销绑定不符')
                if db.execute('SELECT count(*) FROM score_batches').fetchone()[0]:raise ValueError('撤销期间已有批次，停止')
            for name in owned:db.execute('DROP TABLE IF EXISTS '+name)
            if before!=existing_fingerprints(db,list(before)):raise ValueError('账号行变化，撤销事务已取消')
        if root.exists():
            if archive.exists():raise ValueError('保留目录已存在，不覆盖')
            os.rename(root,archive);sync_dir(path)
        elif not archive.is_dir():raise ValueError('成绩目录不在预期位置，保留现场')
        info['state']='complete';record(info)
        return {'versioning_removed':True,'account_rows_preserved':True,'retained_scores':str(archive),'backup':info['backup']}

def main():
    from backend.production import settings
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['preflight','migrate','enable','disable','backup','verify-backup','restore-drill','revert-migration'])
    parser.add_argument('--config',type=Path,default=Path('/etc/racepick/production.json'))
    parser.add_argument('--source',type=Path);parser.add_argument('--expected-data');parser.add_argument('--expected-cars');parser.add_argument('--backup',type=Path)
    args=parser.parse_args();os.umask(0o077)
    try:
        config=settings(args.config)
        if args.action in ('preflight','migrate'):
            if not args.source:raise ValueError('必须指定--source当前已上线版本目录')
            active=Path('/opt/racepick/current')
            if not active.is_dir() or args.source.resolve()!=active.resolve():raise ValueError('source必须与当前/opt/racepick/current一致；应用版本已变化时先重新核对基线')
            if args.action=='migrate' and (not args.expected_data or not args.expected_cars):raise ValueError('迁移必须明确提供已核对的两份SHA256')
            result=(preflight if args.action=='preflight' else migrate)(config,args.source,args.expected_data,args.expected_cars)
        elif args.action=='revert-migration':
            if not args.source:raise ValueError('必须提供拟回退应用版本的--source，以核对成绩仍完全一致')
            result=revert_migration(config,args.source)
        elif args.action in ('enable','disable'):result=toggle(config,args.action=='enable')
        elif args.action=='backup':result=str(backup(config))
        else:
            if not args.backup:raise ValueError('必须指定--backup')
            result=verify_backup(args.backup) if args.action=='verify-backup' else drill(config,args.backup)
        print(json.dumps(result,ensure_ascii=False,indent=2))
    except (OSError,ValueError,sqlite3.Error,zipfile.BadZipFile) as error:parser.exit(1,str(error)+'\n')

if __name__=='__main__':main()
