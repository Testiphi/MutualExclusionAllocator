"""Read-only score coverage and ledger-derived national viewing rights. No score writes."""
import hashlib
import json
import math
import time
from pathlib import Path
from fastapi import HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, ConfigDict, Field, StrictInt
from data_tools import SC_TYPES, star_limits

COLUMN_LIMIT=48
TABLES=('coverage_schema','coverage_choices','coverage_events')
RULES={'version':1,'first':{'points':50,'valid':5},'full':{'points':150,'valid':15,'high':5},'valid_quality':6,'high_quality':8}

def state(db):
    present={r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")} & set(TABLES)
    if not present:return {'coverage_schema':0,'coverage_counts':{}}
    if present!=set(TABLES):raise ValueError('成绩表权限表不完整')
    if [r[0] for r in db.execute('SELECT version FROM coverage_schema')]!=[1]:raise ValueError('成绩表权限schema不兼容')
    return {'coverage_schema':1,'coverage_counts':{t:db.execute('SELECT count(*) FROM '+t).fetchone()[0] for t in TABLES[1:]}}

def migrate(db):
    if state(db)['coverage_schema']:return
    db.execute('CREATE TABLE coverage_schema(version INTEGER PRIMARY KEY)')
    db.execute('CREATE TABLE coverage_choices(user_id TEXT PRIMARY KEY REFERENCES users(id),map_id TEXT NOT NULL,created_at INTEGER NOT NULL)')
    db.execute('CREATE TABLE coverage_events(id INTEGER PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id),action TEXT NOT NULL,snapshot TEXT NOT NULL,created_at INTEGER NOT NULL)')
    db.execute('INSERT INTO coverage_schema VALUES(1)')

def map_id(big):return hashlib.sha256(('cn:'+big).encode()).hexdigest()[:24]
def identity(p):return tuple(p.get(k) for k in ('big','small','zone','tier','car','stars','route'))
def key(p):return hashlib.sha256(json.dumps(identity(p),ensure_ascii=False).encode()).hexdigest()[:32]
def rights(db,actor):
    result={'level':0,'points':0,'valid':0,'high':0,'chosen':None,'admin':False}
    if not actor or not actor['verified']:return result
    rows=db.execute('SELECT quality_points,bonus FROM contributions WHERE user_id=?',(actor['id'],)).fetchall()
    result.update(points=sum(r[0]+r[1] for r in rows),valid=sum(r[0]>=6 for r in rows),high=sum(r[0]>=8 for r in rows))
    result['admin']=actor['role'] in ('admin','superadmin')
    result['level']=2 if result['admin'] or result['points']>=150 and result['valid']>=15 and result['high']>=5 else 1 if result['points']>=50 and result['valid']>=5 else 0
    choice=db.execute('SELECT map_id FROM coverage_choices WHERE user_id=?',(actor['id'],)).fetchone()
    result['chosen']=choice[0] if choice else None
    return result

def unlocked(access,server,big):return server=='cn' and (access['level']==2 or access['level']==1 and access['chosen']==map_id(big))

def records(track,zone,tier,route):
    result={}
    for entry in track.get(zone,{}).get(tier,[]):
        value=entry.get('time')
        if type(value) not in (int,float) or not math.isfinite(value) or value<=0 or bool(entry.get('sc'))!=bool(route) or (route and entry.get('sc_type')!=route):continue
        for car in entry.get('cars',[]):
            if car.get('oc'):continue
            k=(car['name'],car.get('stars'));result[k]=min(value,result.get(k,value))
    return result

def public_columns(coverage):
    # Choose complementary default-star columns before filters or per-car star choices.
    # Never invent a reference for a row without an actual eligible record.
    remaining=set().union(*coverage.values()) if coverage else set()
    chosen=set()
    while remaining:
        car=min(coverage,key=lambda name:(-len(coverage[name]&remaining),-len(coverage[name]),name.casefold()))
        chosen.add(car);remaining-=coverage[car]
    return chosen

def run_types(track,mode):
    if mode=='normal':return ['']
    types={e.get('sc_type') for z in ('五区','四区') for k in ('理论','高手') for e in track.get(z,{}).get(k,[]) if e.get('sc') and e.get('sc_type') in SC_TYPES}
    if track.get('has_special_route') and track.get('special_route_note') in SC_TYPES:types.add(track['special_route_note'])
    return sorted(types)

def matrix(data,catalog,access,*,server='cn',zone='五区',tier='理论',big='all',route='normal',query='',stars='all',offset=0,gaps=False,star_map=None):
    if server not in ('cn','global') or zone not in ('五区','四区') or tier not in ('理论','高手') or route not in ('normal','special'):raise HTTPException(422,'表格范围无效')
    if server=='global' and (zone!='五区' or tier!='理论'):raise HTTPException(422,'国际服仅提供五区满星理论')
    if stars!='all' and stars not in ('1','2','3','4','5','6'):raise HTTPException(422,'星级无效')
    star_map=star_map or {}
    if len(star_map)>200 or any(type(v) is not int or not 1<=v<=6 or len(k)>80 for k,v in star_map.items()):raise HTTPException(422,'星级选择无效')
    cars=[c for c in catalog['cars'] if c.get('nickname') and zone in c.get('zones',[])]
    bounds={c['nickname']:star_limits(c,zone) for c in cars};counts={c['nickname']:0 for c in cars}
    coverage={c['nickname']:set() for c in cars}
    for c,star in star_map.items():
        if c in bounds and not bounds[c][0]<=star<=bounds[c][1]:raise HTTPException(422,'所选星级不适用于该车和分区')
    for index,track in enumerate(data['tracks']):
        seen=set()
        for run in run_types(track,route):
            for name,star in records(track,zone,tier,run):
                if name not in bounds:continue
                low,high=bounds[name]
                if tier=='理论' and star in (None,high) or tier=='高手' and type(star) is int and low<=star<=high:seen.add(name)
                if tier=='理论' and star in (None,high) or tier=='高手' and star==high:coverage[name].add((index,run))
        for name in seen:counts[name]+=1
    samples=public_columns(coverage)
    # References lead, then coverage; neither changes when filters or stars change.
    cars.sort(key=lambda c:(c['nickname'] not in samples,-counts[c['nickname']],c['nickname'].casefold()))
    candidates=[]
    for c in cars:
        if query.casefold() not in (c['nickname']+' '+c['title']).casefold():continue
        low,high=bounds[c['nickname']]
        chosen=star_map.get(c['nickname'],int(stars) if stars!='all' and low<=int(stars)<=high else high)
        candidates.append({'car':c['nickname'],'title':c['title'],'stars':None if tier=='理论' else chosen,'max_stars':high,'star_options':list(range(low,high+1)) if tier=='高手' else [],'coverage_count':counts[c['nickname']],'public':c['nickname'] in samples})
    offset=min(offset,((len(candidates)-1)//COLUMN_LIMIT)*COLUMN_LIMIT) if candidates else 0
    columns=candidates[offset:offset+COLUMN_LIMIT];rows=[]
    for t in data['tracks']:
        if big!='all' and map_id(t['大地图'])!=big:continue
        for run in run_types(t,route):
            found=records(t,zone,tier,run);cells=[]
            for c in columns:
                target={k:c[k] for k in ('car','stars')};target.update(big=t['大地图'],small=t['小地图'],zone=zone,tier=tier,route=run)
                values=[found[k] for k in ((c['car'],None),(c['car'],c['max_stars'])) if k in found] if tier=='理论' else [found[c['car'],c['stars']]] if (c['car'],c['stars']) in found else []
                value=min(values,default=None)
                is_sample=c['car'] in samples
                visible=unlocked(access,server,t['大地图']) or is_sample
                cells.append({'key':key(target),'status':'empty' if value is None else 'filled','value':value if visible else None,'public':is_sample,'target':target if server=='cn' else None})
            if gaps and not any(c['status']=='empty' for c in cells):continue
            rows.append({'big':t['大地图'],'small':t['小地图'],'route':run,'map_id':map_id(t['大地图']),'cells':cells})
    return {'columns':columns,'rows':rows,'column_total':len(candidates),'column_offset':offset,'column_limit':COLUMN_LIMIT}

class CoverageView(BaseModel):
    model_config=ConfigDict(extra='forbid')
    server:str='cn'
    zone:str='五区'
    tier:str='理论'
    big:str=Field(default='all',max_length=80)
    route:str='normal'
    q:str=Field(default='',max_length=80)
    stars:str='all'
    offset:int=Field(default=0,ge=0,le=5000)
    gaps:bool=False
    star_map:dict[str,StrictInt]=Field(default_factory=dict,max_length=200)

class Choice(BaseModel):
    model_config=ConfigDict(extra='forbid')
    map_id:str=Field(pattern=r'^[a-f0-9]{24}$')

def install(app,store,root,user):
    def actor(request):
        try:return user(request)
        except HTTPException as error:
            if error.status_code==401:return None
            raise
    def source(server):
        if server=='cn':
            info,contents=app.state.score_versions.current()
            return json.loads(contents['gauntlet_data.json']),json.loads(contents['cars.json']),info['id']
        if server!='global':raise HTTPException(422,'服别无效')
        from tools.build_global_data import validate_global_bundle
        names=('cars.global.json','gauntlet_data.global.json','global-data-manifest.json');raw={n:(root/n).read_bytes() for n in names}
        catalog,data,manifest=(json.loads(raw[n]) for n in names);validate_global_bundle(catalog,data,manifest,raw_files=raw)
        return data,catalog,manifest['_meta']['dataset_version']
    @app.get('/score-table')
    def page():return HTMLResponse((root/'coverage.html').read_text(encoding='utf-8'))
    def listing_data(request:Request,server:str='cn',zone:str='五区',tier:str='理论',big:str='all',route:str='normal',q:str='',stars:str='all',offset:int=0,gaps:bool=False,star_map=None):
        if len(q)>80 or not 0<=offset<=5000:raise HTTPException(422,'筛选范围无效')
        current=actor(request);data,catalog,version=source(server)
        with store.connect() as db:
            access=rights(db,current);result=matrix(data,catalog,access,server=server,zone=zone,tier=tier,big=big,route=route,query=q,stars=stars,offset=offset,gaps=gaps,star_map=star_map)
            own={}
            if current:
                for row in db.execute("SELECT id,status,payload FROM submissions WHERE owner_id=? AND status IN ('draft','pending','needs_info','accepted') AND NOT EXISTS(SELECT 1 FROM write_receipts WHERE submission_id=submissions.id) ORDER BY updated_at",(current['id'],)):
                    p=json.loads(row['payload']);own[key(p)]={'id':row['id'],'status':row['status']}
            if server=='cn':
                for r in result['rows']:
                    for c in r['cells']:
                        if c['key'] in own:c['mine']=own[c['key']]
        result.update(version=version,server=server,production=app.state.score_versions.production,access=access,user_id=current['id'] if current else None,rules=RULES,
                      maps=[{'id':map_id(name),'name':name} for name in dict.fromkeys(t['大地图'] for t in data['tracks'])])
        return JSONResponse(result,headers={'Cache-Control':'private, no-store','Vary':'Cookie'})
    @app.get('/api/coverage')
    def listing(request:Request,server:str='cn',zone:str='五区',tier:str='理论',big:str='all',route:str='normal',q:str='',stars:str='all',offset:int=0,gaps:bool=False):
        return listing_data(request,server,zone,tier,big,route,q,stars,offset,gaps)
    @app.post('/api/coverage/view')
    def query_view(body:CoverageView,request:Request):
        # Read-only query body keeps per-car choices out of a potentially oversized URL.
        return listing_data(request,**body.model_dump())
    @app.post('/api/coverage/choice')
    def select_map(body:Choice,request:Request):
        current=user(request)
        if not current['verified']:raise HTTPException(403,'请先验证邮箱')
        if request.headers.get('x-account-id')!=current['id']:raise HTTPException(401,'账号变化，请刷新')
        data,_,_=source('cn')
        if body.map_id not in {map_id(t['大地图']) for t in data['tracks']}:raise HTTPException(422,'地图不存在')
        with store.connect() as db:
            db.execute('BEGIN IMMEDIATE');app.state.require_active_session(request,db);access=rights(db,current)
            if access['chosen']:
                if access['chosen']==body.map_id:return {'chosen':access['chosen']}
                raise HTTPException(409,'已选择地图，不能自行更换')
            if access['level']!=1:raise HTTPException(409,'尚未达标或已拥有全部地图权益')
            now=int(time.time());db.execute('INSERT INTO coverage_choices VALUES(?,?,?)',(current['id'],body.map_id,now))
            db.execute('INSERT INTO coverage_events(user_id,action,snapshot,created_at) VALUES(?,?,?,?)',(current['id'],'choose',json.dumps({'map_id':body.map_id,'rules':1},ensure_ascii=False),now))
        return {'chosen':body.map_id}
