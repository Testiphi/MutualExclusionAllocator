"""Read-only accepted-submission previews. Source files are never opened for writing."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import secrets
import time
from typing import Literal

from fastapi import HTTPException, Request
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel, ConfigDict, Field, StrictInt

from apply_changes import apply_changes
from format_json import format_data
from validate_data import validate_data
from backend.submissions import Score, normalize

ROOT=Path(__file__).resolve().parents[1]
ENGINE_FILES=('apply_changes.py','format_json.py','data_tools.py','validate_data.py','backend/previews.py','backend/submissions.py')


def sha(data):return hashlib.sha256(data).hexdigest()
def encoded(value):return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)
def changes_content(result):
    return json.dumps({**result['changes'],'read_only_preview':True,'write_authorized':False,'preview_id':result['id']},ensure_ascii=False,indent=2,sort_keys=True)+'\n'
def engine_hashes():return {name:sha((ROOT/name).read_bytes()) for name in ENGINE_FILES}
LOADED_ENGINE=engine_hashes()
LOADED_TOOL_TEXT={name:sha((ROOT/name).read_text(encoding='utf-8-sig').encode()) for name in ENGINE_FILES[:4]}


def migrate_previews(db):
    version=db.execute('SELECT max(version) FROM schema_version').fetchone()[0]
    if version==6:return
    if version!=5:raise RuntimeError('只读预览迁移需要数据库v5')
    db.execute('''CREATE TABLE IF NOT EXISTS preview_batches(
        id TEXT PRIMARY KEY, actor_id TEXT NOT NULL REFERENCES users(id),
        request_key TEXT NOT NULL, request_hash TEXT NOT NULL, created_at INTEGER NOT NULL,
        result_json TEXT NOT NULL, preview_json TEXT,
        UNIQUE(actor_id,request_key))''')
    db.execute('INSERT INTO schema_version VALUES (6)')


class Pick(BaseModel):
    model_config=ConfigDict(extra='forbid')
    id:str=Field(pattern=r'^[a-f0-9]{32}$')
    revision:StrictInt=Field(ge=1)


class Generate(BaseModel):
    model_config=ConfigDict(extra='forbid')
    request_key:str=Field(pattern=r'^[A-Za-z0-9_-]{16,80}$')
    items:list[Pick]=Field(min_length=1,max_length=50)


def load_source(directory):
    if directory is None:raise HTTPException(503,'未配置正式库预览来源；请用 --preview-source 显式指定维护仓库目录')
    try:
        raw_data=(directory/'gauntlet_data.json').read_bytes()
        raw_cars=(directory/'cars.json').read_bytes()
        data=json.loads(raw_data.decode('utf-8-sig'))
        cars=json.loads(raw_cars.decode('utf-8-sig'))
    except (OSError,ValueError):raise HTTPException(409,'正式库文件不可读或JSON格式错误；未生成预览') from None
    try:
        tools={name:sha((directory/name).read_text(encoding='utf-8-sig').encode()) for name in ENGINE_FILES[:4] if (directory/name).is_file()}
    except (OSError,ValueError):raise HTTPException(409,'正式维护工具无法核对') from None
    return data,cars,{'directory':str(directory),'data_sha256':sha(raw_data),'cars_sha256':sha(raw_cars),'tool_text_sha256':tools}


def key(change):
    return (change['big'],change['small'],change['zone'],change['tier'],change['car'],change['stars'],change['sc'],change['sc_type'])


def flatten(data):
    result={}
    for track in data['tracks']:
        for zone in ('五区','四区'):
            for tier in ('理论','高手','普通','自动'):
                for entry in track[zone][tier]:
                    car=entry['cars'][0]
                    k=(track['大地图'],track['小地图'],zone,tier,car['name'],car.get('stars'),bool(entry.get('sc')),entry.get('sc_type') if entry.get('sc') else None)
                    if k in result:raise ValueError('正式库存在重复目标键')
                    result[k]=entry
    return result


def target_fields(k):return dict(zip(('big','small','zone','tier','car','stars','sc','sc_type'),k))
def value(entry,tier):return None if entry is None else ('✓' if tier in ('普通','自动') else entry.get('time'))


def build_preview(rows,data,cars,source):
    result={'version':1,'read_only':True,'write_authorized':False,'source':source,
            'engine':LOADED_ENGINE,'state':'ready','items':[],'actual_changes':[],'errors':[],
            'changes':{'version':1,'structure':[],'changes':[]},
            'summary':{'new':0,'placeholder':0,'updated':0,'slower':0,'faster':0,'ordinary_mirrors':0,'unchanged':0,'conflicts':0}}
    try:
        errors,_=validate_data(data,cars)
        if errors:raise ValueError('正式库当前校验失败：'+'；'.join(errors[:20]))
        before=flatten(data)
    except (ValueError,TypeError,KeyError,AttributeError) as error:
        before={};result['errors'].append(str(error));result['state']='blocked'
    seen={};direct={};mirror_sources={}
    for row in rows:
        payload=json.loads(row['accepted_payload']) if row['accepted_payload'] else None
        item={'submission_id':row['id'],'revision':row['revision'],'accepted_hash':sha((row['accepted_payload'] or '').encode()),
              'score':row['review_score'],'review_reason':row['decision_reason'],'accepted_payload':payload}
        result['items'].append(item)
        old_basis=json.loads(row['baseline']) if row['baseline'] else {}
        item['review_basis_changed']=old_basis!={'data':source['data_sha256'],'cars':source['cars_sha256']}
        if result['errors'] and not before:
            item.update(kind='conflict',error='正式库基础校验失败，不能计算此条');result['summary']['conflicts']+=1;continue
        try:
            if payload is None:raise ValueError('缺少拟采纳内容')
            candidate=normalize(Score(**payload),data,cars)
            if candidate['unlisted']:raise ValueError('未收录资料需要先维护规则，不能形成数据改动')
            if candidate['car']!=payload['car']:raise ValueError('车辆身份已变化，请重新审核，不能自动迁移到新昵称')
            change={name:candidate[name] for name in ('big','small','zone','tier','car','stars')}
            change.update(sc=bool(candidate['route']),sc_type=candidate['route'] or None)
            k=key(change)
            if k in seen:
                seen[k].update(kind='conflict',error='批次内多个投稿指向同一目标，请保留一个后重新生成')
                raise ValueError('批次内多个投稿指向同一目标：'+seen[k]['submission_id'])
            seen[k]=item
            entry=before.get(k);old=value(entry,candidate['tier'])
            new='✓' if candidate['tier'] in ('普通','自动') else float(candidate['time'])
            change.update(old=old,new=new,old_present=old is not None,new_present=True)
            change['kind']='added' if old is None else ('faster' if isinstance(new,(int,float)) and new<old else 'slower' if isinstance(new,(int,float)) and new>old else 'changed')
            item.update(target=target_fields(k),old=old,new=new)
            if old==new:
                item['kind']='unchanged';result['summary']['unchanged']+=1;continue
            kind='placeholder' if entry is not None and old is None else 'new' if old is None else 'update'
            item['kind']=kind;item['slower']=change['kind']=='slower';item['faster']=change['kind']=='faster'
            result['summary']['new' if kind=='new' else 'placeholder' if kind=='placeholder' else 'updated']+=1
            if item['slower']:result['summary']['slower']+=1
            if item['faster']:result['summary']['faster']+=1
            change.update(id=len(result['changes']['changes'])+1,accepted=False,submission_id=row['id'])
            result['changes']['changes'].append(change);direct[k]=item
            if candidate['tier']=='高手' and not candidate['route']:
                mk=(k[0],k[1],k[2],'普通',k[4],k[5],False,None)
                mirror_sources.setdefault(mk,[]).append(row['id'])
        except (HTTPException,ValueError,KeyError,TypeError) as error:
            item.update(kind='conflict',error=error.detail if isinstance(error,HTTPException) else str(error))
    for category in ('new','placeholder','updated','slower','faster','unchanged'):result['summary'][category]=0
    for item in result['items']:
        kind=item['kind']
        if kind in ('new','placeholder','unchanged'):result['summary'][kind]+=1
        elif kind=='update':
            result['summary']['updated']+=1
            if item.get('slower'):result['summary']['slower']+=1
            if item.get('faster'):result['summary']['faster']+=1
    result['summary']['conflicts']=sum(i['kind']=='conflict' for i in result['items'])
    if result['errors'] or result['summary']['conflicts']:
        result['state']='blocked';return result,None
    try:
        simulation=deepcopy(result['changes'])
        for c in simulation['changes']:c['accepted']=True
        updated,_=apply_changes(data,simulation,cars)
        after=flatten(updated)
        for k in sorted(set(before)|set(after),key=repr):
            old_entry=before.get(k);new_entry=after.get(k)
            if old_entry==new_entry:continue
            effect={'target':target_fields(k),'old':value(old_entry,k[3]),'new':value(new_entry,k[3]),
                    'before_entry':old_entry,'after_entry':new_entry}
            if k in direct:
                effect.update(origin='direct',submission_ids=[direct[k]['submission_id']],kind=direct[k]['kind'])
                if k in mirror_sources:effect['mirror_contributors']=mirror_sources[k]
            elif k in mirror_sources and old_entry is None and new_entry is not None:
                effect.update(origin='ordinary_mirror',submission_ids=mirror_sources[k],kind='new')
                result['summary']['ordinary_mirrors']+=1
            else:raise ValueError('模拟产生未预期的额外变动：'+repr(k))
            result['actual_changes'].append(effect)
        for k,item in direct.items():
            if value(after.get(k),k[3])!=item['new']:raise ValueError('模拟结果与候选清单不一致')
        preview=format_data(updated)
        result['preview_sha256']=sha(preview.encode('utf-8'))
        result['validation']='passed'
        return result,preview
    except (ValueError,TypeError,KeyError,AttributeError) as error:
        result['state']='blocked';result['errors'].append(str(error));return result,None


def install(app,store,root,user,source_dir=None):
    source=Path(source_dir).resolve() if source_dir is not None else None
    def admin(request):
        actor=user(request)
        if request.headers.get('x-account-id')!=actor['id']:raise HTTPException(401,'账号已变化，请刷新')
        if actor['role'] not in ('admin','superadmin') or not actor['verified']:raise HTTPException(403,'需要已验证的管理员权限')
        return actor

    def selected_rows(db,picks):
        rows=[]
        for pick in picks:
            if hasattr(app.state,'writeback'): app.state.writeback.guard(db,pick.id)
            row=db.execute('SELECT * FROM submissions WHERE id=?',(pick.id,)).fetchone()
            if not row or row['status']!='accepted' or row['revision']!=pick.revision:
                raise HTTPException(409,'所选投稿已变化或不再是已采纳状态，请刷新后重新选择')
            rows.append(row)
        return rows

    def freshness(result):
        reasons=[]
        try:
            if source is None or Path(result['source']['directory'])!=source:reasons.append('正式库预览来源配置已变化')
            _,_,current=load_source(source)
            if current!=result['source']:reasons.append('正式成绩或车辆规则已变化')
            if engine_hashes()!=result['engine']:reasons.append('维护工具版本已变化')
        except (HTTPException,OSError):reasons.append('无法核对正式库或工具版本')
        with store.connect() as db:
            for item in result['items']:
                if hasattr(app.state,'writeback') and db.execute('SELECT 1 FROM write_receipts WHERE submission_id=?',(item['submission_id'],)).fetchone():
                    reasons.append('投稿已有应用或回滚回执：'+item['submission_id'])
                row=db.execute('SELECT revision,status,accepted_payload FROM submissions WHERE id=?',(item['submission_id'],)).fetchone()
                if not row or row['status']!='accepted' or row['revision']!=item['revision'] or sha((row['accepted_payload'] or '').encode())!=item['accepted_hash']:
                    reasons.append('投稿审核版本已变化：'+item['submission_id'])
        return reasons

    def stored(db,bid):
        row=db.execute('SELECT * FROM preview_batches WHERE id=?',(bid,)).fetchone()
        if not row:raise HTTPException(404,'预览不存在')
        return row

    @app.get('/data-previews')
    def page():return FileResponse(root/'data_previews.html')

    @app.get('/api/admin/preview-source')
    def info(request:Request):
        admin(request)
        if source is None:return {'configured':False}
        _,_,basis=load_source(source)
        return {'configured':True,'source':basis,'read_only':True}

    @app.get('/api/admin/accepted-submissions')
    def candidates(request:Request,offset:int=0):
        admin(request)
        if offset<0:raise HTTPException(422,'页码无效')
        with store.connect() as db:
            pending="status='accepted'"
            if hasattr(app.state,'writeback'): pending+=" AND NOT EXISTS(SELECT 1 FROM write_receipts WHERE submission_id=submissions.id)"
            total=db.execute('SELECT count(*) FROM submissions WHERE '+pending).fetchone()[0]
            rows=db.execute('SELECT id,revision,accepted_payload,review_score,decision_reason FROM submissions WHERE '+pending+' ORDER BY updated_at DESC,id DESC LIMIT 50 OFFSET ?',(offset,)).fetchall()
        return {'total':total,'items':[{**dict(r),'accepted_payload':json.loads(r['accepted_payload']) if r['accepted_payload'] else None} for r in rows]}

    @app.get('/api/admin/previews')
    def listing(request:Request):
        admin(request)
        with store.connect() as db:rows=db.execute('SELECT id,created_at,result_json FROM preview_batches ORDER BY created_at DESC,id DESC LIMIT 30').fetchall()
        return {'items':[{'id':r['id'],'created_at':r['created_at'],'generated_state':json.loads(r['result_json'])['state']} for r in rows]}

    @app.post('/api/admin/previews')
    def generate(body:Generate,request:Request):
        actor=admin(request)
        if len({i.id for i in body.items})!=len(body.items):raise HTTPException(422,'不能重复选择同一投稿')
        if engine_hashes()!=LOADED_ENGINE:raise HTTPException(409,'维护工具代码已变化，请重启本地服务后生成预览')
        fingerprint=sha(encoded(body.model_dump()).encode())
        with store.connect() as db:
            old=db.execute('SELECT id,request_hash FROM preview_batches WHERE actor_id=? AND request_key=?',(actor['id'],body.request_key)).fetchone()
            if old:
                if old['request_hash']!=fingerprint:raise HTTPException(409,'请求标识已用于其他选项，请重新生成')
                return {'id':old['id'],'reused':True}
            rows=selected_rows(db,body.items)
        data,cars,basis=load_source(source)
        if any(LOADED_TOOL_TEXT.get(name)!=digest for name,digest in basis['tool_text_sha256'].items()):
            raise HTTPException(409,'正式维护工具与当前服务版本不一致，请同步工具后重启；未生成预览')
        result,preview=build_preview(rows,data,cars,basis)
        _,_,after_basis=load_source(source)
        if basis!=after_basis:raise HTTPException(409,'生成期间正式库变化，未保存预览，请重试')
        if engine_hashes()!=LOADED_ENGINE:raise HTTPException(409,'生成期间工具变化，请重启后重试')
        bid=secrets.token_hex(16);now=int(time.time())
        result.update(id=bid,created_at=now)
        result['changes_sha256']=sha(changes_content(result).encode('utf-8'))
        with store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            fresh=selected_rows(db,body.items)
            if any(a['accepted_payload']!=b['accepted_payload'] for a,b in zip(rows,fresh)):raise HTTPException(409,'生成期间采纳内容变化')
            # Concurrent retries resolve to the same preview instead of adding duplicates.
            old=db.execute('SELECT id,request_hash FROM preview_batches WHERE actor_id=? AND request_key=?',(actor['id'],body.request_key)).fetchone()
            if old:
                if old['request_hash']!=fingerprint:raise HTTPException(409,'请求标识已变化')
                return {'id':old['id'],'reused':True}
            db.execute('INSERT INTO preview_batches VALUES (?,?,?,?,?,?,?)',(bid,actor['id'],body.request_key,fingerprint,now,encoded(result),preview))
        return {'id':bid,'reused':False}

    @app.get('/api/admin/previews/{bid}')
    def detail(bid:str,request:Request):
        admin(request)
        with store.connect() as db:row=stored(db,bid)
        result=json.loads(row['result_json']);reasons=freshness(result)
        return {**result,'generated_state':result['state'],'state':'stale' if reasons else result['state'],'stale_reasons':reasons}

    @app.get('/api/admin/previews/{bid}/download')
    def download(bid:str,request:Request,kind:Literal['changes','preview','manifest']):
        admin(request)
        with store.connect() as db:row=stored(db,bid)
        result=json.loads(row['result_json'])
        if freshness(result):raise HTTPException(409,'预览已过期，请重新生成；未下载旧清单')
        if result['state']!='ready':raise HTTPException(409,'预览存在阻止项，不能下载执行候选文件')
        if kind=='preview':content=row['preview_json'];suffix='preview.json'
        elif kind=='changes':
            content=changes_content(result);suffix='changes.review.json'
        else:content=json.dumps(result,ensure_ascii=False,indent=2)+'\n';suffix='manifest.json'
        return Response(content,media_type='application/json',headers={'Content-Disposition':f'attachment; filename="{bid}.{suffix}"'})
