"""International runtime versions; reuse the national transaction/recovery workflow.

Only an explicitly provisioned state directory is writable. Maintenance inputs,
workbooks and the application's bundled JSON are read-only seeds.
"""
from copy import deepcopy
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import tempfile
import time
from fastapi import HTTPException
from backend.score_repository import Versions, encode, digest, write_new, sync_dir, validate_lab
from backend.score_versions import ScoreWriter, reject, LOADED_ENGINE, LOADED_EXTRA
from backend.submissions import Score, normalize, comparison, identity
from backend.score_scopes import global_source
from tools.build_global_data import validate_global_bundle, canonical_bytes, file_bytes

FILES=('cars.global.json','gauntlet_data.global.json','global-data-manifest.json')

def validate_root(root,accounts,production=False):
    root=Path(root).absolute();accounts=Path(accounts).absolute()
    expected=accounts/'global-score-state' if production else accounts.parent/'global-score-state'
    if root!=expected or root.resolve()!=root:raise ValueError('国际成绩状态路径或账号绑定无效')
    if not root.is_dir() or not (root/'global-scores.json').is_file():raise ValueError('国际成绩状态尚未显式初始化')
    if not production:validate_lab(accounts.parent,accounts)
    marker=json.loads((root/'global-scores.json').read_text(encoding='utf-8'))
    if marker.get('kind')!='racepick-global-scores-v1' or marker.get('production')!=production:raise ValueError('国际成绩标记无效')
    account_marker=json.loads((accounts/'production.json' if production else accounts.parent/'lab.json').read_text(encoding='utf-8'))
    if marker.get('account_marker')!=account_marker:raise ValueError('国际成绩绑定到其他账号库')
    for part in [root,*root.rglob('*')]:
        if part.is_symlink() or part.resolve()!=part or (part.is_file() and part.stat().st_nlink!=1):raise ValueError('国际成绩目录不能含链接')
    for part in ('scores/versions','backups'):
        if not (root/part).is_dir():raise ValueError('国际成绩目录不完整')
    return root,marker

def validate_contents(contents):
    catalog,data,manifest=(json.loads(contents[n]) for n in FILES)
    validate_global_bundle(catalog,data,manifest,raw_files=contents)
    return catalog,data,manifest

class GlobalVersions(Versions):
    def create(self,contents,parent,kind,batch=None):
        validate_contents(contents)
        body={'schema':1,'server':'global','parent':parent,'kind':kind,'batch':batch,'created_at':int(time.time()),'nonce':secrets.token_hex(16),'files':{n:digest(contents[n]) for n in FILES}}
        vid=digest(encode(body).encode())[:32];body['id']=vid
        folder=Path(tempfile.mkdtemp(prefix='.building-',dir=self.root))
        for name in FILES:write_new(folder/name,contents[name])
        write_new(folder/'manifest.json',encode(body).encode());sync_dir(folder);os.rename(folder,self.root/vid);sync_dir(self.root)
        return vid
    def read(self,vid):
        if not re.fullmatch('[a-f0-9]{32}',vid):raise ValueError('国际成绩版本ID无效')
        _,marker=self.validator(self.lab);folder=self.root/vid
        if folder.is_symlink() or folder.resolve()!=folder:raise ValueError('国际成绩版本路径无效')
        info=json.loads((folder/'manifest.json').read_text(encoding='utf-8'));contents={n:(folder/n).read_bytes() for n in FILES}
        if info.get('server')!='global' or info.get('schema')!=1 or info.get('id')!=vid or digest(encode({k:v for k,v in info.items() if k!='id'}).encode())[:32]!=vid or set(info.get('files',{}))!=set(FILES):raise ValueError('国际成绩版本清单无效')
        if any(digest(contents[n])!=info['files'][n] for n in FILES):raise ValueError('国际成绩版本被修改')
        catalog,_,_=validate_contents(contents)
        if catalog['_meta']['catalog_payload_sha256']!=marker['catalog_payload_sha256']:raise ValueError('国际车辆规则与冻结基线不一致')
        return info,contents

