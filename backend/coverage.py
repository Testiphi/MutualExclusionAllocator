"""Read-only score coverage and ledger-derived national viewing rights. No score writes."""
import hashlib
import json
import math
import time
from pathlib import Path
from fastapi import HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, ConfigDict, Field
from data_tools import SC_TYPES, star_limits

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

def matrix(data,catalog,access,*,server='cn',zone='五区',tier='理论',big='all',route='normal',query='',stars='all',offset=0,gaps=False):
    if server not in ('cn','global') or zone not in ('五区','四区') or tier not in ('理论','高手') or route not in ('normal','special'):
        raise HTTPException(422,'表格范围无效')
    if server=='global' and (zone!='五区' or tier!='理论'):raise HTTPException(422,'国际服仅提供五区满星理论')
    if stars!='all' and stars not in ('1','2','3','4','5','6'):raise HTTPException(422,'星级无效')
    cars=[c for c in catalog['cars'] if c.get('nickname') and zone in c.get('zones',[])]
    candidates=[]
    for c in cars:
        low,high=star_limits(c,zone)
        for star in [None] if tier=='理论' else range(low,high+1):
            if query.casefold() not in (c['nickname']+' '+c['title']).casefold() or tier=='高手' and stars!='all' and star!=int(stars):continue
            candidates.append({'car':c['nickname'],'title':c['title'],'stars':star,'max_stars':high})
    columns=candidates[offset:offset+24];rows=[]
    for t in data['tracks']:
        if big!='all' and map_id(t['大地图'])!=big:continue
        theoretical=records(t,zone,'理论','')
        reference=[]
        for c in cars:
            # Theory keys remain unchanged; do not treat explicit lower-star records as maximum-star theory.
            maximum=star_limits(c,zone)[1]
            for s in (None,maximum):
                if (c['nickname'],s) in theoretical:reference.append((theoretical[c['nickname'],s],c['nickname'],s))
        public=min(reference,key=lambda r:(r[0],r[1],r[2] is not None,r[2] or 0),default=None)
        if route=='normal':routes=['']
        else:
            types={e.get('sc_type') for z in ('五区','四区') for k in ('理论','高手') for e in t.get(z,{}).get(k,[]) if e.get('sc') and e.get('sc_type') in SC_TYPES}
            if t.get('has_special_route') and t.get('special_route_note') in SC_TYPES:types.add(t['special_route_note'])
            routes=sorted(types)
        for run in routes:
            found=records(t,zone,tier,run);cells=[]
            for c in columns:
                target={k:c[k] for k in ('car','stars')};target.update(big=t['大地图'],small=t['小地图'],zone=zone,tier=tier,route=run)
                values=[found[k] for k in ((c['car'],None),(c['car'],c['max_stars'])) if k in found] if tier=='理论' else [found[c['car'],c['stars']]] if (c['car'],c['stars']) in found else []
                value=min(values,default=None)
                public_cell=not run and tier=='理论' and public is not None and c['car']==public[1] and value==public[0]
                visible=unlocked(access,server,t['大地图']) or public_cell
                cells.append({'key':key(target),'status':'empty' if value is None else 'filled','value':value if visible else None,'public':public_cell,
                              'target':target if server=='cn' else None})
            if gaps and not any(c['status']=='empty' for c in cells):continue
            rows.append({'big':t['大地图'],'small':t['小地图'],'route':run,'map_id':map_id(t['大地图']),'cells':cells})
    return {'columns':columns,'rows':rows,'column_total':len(candidates),'column_offset':offset,'column_limit':24}

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
    @app.get('/api/coverage')
    def listing(request:Request,server:str='cn',zone:str='五区',tier:str='理论',big:str='all',route:str='normal',q:str='',stars:str='all',offset:int=0,gaps:bool=False):
        if len(q)>80 or not 0<=offset<=5000:raise HTTPException(422,'筛选范围无效')
        current=actor(request);data,catalog,version=source(server)
        with store.connect() as db:
            access=rights(db,current);result=matrix(data,catalog,access,server=server,zone=zone,tier=tier,big=big,route=route,query=q,stars=stars,offset=offset,gaps=gaps)
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
