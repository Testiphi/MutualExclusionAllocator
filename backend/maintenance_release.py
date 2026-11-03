"""Explicit offline dual-server maintenance release; no HTTP or automatic import."""
from contextlib import closing
import argparse
import json
import os
from pathlib import Path
import secrets
import sqlite3
import time

from backend.score_repository import encode,digest,write_new,sync_dir
from backend.score_versions import ScoreWriter
from backend.global_scores import GlobalScoreWriter,validate_contents
from backend.production import require_database,service_lock,settings
from backend.score_production import backup,verify_backup,existing_fingerprints
from validate_data import validate_data

FILES=('gauntlet_data.json','cars.json','cars.global.json','gauntlet_data.global.json','global-data-manifest.json')

class ReadStore:
    """Preview must never initialize, migrate or write an account database."""
    def __init__(self,path):self.directory=Path(path)
    def connect(self):
        db=sqlite3.connect((self.directory/'accounts.sqlite3').as_uri()+'?mode=ro',uri=True)
        db.row_factory=sqlite3.Row
        return closing(db)

def writers(config):
    root=require_database(config);store=ReadStore(root)
    return root,store,ScoreWriter(root/'score-state',store,True),GlobalScoreWriter(root/'global-score-state',store,True)

def source_files(source,freeze_id):
    from production_release_tools import verify
    source=Path(source).resolve();release=verify(source);provenance=release['provenance']
    if provenance.get('data_source_kind')!='approved_local_freeze' or provenance.get('data_freeze_id')!=freeze_id or provenance.get('data_commit') is not None:
        raise ValueError('必须使用指定本地冻结的完整已校验发布目录')
    raw={n:(source/n).read_bytes() for n in FILES}
    if set(provenance['data_runtime'])!=set(FILES):raise ValueError('冻结文件集合异常')
    for n,value in raw.items():
        declared=provenance['data_runtime'][n]
        if digest(value)!=declared['sha256'] or len(value)!=declared['bytes']:raise ValueError('冻结原字节不匹配：'+n)
    errors,_=validate_data(json.loads(raw[FILES[0]]),json.loads(raw[FILES[1]]))
    if errors:raise ValueError(str(errors))
    validate_contents({n:raw[n] for n in FILES[2:]})
    return raw,{'release_id':release['id'],'code_commit':provenance['code_commit'],
                'freeze_id':freeze_id,'freeze_manifest_sha256':provenance['data_freeze_manifest_sha256'],
                'archive_sha256':provenance['data_source_archive_sha256'],'files':{n:digest(v) for n,v in raw.items()}}

def rows(raw):
    result={}
    for track in json.loads(raw)['tracks']:
        for zone in ('五区','四区'):
            for tier,entries in track.get(zone,{}).items():
                for entry in entries:
                    for car in entry['cars']:
                        key=(track['大地图'],track['小地图'],zone,tier,car['name'],car.get('stars'),bool(car.get('oc')),bool(entry.get('sc')),entry.get('sc_type') or '')
                        if key in result:raise ValueError('重复成绩身份，禁止自动发布：'+encode(key))
                        result[key]={**{k:v for k,v in entry.items() if k!='cars'},'car':car}
    return result

