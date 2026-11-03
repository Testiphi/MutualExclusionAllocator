"""Independent international account garages; no score/catalog/workbook writes."""
import json
import time
from fastapi import HTTPException
from pydantic import BaseModel,ConfigDict,Field,StrictInt,StrictBool

TABLES={'global_profile_schema','profiles_global'}


class GlobalProfileInput(BaseModel):
    model_config=ConfigDict(extra='forbid')
    revision:StrictInt=Field(ge=0)
    cars:list[str]=Field(max_length=500)
    stars:dict[str,StrictInt]=Field(default_factory=dict,max_length=500)
    ocMap:dict[str,StrictBool]=Field(default_factory=dict,max_length=500)


def state(db):
    present={r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")} & TABLES
    if not present:return {'global_profile_schema':0}
    if present!=TABLES or [r[0] for r in db.execute('SELECT version FROM global_profile_schema')]!=[1]:
        raise ValueError('国际账号车库schema不完整或不兼容')
    return {'global_profile_schema':1}


def migrate(store):
    with store.connect() as db:
        db.execute('BEGIN IMMEDIATE')
        if state(db)['global_profile_schema']==1:return {'already_migrated':True}
        db.execute('CREATE TABLE global_profile_schema(version INTEGER PRIMARY KEY)')
        db.execute('''CREATE TABLE profiles_global(user_id TEXT PRIMARY KEY REFERENCES users(id),cars TEXT NOT NULL,
                   stars TEXT NOT NULL,oc_map TEXT NOT NULL,revision INTEGER NOT NULL,updated_at INTEGER NOT NULL)''')
        db.execute('INSERT INTO global_profile_schema VALUES(1)')
    return {'already_migrated':False,'initial_profiles':0}


def require(db):
    if state(db)['global_profile_schema']!=1:raise HTTPException(503,'国际账号云车库尚未显式迁移；本机数据保持')


def get(store,uid):
    with store.connect() as db:
        require(db);row=db.execute('SELECT * FROM profiles_global WHERE user_id=?',(uid,)).fetchone()
    return {'revision':row['revision'] if row else 0,'profile':None if row is None else
            {'cars':json.loads(row['cars']),'stars':json.loads(row['stars']),'ocMap':json.loads(row['oc_map'])}}


def put(store,uid,body,active,known,oc_known):
    if (len(set(body.cars))!=len(body.cars) or any(c not in known for c in body.cars)
            or any(c not in known or n<1 or n>6 for c,n in body.stars.items())
            or any(c not in known or (enabled and c not in oc_known) for c,enabled in body.ocMap.items())):
        raise HTTPException(422,'国际车辆、星级或OC设置无效；不使用国服规则回退')
    with store.connect() as db:
        db.execute('BEGIN IMMEDIATE');active(db);require(db)
        row=db.execute('SELECT revision FROM profiles_global WHERE user_id=?',(uid,)).fetchone()
        revision=row['revision'] if row else 0
        if body.revision!=revision:raise HTTPException(409,'国际账号车库已在其他窗口更新，请加载或明确覆盖')
        revision+=1
        db.execute('INSERT INTO profiles_global VALUES(?,?,?,?,?,?) ON CONFLICT(user_id) DO UPDATE SET cars=excluded.cars,stars=excluded.stars,oc_map=excluded.oc_map,revision=excluded.revision,updated_at=excluded.updated_at',
                   (uid,json.dumps(body.cars,ensure_ascii=False),json.dumps(body.stars,ensure_ascii=False),json.dumps(body.ocMap,ensure_ascii=False),revision,int(time.time())))
    return {'revision':revision}


def migrate_production(config):
    from backend.production import require_database,service_lock,backup
    from backend.app import Store
    from backend.score_production import existing_fingerprints
    path=require_database(config)
    with service_lock(path):
        store=Store(path)
        with store.connect() as db:
            if state(db)['global_profile_schema']==1:return {'already_migrated':True}
            names=[r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
            before=existing_fingerprints(db,names)
        restore_point=backup(config)
        result=migrate(store)
        with store.connect() as db:
            if existing_fingerprints(db,names)!=before:raise ValueError('原业务内容发生非预期变化，停止推进并保全现场')
        return {**result,'backup':str(restore_point),'existing_rows_preserved':True}


if __name__=='__main__':
    import argparse
    from pathlib import Path
    p=argparse.ArgumentParser();p.add_argument('command',choices=['migrate-local','migrate-production'])
    p.add_argument('--data-dir',type=Path);p.add_argument('--config',type=Path);args=p.parse_args()
    if args.command=='migrate-local':
        from backend.score_repository import validate_lab
        from backend.app import Store
        if args.data_dir is None or args.config is not None:p.error('本地迁移只接受--data-dir')
        validate_lab(args.data_dir.parent,args.data_dir)
        if (args.data_dir/'production.json').exists():raise ValueError('禁止通过本地入口迁移正式库')
        print(json.dumps(migrate(Store(args.data_dir))))
    else:
        from backend.production import settings
        if args.config is None or args.data_dir is not None:p.error('生产迁移只接受--config，需停服备份及单独授权')
        print(json.dumps(migrate_production(settings(args.config))))