def provision(root,accounts,source,production=False):
    root=Path(root).absolute();accounts=Path(accounts).absolute()
    expected=accounts/'global-score-state' if production else accounts.parent/'global-score-state'
    if root!=expected or root.exists():raise ValueError('国际成绩初始化目标已存在或不合法')
    raw={n:(Path(source)/n).read_bytes() for n in FILES};catalog,_,manifest=validate_contents(raw)
    staging=root.parent/('global-score-staging-'+secrets.token_hex(12));staging.mkdir()
    for part in ('scores/versions','backups'):(staging/part).mkdir(parents=True)
    vid=GlobalVersions(staging).create(raw,None,'initial')
    account_marker=json.loads((accounts/'production.json' if production else accounts.parent/'lab.json').read_text(encoding='utf-8'))
    marker={'kind':'racepick-global-scores-v1','production':production,'account_marker':account_marker,'binding':secrets.token_hex(16),'initial':vid,'catalog_payload_sha256':catalog['_meta']['catalog_payload_sha256'],'seed_hashes':{n:digest(raw[n]) for n in FILES},'seed_dataset_version':manifest['_meta']['dataset_version']}
    write_new(staging/'global-scores.json',encode(marker).encode());sync_dir(staging);os.rename(staging,root);sync_dir(root.parent)
    return validate_root(root,accounts,production)

def rebind(catalog,data,manifest):
    parent_version=manifest['_meta']['dataset_version']
    catalog={k:v for k,v in deepcopy(catalog).items() if k!='_meta'};data={k:v for k,v in deepcopy(data).items() if k!='_meta'}
    binding={'server_id':'global','schema_version':1,'catalog_payload_sha256':digest(canonical_bytes(catalog)),'scores_payload_sha256':digest(canonical_bytes(data))}
    meta={**binding,'dataset_version':digest(canonical_bytes(binding)),'manifest_file':FILES[2]}
    catalog={'_meta':deepcopy(meta),**catalog};data={'_meta':deepcopy(meta),**data};manifest=deepcopy(manifest)
    manifest['_meta']=deepcopy(meta);manifest['runtime_origin']={'kind':'reviewed-submissions','parent_dataset_version':parent_version}
    entries=[e for t in data['tracks'] for e in t['五区']['理论']]
    oc=sum(bool(e['cars'][0].get('oc')) for e in entries);sc=sum(bool(e.get('sc')) for e in entries)
    manifest['counts']={'physical_cars':len(catalog['cars']),'tracks':len(data['tracks']),'covered_tracks':sum(bool(t['五区']['理论']) for t in data['tracks']),'score_entries':len(entries),'non_oc_entries':len(entries)-oc,'oc_entries':oc,'special_entries':sc,'normal_entries':len(entries)-sc}
    raw={FILES[0]:file_bytes(catalog),FILES[1]:file_bytes(data)}
    manifest['files']={name:{'sha256':digest(raw[name]),'bytes':len(raw[name]),'payload_sha256':meta[field]} for name,field in [(FILES[0],'catalog_payload_sha256'),(FILES[1],'scores_payload_sha256')]}
    raw[FILES[2]]=file_bytes(manifest);validate_contents(raw);return raw