def difference(before,after):
    old,new=rows(before),rows(after);items=[]
    counts={'added':0,'removed':0,'faster':0,'slower':0,'changed':0}
    for key in sorted(old.keys()|new.keys(),key=encode):
        a,b=old.get(key),new.get(key)
        if a==b:continue
        kind='added' if a is None else 'removed' if b is None else 'changed'
        if a and b and isinstance(a.get('time'),(int,float)) and isinstance(b.get('time'),(int,float)):
            kind='faster' if b['time']<a['time'] else 'slower' if b['time']>a['time'] else 'changed'
        counts[kind]+=1;items.append({'key':list(key),'kind':kind,'before':a,'after':b})
    def structure(raw):
        data=json.loads(raw);tracks={}
        for track in data['tracks']:
            key=encode([track['大地图'],track['小地图']])
            if key in tracks:raise ValueError('重复地图身份')
            tracks[key]={'metadata':{k:v for k,v in track.items() if k not in ('五区','四区')},
                         'order':[[zone,[[tier,[{k:v for k,v in e.items() if k!='time'} for e in entries]]
                                  for tier,entries in track.get(zone,{}).items()]] for zone in ('五区','四区') if zone in track]}
        return {k:v for k,v in data.items() if k!='tracks'},list(tracks),tracks
    a_meta,a_order,a_tracks=structure(before);b_meta,b_order,b_tracks=structure(after)
    layout={'metadata':{'before':a_meta,'after':b_meta} if a_meta!=b_meta else None,
            'track_order':{'before':a_order,'after':b_order} if a_order!=b_order else None,
            'tracks':[{'map':json.loads(k),'before':a_tracks.get(k),'after':b_tracks.get(k)}
                      for k in sorted(a_tracks.keys()|b_tracks.keys()) if a_tracks.get(k)!=b_tracks.get(k)]}
    return {'before_keys':len(old),'after_keys':len(new),'counts':counts,'items':items,'layout_changes':layout}

def catalog_diff(before,after):
    a,b=json.loads(before),json.loads(after)
    old={c['title']:c for c in a['cars']};new={c['title']:c for c in b['cars']}
    return {'cars':[{'title':k,'before':old.get(k),'after':new.get(k)} for k in sorted(old.keys()|new.keys()) if old.get(k)!=new.get(k)],
            'other_fields':[{'field':k,'before':a.get(k),'after':b.get(k)} for k in sorted(a.keys()|b.keys()) if k!='cars' and a.get(k)!=b.get(k)]}

def preview(config,source,freeze_id):
    target,provenance=source_files(source,freeze_id)
    root,store,cn,gl=writers(config)
    with store.connect() as db:
        db.execute('BEGIN')
        cn.idle(db);gl.idle(db)
        bases={'cn':cn.current_id(db),'global':gl.current_id(db)}
        controls={n:dict(db.execute('SELECT * FROM '+n+' WHERE slot=1').fetchone()) for n in ('score_control','global_score_control')}
    _,national=cn.versions.read(bases['cn']);_,international=gl.versions.read(bases['global'])
    body={'schema':1,'kind':'racepick-maintenance-release','source':provenance,
          'account_binding':digest((root/'production.json').read_bytes()),'bases':bases,'controls':controls,
          'base_hashes':{n:digest(v) for n,v in {**national,**international}.items()},
          'scores':{'cn':difference(national[FILES[0]],target[FILES[0]]),'global':difference(international[FILES[3]],target[FILES[3]])},
          'catalogs':{'cn':catalog_diff(national[FILES[1]],target[FILES[1]]),'global':catalog_diff(international[FILES[2]],target[FILES[2]])}}
    body['digest']=digest(encode(body).encode());return body

def plan_digest(plan):return digest(encode({k:v for k,v in plan.items() if k!='digest'}).encode())

def register(path,key,value,plan):
    marker=json.loads(path.read_bytes())
    if value==marker[key]:return
    marker.setdefault('maintenance_catalogs',{}).setdefault(value,{'schema':1,'plan':plan['digest'],
        'freeze_id':plan['source']['freeze_id'],'freeze_manifest_sha256':plan['source']['freeze_manifest_sha256']})
    temporary=path.with_name('.catalog-'+secrets.token_hex(12))
    write_new(temporary,encode(marker).encode());os.chmod(temporary,path.stat().st_mode & 0o777)
    if os.name=='posix':os.chown(temporary,path.stat().st_uid,path.stat().st_gid)
    os.replace(temporary,path);sync_dir(path.parent)

def version_permissions(writer,identity,base):
    """Root-invoked release must remain readable by the existing service owner."""
    folder=writer.versions.root/identity;old=writer.versions.root/base
    for target in [*folder.iterdir(),folder]:
        template=old/target.name if target!=folder else old
        info=template.stat();os.chmod(target,info.st_mode & 0o777)
        if os.name=='posix':os.chown(target,info.st_uid,info.st_gid)
    sync_dir(folder)

def checkpoint(name):pass  # Test-only seam; no CLI fault injection.

def require_owner(root):
    if os.name=='posix' and os.geteuid()!=(root/'accounts.sqlite3').stat().st_uid:
        raise ValueError('请以现有账号库owner运行维护发布，避免root生成服务无法读取的中间文件')

def audit(db,identity):
    if not db.execute("SELECT 1 FROM sqlite_master WHERE name='maintenance_releases'").fetchone():return None
    row=db.execute('SELECT receipt FROM maintenance_releases WHERE id=?',(identity,)).fetchone()
    return json.loads(row[0]) if row else None

def apply(config,source,plan,expected_digest):
    if plan.get('digest')!=expected_digest or plan_digest(plan)!=expected_digest:raise ValueError('批准计划SHA不匹配')
    root=require_database(config)
    require_owner(root)
    with service_lock(root):
        root,store,cn,gl=writers(config)
        with store.connect() as db:
            previous=audit(db,expected_digest)
            if previous:
                if previous['state']!='applied' or {s:w.current_id(db) for s,w in [('cn',cn),('global',gl)]}!=previous['targets']:raise ValueError('此计划已执行或回退且状态已变化；禁止重复发布')
                return {**previous,'idempotent':True}
        if preview(config,source,plan['source']['freeze_id'])!=plan:raise ValueError('基线/规则/开关/源或计划变化，必须重新预览批准')
        point=backup(config);verify_backup(point)
        target,_=source_files(source,plan['source']['freeze_id'])
        with cn.versions.lock(),gl.versions.lock(),closing(sqlite3.connect(root/'accounts.sqlite3')) as db,db:
            db.execute('BEGIN IMMEDIATE');cn.idle(db);gl.idle(db)
            if {s:w.current_id(db) for s,w in [('cn',cn),('global',gl)]}!=plan['bases']:raise ValueError('活动版本变化')
            names=[r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'") if r[0] not in ('score_current','global_score_current','maintenance_releases')]
            before=existing_fingerprints(db,names)
            register(root/'score-state/production-scores.json','cars_sha256',digest(target['cars.json']),plan)
            catalog=json.loads(target['cars.global.json'])['_meta']['catalog_payload_sha256']
            register(root/'global-score-state/global-scores.json','catalog_payload_sha256',catalog,plan)
            checkpoint('registered')
            targets={'cn':cn.versions.create({n:target[n] for n in FILES[:2]},plan['bases']['cn'],'maintenance-freeze',expected_digest),
                     'global':gl.versions.create({n:target[n] for n in FILES[2:]},plan['bases']['global'],'maintenance-freeze',expected_digest)}
            version_permissions(cn,targets['cn'],plan['bases']['cn']);version_permissions(gl,targets['global'],plan['bases']['global'])
            db.execute('UPDATE score_current SET version=? WHERE slot=1',(targets['cn'],));checkpoint('cn-pointer')
            db.execute('UPDATE global_score_current SET version=? WHERE slot=1',(targets['global'],))
            receipt={'schema':1,'id':expected_digest,'state':'applied','applied_at':int(time.time()),'plan':plan,
                     'bases':plan['bases'],'targets':targets,'backup':str(point),'backup_sha256':digest(point.read_bytes()),'existing_rows_preserved':True}
            db.execute('CREATE TABLE IF NOT EXISTS maintenance_releases(id TEXT PRIMARY KEY,receipt TEXT NOT NULL)')
            db.execute('INSERT INTO maintenance_releases VALUES(?,?)',(expected_digest,encode(receipt)))
            if existing_fingerprints(db,names)!=before:raise ValueError('原业务行发生非预期变化，事务回滚')
            checkpoint('before-commit')
        _,_,cn,gl=writers(config)
        for writer in (cn,gl):writer.current()
        return receipt

def rollback(config,identity,expected_receipt):
    root=require_database(config)
    require_owner(root)
    with service_lock(root):
        root,store,cn,gl=writers(config)
        with store.connect() as db:
            receipt=audit(db,identity)
            if not receipt:raise ValueError('找不到本次维护发布审计')
            if digest(encode(receipt).encode())!=expected_receipt:raise ValueError('回退回执SHA不匹配')
            if receipt['state']!='applied':raise ValueError('发布已回退')
            cn.idle(db);gl.idle(db)
            if {s:w.current_id(db) for s,w in [('cn',cn),('global',gl)]}!=receipt['targets']:raise ValueError('发布后有新成绩版本，禁止回退覆盖')
        point=backup(config);verify_backup(point)
        with cn.versions.lock(),gl.versions.lock(),closing(sqlite3.connect(root/'accounts.sqlite3')) as db,db:
            db.execute('BEGIN IMMEDIATE');cn.idle(db);gl.idle(db)
            if {s:w.current_id(db) for s,w in [('cn',cn),('global',gl)]}!=receipt['targets']:raise ValueError('回退基线变化')
            names=[r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'") if r[0] not in ('score_current','global_score_current','maintenance_releases')]
            before=existing_fingerprints(db,names)
            for s,w in [('cn',cn),('global',gl)]:
                w.versions.read(receipt['bases'][s])
                db.execute('UPDATE '+w.current_table+' SET version=? WHERE slot=1',(receipt['bases'][s],))
            receipt.update(state='reverted',reverted_at=int(time.time()),rollback_backup=str(point),rollback_backup_sha256=digest(point.read_bytes()))
            db.execute('UPDATE maintenance_releases SET receipt=? WHERE id=?',(encode(receipt),identity))
            if existing_fingerprints(db,names)!=before:raise ValueError('回退时原业务行发生变化，事务回滚')
        return receipt

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['preview','apply','status','rollback'])
    p.add_argument('--config',type=Path,required=True);p.add_argument('--source',type=Path);p.add_argument('--freeze-id')
    p.add_argument('--plan',type=Path);p.add_argument('--expected-plan');p.add_argument('--id');p.add_argument('--expected-receipt')
    p.add_argument('--confirm-all-differences',action='store_true');p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists():p.error('输出已存在，不覆盖证据')
    config=settings(a.config)
    if a.action=='preview':
        if not a.source or not a.freeze_id:p.error('preview需要--source/--freeze-id')
        result=preview(config,a.source,a.freeze_id)
    elif a.action=='apply':
        if not a.source or not a.plan or not a.expected_plan or not a.confirm_all_differences:p.error('apply需要源/计划/批准摘要及全部差异确认')
        result=apply(config,a.source,json.loads(a.plan.read_bytes()),a.expected_plan)
    elif a.action=='rollback':
        if not a.id or not a.expected_receipt:p.error('rollback需要明确id及当前回执SHA')
        result=rollback(config,a.id,a.expected_receipt)
    else:
        if not a.id:p.error('status需要id')
        with ReadStore(require_database(config)).connect() as db:result=audit(db,a.id)
        if result is None:raise ValueError('未找到该发布')
    write_new(a.output,(json.dumps(result,ensure_ascii=False,indent=2)+'\n').encode())
    canonical={k:v for k,v in result.items() if k!='idempotent'}
    print(json.dumps({'output':str(a.output),'plan_or_receipt_sha256':plan_digest(result) if a.action=='preview' else digest(encode(canonical).encode()),'state':result.get('state','preview')}))

if __name__=='__main__':main()