def preview(rows,contents,source):
    catalog,data,manifest=validate_contents(contents);updated=deepcopy(data)
    result={'version':1,'server':'global','read_only':True,'write_authorized':False,'source':source,'state':'ready','items':[],'actual_changes':[],'errors':[],'changes':{'version':1,'structure':[],'changes':[]},'summary':{k:0 for k in ('new','placeholder','updated','slower','faster','ordinary_mirrors','unchanged','conflicts')}}
    seen=set()
    for row in rows:
        payload=json.loads(row['accepted_payload']);candidate=normalize(Score(**payload),data,catalog)
        if candidate.get('server','cn')!='global' or candidate['unlisted']:reject('国际服批次含其他服别或未收录规则')
        target=identity(candidate)
        if target in seen:reject('批次内目标重复')
        seen.add(target);comp=comparison(candidate,data)
        track=next(t for t in updated['tracks'] if (t['大地图'],t['小地图'])==(candidate['big'],candidate['small']))
        entries=track[candidate['zone']][candidate['tier']]
        matching=[e for e in entries if e['cars'][0]['name']==candidate['car'] and bool(e['cars'][0].get('oc'))==candidate['oc'] and e['cars'][0].get('stars')==candidate['stars'] and bool(e.get('sc'))==bool(candidate['route']) and (not candidate['route'] or e.get('sc_type')==candidate['route'])]
        old=deepcopy(matching[0]) if matching else None
        kind='unchanged' if comp['kind']=='same' else 'new' if comp['old'] is None else 'update'
        item={'submission_id':row['id'],'revision':row['revision'],'accepted_hash':digest(row['accepted_payload'].encode()),'accepted_payload':candidate,'target':{k:candidate[k] for k in ('server','big','small','zone','tier','car','stars','route','oc')},'kind':kind,'old':comp['old'],'new':float(candidate['time']),'slower':comp['kind']=='slower','faster':comp['kind']=='faster'}
        result['items'].append(item);result['summary']['unchanged' if kind=='unchanged' else 'new' if kind=='new' else 'updated']+=1
        if kind=='unchanged':continue
        for field in ('slower','faster'):result['summary'][field]+=int(item[field])
        entry=deepcopy(old) if old else {'cars':[{'name':candidate['car']}]}
        if candidate['oc']:entry['cars'][0]['oc']=True
        if candidate['route']:entry.update(sc=True,sc_type=candidate['route'])
        entry['time']=float(candidate['time'])
        if matching:entries[entries.index(matching[0])]=entry
        else:entries.append(entry)
        entries.sort(key=lambda e:(e['time'],e['cars'][0]['name'],bool(e['cars'][0].get('oc')),bool(e.get('sc')),e.get('sc_type') or ''))
        effect={'target':item['target'],'origin':'direct','submission_ids':[row['id']],'kind':kind,'old':item['old'],'new':item['new'],'before_entry':old,'after_entry':entry}
        result['actual_changes'].append(effect);result['changes']['changes'].append(effect)
    raw=rebind(catalog,updated,manifest);result['validation']='passed';return result,raw

class GlobalScoreWriter(ScoreWriter):
    server='global';current_table='global_score_current';batches_table='global_score_batches';files=FILES
    def __init__(self,root,store,production=False):
        self.production=production;self.store=store;self.lab,self.marker=validate_root(root,store.directory,production)
        self.versions=GlobalVersions(self.lab,lambda p:validate_root(p,store.directory,production))
        with store.connect() as db:
            control=db.execute('SELECT binding FROM global_score_control WHERE slot=1').fetchone()
            if not control or control['binding']!=self.marker['binding']:raise ValueError('国际成绩账号绑定不一致，需显式迁移')
        self.current()
    def current(self):
        with self.store.connect() as db:vid=self.current_id(db)
        info,raw=self.versions.read(vid);catalog=json.loads(raw[FILES[0]])
        if catalog['_meta']['catalog_payload_sha256']!=self.marker['catalog_payload_sha256']:reject('本阶段禁止修改国际车辆规则')
        return info,raw
    def enabled(self,db):
        return super().enabled(db) and bool(db.execute('SELECT enabled FROM global_score_control WHERE slot=1').fetchone()[0])
    def prepare(self,actor,body):
        with self.versions.lock(),self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE');self.idle(db);self.writable(db);self.tools()
            fingerprint=digest(encode(body.model_dump()).encode());old=db.execute(f'SELECT id,request_hash FROM {self.batches_table} WHERE actor=? AND request_key=?',(actor,body.request_key)).fetchone()
            if old:
                if old['request_hash']!=fingerprint:reject('请求标识已用于其他选择')
                row,m=self.get(db,old['id']);return {**m,'state':row['state']}
            rows=self.selected(db,body.items);base=self.current_id(db);_,raw=self.versions.read(base)
            result,target_raw=preview(rows,raw,{'version':base,'server':'global','data_sha256':digest(raw[FILES[1]]),'cars_sha256':digest(raw[FILES[0]])})
            if not result['changes']['changes']:reject('没有有效改动')
            bid=secrets.token_hex(16);target=self.versions.create(target_raw,base,'apply',bid)
            m={'id':bid,'server':'global','actor':actor,'created_at':int(time.time()),'base':base,'target':target,'result':result,'engine':LOADED_ENGINE,'extra':LOADED_EXTRA,'events':[]};m['digest']=digest(encode(m).encode())
            db.execute(f'INSERT INTO {self.batches_table} VALUES(?,?,?,?,?,?)',(bid,actor,body.request_key,fingerprint,'prepared',encode(m)))
            return {**m,'state':'prepared','stale_reasons':[]}
    def fresh(self,db,m):
        self.tools()
        if m['engine']!=LOADED_ENGINE or m['extra']!=LOADED_EXTRA or self.current_id(db)!=m['base']:reject('版本或工具变化，请重新预览')
        from backend.previews import Pick
        rows=self.selected(db,[Pick(id=i['submission_id'],revision=i['revision']) for i in m['result']['items']])
        if any(digest(r['accepted_payload'].encode())!=i['accepted_hash'] for r,i in zip(rows,m['result']['items'])):reject('拟采纳内容变化')
        _,raw=self.versions.read(m['base']);target,target_raw=self.versions.read(m['target'])
        result,expected=preview(rows,raw,m['result']['source'])
        if target['parent']!=m['base'] or expected!=target_raw:reject('候选版本来源或内容变化')

def initialize(root,store,source,production=False,verify_existing=None):
    root=Path(root)
    if not root.exists():provision(root,store.directory,source,production)
    _,marker=validate_root(root,store.directory,production)
    with store.connect() as db:
        db.execute('BEGIN IMMEDIATE')
        existing=db.execute("SELECT 1 FROM sqlite_master WHERE name='global_score_control'").fetchone()
        if existing:
            if db.execute('SELECT binding FROM global_score_control WHERE slot=1').fetchone()[0]!=marker['binding']:raise ValueError('国际成绩已有其他绑定')
        else:
            GlobalScoreWriter.initialize_tables(db,marker['initial'])
            db.execute('CREATE TABLE global_score_control(slot INTEGER PRIMARY KEY CHECK(slot=1),binding TEXT NOT NULL,enabled INTEGER NOT NULL CHECK(enabled IN (0,1)))')
            db.execute('INSERT INTO global_score_control VALUES(1,?,?)',(marker['binding'],int(not production)))
        if verify_existing:verify_existing(db)
    return GlobalScoreWriter(root,store,production)

@contextmanager
def backup_lock(accounts):
    root=Path(accounts)/'global-score-state'
    if not root.exists():yield;return
    versions=GlobalVersions(root,lambda p:validate_root(p,accounts,True))
    with versions.lock():yield

def backup_files(accounts,db):
    from backend.global_score_production import state
    status=state(db)
    if not status['global_score_schema']:return {},status
    root,marker=validate_root(Path(accounts)/'global-score-state',accounts,True)
    if db.execute('SELECT binding FROM global_score_control WHERE slot=1').fetchone()[0]!=marker['binding']:raise ValueError('国际备份账号绑定无效')
    versions=GlobalVersions(root,lambda p:validate_root(p,accounts,True));versions.read(status['global_score_version'])
    content={'global-score-state/global-scores.json':root/'global-scores.json'}
    for folder in versions.root.iterdir():
        if not re.fullmatch('[a-f0-9]{32}',folder.name):continue
        versions.read(folder.name)
        for name in (*FILES,'manifest.json'):content['global-score-state/scores/versions/'+folder.name+'/'+name]=folder/name
    for folder in (root/'backups').iterdir():
        if not folder.is_dir() or not re.fullmatch('[a-f0-9]{32}-(apply|rollback)-[a-f0-9]{12}',folder.name):raise ValueError('国际备份目录名异常')
        manifest=json.loads((folder/'manifest.json').read_text(encoding='utf-8'))
        for name in (*FILES,'accounts.sqlite3'):
            if digest((folder/name).read_bytes())!=manifest['files'][name]:raise ValueError('国际批次备份校验失败')
        for name in (*FILES,'accounts.sqlite3','manifest.json'):content['global-score-state/backups/'+folder.name+'/'+name]=folder/name
    for row in db.execute('SELECT manifest FROM global_score_batches'):
        item=json.loads(row[0]);versions.read(item['base']);versions.read(item['target'])
        if item.get('rollback'):versions.read(item['rollback']['version'])
    return content,status
