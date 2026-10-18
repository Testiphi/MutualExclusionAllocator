"""Private score submissions and review decisions; never writes the reference JSON."""
import base64
from decimal import Decimal, InvalidOperation
import hashlib
import io
import json
import re
import secrets
import time
from typing import Literal
from urllib.parse import urlsplit
import warnings

from fastapi import HTTPException, Request
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictInt
from PIL import Image, UnidentifiedImageError
from data_tools import SC_TYPES, car_records, star_limits


def packed(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def migrate(db):
    db.execute('BEGIN IMMEDIATE')
    version = db.execute('SELECT max(version) FROM schema_version').fetchone()[0]
    if version not in (1, 2, 3):
        raise RuntimeError('不支持的数据库版本')
    if version == 3:
        return
    if version == 2:
        db.execute('ALTER TABLE submissions ADD COLUMN review_score INTEGER CHECK(review_score BETWEEN 0 AND 5)')
        db.execute('INSERT INTO schema_version VALUES (3)')
        return
    statements = [
        '''CREATE TABLE submissions (
            id TEXT PRIMARY KEY, owner_id TEXT NOT NULL REFERENCES users(id), batch_id TEXT NOT NULL,
            revision INTEGER NOT NULL, status TEXT NOT NULL CHECK(status IN ('draft','pending','needs_info','accepted','ignored')),
            payload TEXT NOT NULL, target_key TEXT, accepted_payload TEXT, decision_reason TEXT,
            baseline TEXT, created_at INTEGER NOT NULL, updated_at INTEGER NOT NULL)''',
        '''CREATE TABLE submission_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT, submission_id TEXT NOT NULL REFERENCES submissions(id),
            revision INTEGER NOT NULL, actor_id TEXT NOT NULL REFERENCES users(id), action TEXT NOT NULL,
            snapshot TEXT NOT NULL, created_at INTEGER NOT NULL,
            UNIQUE(submission_id,revision))''',
        '''CREATE TABLE submission_images (
            id TEXT PRIMARY KEY, submission_id TEXT NOT NULL REFERENCES submissions(id),
            content BLOB NOT NULL, digest TEXT NOT NULL, created_at INTEGER NOT NULL, active INTEGER NOT NULL DEFAULT 1)''',
        '''CREATE TABLE submission_requests (
            owner_id TEXT NOT NULL REFERENCES users(id), request_key TEXT NOT NULL, fingerprint TEXT NOT NULL,
            result TEXT NOT NULL, PRIMARY KEY(owner_id,request_key))''',
        '''CREATE TABLE role_events(id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT NOT NULL REFERENCES users(id), old_role TEXT NOT NULL, new_role TEXT NOT NULL, changed_at INTEGER NOT NULL)''',
        'CREATE INDEX submissions_owner ON submissions(owner_id,updated_at)',
        'CREATE INDEX submissions_queue ON submissions(status,updated_at)',
        'CREATE INDEX submissions_target ON submissions(target_key)',
    ]
    for sql in statements:
        db.execute(sql)
    db.execute('INSERT INTO schema_version VALUES (2)')
    db.execute('ALTER TABLE submissions ADD COLUMN review_score INTEGER CHECK(review_score BETWEEN 0 AND 5)')
    db.execute('INSERT INTO schema_version VALUES (3)')


class Score(BaseModel):
    model_config = ConfigDict(extra='forbid')
    big: str = Field(default='', max_length=100)
    small: str = Field(default='', max_length=100)
    zone: Literal['五区','四区'] = '五区'
    tier: Literal['高手','理论','普通','自动'] = '高手'
    car: str = Field(default='', max_length=150)
    stars: StrictInt | None = Field(default=None, ge=1, le=6)
    route: str = Field(default='', max_length=40)
    time: str = Field(default='', max_length=24)
    notes: str = Field(default='', max_length=2000)
    video_url: str = Field(default='', max_length=1000)
    unlisted: StrictBool = False


class CreateBatch(BaseModel):
    model_config = ConfigDict(extra='forbid')
    request_key: str = Field(pattern=r'^[a-zA-Z0-9_-]{16,80}$')
    entries: list[Score] = Field(min_length=1,max_length=20)


class Revision(BaseModel):
    model_config = ConfigDict(extra='forbid')
    revision: StrictInt = Field(ge=1)


class Edit(Revision):
    entry: Score


class Review(Revision):
    action: Literal['accept','needs_info','ignore','reopen']
    entry: Score | None = None
    reason: str = Field(default='',max_length=2000)
    basis: dict[str,str] = Field(default_factory=dict,max_length=2)
    slower_confirmed: StrictBool = False
    review_score: StrictInt | None = Field(default=None,ge=0,le=5)


class Picture(Revision):
    data: str = Field(max_length=2900000)


def reference(root):
    data_bytes = (root/'gauntlet_data.json').read_bytes()
    cars_bytes = (root/'cars.json').read_bytes()
    return (json.loads(data_bytes), json.loads(cars_bytes),
            {'data':hashlib.sha256(data_bytes).hexdigest(),'cars':hashlib.sha256(cars_bytes).hexdigest()})


def normalize(entry, data, cars, strict=True):
    value = entry.model_dump()
    value = {k:v.strip() if isinstance(v,str) else v for k,v in value.items()}
    if value['video_url']:
        try: url = urlsplit(value['video_url'])
        except ValueError: raise HTTPException(422,'证据链接格式不正确')
        if url.scheme not in ('http','https') or not url.hostname or url.username or url.password:
            raise HTTPException(422,'证据链接必须是完整的HTTP/HTTPS地址，不含用户名密码')
    if not strict:
        return value
    if value['unlisted']:
        if len(value['notes']) < 10:
            raise HTTPException(422,'未收录资料请在说明中写明车辆、地图或跑法及来源，至少10字')
        return value
    if not any(t['大地图']==value['big'] and t['小地图']==value['small'] for t in data['tracks']):
        raise HTTPException(422,'请选择参考库中已有的地图，未收录内容请改为补充建议')
    record = car_records(cars).get(value['car'])
    if not record or not record.get('nickname') or value['zone'] not in record.get('zones',[]):
        raise HTTPException(422,'车辆不存在或不属于所选分区')
    value['car'] = record['nickname']
    if value['tier']=='高手' and value['stars'] is None:
        raise HTTPException(422,'高手成绩需要明确星级')
    if value['stars'] is not None:
        low,high = star_limits(record,value['zone'])
        if not low <= value['stars'] <= high:
            raise HTTPException(422,f'该车辆在所选分区允许的星级为{low}–{high}')
    if value['route'] and value['tier'] in ('普通','自动'):
        raise HTTPException(422,'普通/自动档只表示车辆可用性，不能包含特殊跑法；原始特殊跑法请保留在投稿说明中')
    if value['route'] and value['route'] not in SC_TYPES:
        raise HTTPException(422,'跑法不在当前白名单中')
    raw = value['time']
    if not re.fullmatch(r'(?:[0-9]{1,4}:)?[0-9]{1,5}(?:\.[0-9]{1,3})?',raw):
        raise HTTPException(422,'成绩请填秒数或分:秒，最多3位小数；不会自动四舍五入')
    try:
        if ':' in raw:
            minutes,seconds = raw.split(':')
            if Decimal(seconds)>=60: raise InvalidOperation
            result = Decimal(minutes)*60+Decimal(seconds)
        else: result = Decimal(raw)
        if result<=0: raise InvalidOperation
    except InvalidOperation:
        raise HTTPException(422,'成绩必须为正数；分秒格式的秒数必须小于60')
    value['time']=format(result,'f')
    return value


def identity(value):
    if value['unlisted']: return None
    return packed([value[k] for k in ('big','small','zone','tier','car','stars','route')])


def comparison(value, data):
    if value['unlisted']:
        return {'kind':'rule_needed','old':None,'effect':'需要先维护车辆、地图或跑法规则，不能直接采纳入库'}
    track=next(t for t in data['tracks'] if t['大地图']==value['big'] and t['小地图']==value['small'])
    entries=track[value['zone']][value['tier']]
    matches=[e for e in entries if len(e['cars'])==1 and e['cars'][0]['name']==value['car']
             and e['cars'][0].get('stars')==value['stars'] and bool(e.get('sc'))==bool(value['route'])
             and (not value['route'] or e.get('sc_type')==value['route'])]
    if len(matches)>1: raise HTTPException(409,'参考库存在重复目标，需先维护正式数据')
    if value['tier'] in ('普通','自动'):
        return {'kind':'availability_existing' if matches else 'availability_new','old':'✓' if matches else None,'new':'✓','delta':None,
                'effect':'仅提出'+value['tier']+'档可用性归档建议；原始成绩留在投稿，不作为正式库的time字段，不删除其他档位数据'}
    old=matches[0].get('time') if matches else None
    new=Decimal(value['time'])
    kind='placeholder' if matches and old is None else 'new' if old is None else 'same' if new==Decimal(str(old)) else 'faster' if new<Decimal(str(old)) else 'slower'
    effect='不自动修改其他档位或分区'
    if value['tier']=='高手' and not value['route']:
        mirror=any(len(e['cars'])==1 and e['cars'][0]['name']==value['car'] and e['cars'][0].get('stars')==value['stars'] and not e.get('sc') for e in track[value['zone']]['普通'])
        effect='普通镜像已存在；不自动同步另一分区' if mirror else '将来应用时需补同区普通镜像；不自动同步另一分区'
    return {'kind':kind,'old':old,'new':value['time'],'delta':None if old is None else str(new-Decimal(str(old))), 'effect':effect}


def install(app,store,root,user,reference_root=None):
    reference_root = reference_root or root
    def actor(request,admin=False,header=True):
        owner=user(request)
        if header and request.headers.get('x-account-id') != owner['id']:
            raise HTTPException(401,'账号已切换，请刷新后重试')
        if not owner['verified']: raise HTTPException(403,'请先验证邮箱')
        if admin and owner['role']!='admin': raise HTTPException(403,'需要管理员权限')
        return owner

    def get_row(db,sid,owner):
        row=db.execute('SELECT * FROM submissions WHERE id=?',(sid,)).fetchone()
        if not row or (row['owner_id']!=owner['id'] and (owner['role']!='admin' or row['status']=='draft')):
            raise HTTPException(404,'投稿不存在')
        return row

    def expected(row,revision):
        if row['revision']!=revision: raise HTTPException(409,'投稿已在其他窗口修改，请刷新详情后重试')

    def event(db,sid,owner,action,raw=None):
        row=db.execute('SELECT * FROM submissions WHERE id=?',(sid,)).fetchone()
        snapshot={'status':row['status'],'payload':json.loads(row['payload']),
                  'accepted_payload':json.loads(row['accepted_payload']) if row['accepted_payload'] else None,
                  'reason':row['decision_reason'],'review_score':row['review_score'],'baseline':json.loads(row['baseline']) if row['baseline'] else None,
                  'images':[r['id'] for r in db.execute('SELECT id FROM submission_images WHERE submission_id=? AND active=1 ORDER BY created_at',(sid,))]}
        if raw is not None: snapshot['raw']=raw
        db.execute('INSERT INTO submission_events(submission_id,revision,actor_id,action,snapshot,created_at) VALUES (?,?,?,?,?,?)',
                   (sid,row['revision'],owner['id'],action,packed(snapshot),int(time.time())))

    @app.get('/submissions')
    def page(): return FileResponse(root/'submissions.html')

    @app.get('/api/submissions/catalog')
    def catalog(request:Request):
        actor(request)
        data,cars,basis=reference(reference_root)
        return {'tracks':[{'big':t['大地图'],'small':t['小地图']} for t in data['tracks']],
                'cars':[{'name':c['nickname'],'title':c['title'],'zones':c.get('zones',[]),
                         'limits':{z:star_limits(c,z) for z in c.get('zones',[])}} for c in cars['cars'] if c.get('nickname') and c.get('zones')],
                'routes':list(SC_TYPES),'basis':basis,'reference_label':'本地功能分支参考库快照，尚非线上实时库'}

    @app.post('/api/submissions')
    def create(body:CreateBatch,request:Request):
        owner=actor(request)
        data,cars,_=reference(reference_root)
        fingerprint=hashlib.sha256(packed(body.model_dump()).encode()).hexdigest()
        with store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            prior=db.execute('SELECT * FROM submission_requests WHERE owner_id=? AND request_key=?',(owner['id'],body.request_key)).fetchone()
            if prior:
                if prior['fingerprint']!=fingerprint: raise HTTPException(409,'提交标识已用于其他内容，请刷新后重新操作')
                return json.loads(prior['result'])
            if db.execute('SELECT count(*) FROM submissions WHERE owner_id=? AND created_at>?',(owner['id'],int(time.time())-86400)).fetchone()[0]+len(body.entries)>100:
                raise HTTPException(429,'每天最多保存100条投稿，请明天再试')
            batch=secrets.token_hex(16); ids=[]
            for entry in body.entries:
                value=normalize(entry,data,cars,False)
                sid=secrets.token_hex(16); now=int(time.time())
                db.execute('INSERT INTO submissions(id,owner_id,batch_id,revision,status,payload,created_at,updated_at) VALUES (?,?,?,1,\'draft\',?,?,?)',
                           (sid,owner['id'],batch,packed(value),now,now))
                event(db,sid,owner,'created',entry.model_dump()); ids.append(sid)
            result={'ids':ids,'batch_id':batch}
            db.execute('INSERT INTO submission_requests VALUES (?,?,?,?)',(owner['id'],body.request_key,fingerprint,packed(result)))
        return result

    @app.get('/api/submissions')
    def listing(request:Request,scope:Literal['mine','review']='mine',status:str='',q:str='',offset:int=0):
        owner=actor(request,scope=='review')
        if len(q)>100 or offset<0: raise HTTPException(422,'查询参数不正确')
        conditions=['owner_id=?'] if scope=='mine' else ["status!='draft'"]
        args=[owner['id']] if scope=='mine' else []
        if status:
            if status not in ('draft','pending','needs_info','accepted','ignored'): raise HTTPException(422,'状态不正确')
            conditions.append('status=?'); args.append(status)
        if q:
            conditions.append("payload LIKE ? ESCAPE '\\'")
            args.append('%'+q.replace('\\','\\\\').replace('%','\\%').replace('_','\\_')+'%')
        where=' AND '.join(conditions)
        with store.connect() as db:
            total=db.execute('SELECT count(*) FROM submissions WHERE '+where,args).fetchone()[0]
            rows=db.execute('SELECT id,batch_id,owner_id,revision,status,payload,decision_reason,review_score,updated_at FROM submissions WHERE '+where+' ORDER BY updated_at DESC,id DESC LIMIT 50 OFFSET ?',args+[offset]).fetchall()
        return {'total':total,'items':[{**dict(r),'payload':json.loads(r['payload'])} for r in rows]}

    @app.get('/api/submissions/{sid}')
    def detail(sid:str,request:Request):
        owner=actor(request)
        with store.connect() as db:
            row=get_row(db,sid,owner); result=dict(row)
            result['payload']=json.loads(row['payload'])
            result['accepted_payload']=json.loads(row['accepted_payload']) if row['accepted_payload'] else None
            result['baseline']=json.loads(row['baseline']) if row['baseline'] else None
            result['images']=[{'id':r['id'],'digest':r['digest'],'url':f'/api/submissions/{sid}/images/{r["id"]}'} for r in db.execute('SELECT id,digest FROM submission_images WHERE submission_id=? AND active=1 ORDER BY created_at',(sid,))]
            result['events']=[{**dict(r),'snapshot':json.loads(r['snapshot'])} for r in db.execute('SELECT revision,actor_id,action,snapshot,created_at FROM submission_events WHERE submission_id=? ORDER BY revision',(sid,))]
            result['same_target']=[]
            if owner['role']=='admin' and row['target_key']:
                result['same_target']=[dict(r) for r in db.execute("SELECT id,status FROM submissions WHERE target_key=? AND id!=? AND status!='draft' ORDER BY updated_at DESC LIMIT 20",(row['target_key'],sid))]
        try:
            data,cars,basis=reference(reference_root)
            candidate=normalize(Score(**(result['accepted_payload'] or result['payload'])),data,cars)
            result['comparison']=comparison(candidate,data)
            result['basis']=basis
        except HTTPException as error:
            result['comparison']={'kind':'invalid','effect':error.detail}
        return result

    @app.put('/api/submissions/{sid}')
    def edit(sid:str,body:Edit,request:Request):
        owner=actor(request); data,cars,_=reference(reference_root)
        value=normalize(body.entry,data,cars,False)
        with store.connect() as db:
            db.execute('BEGIN IMMEDIATE'); row=get_row(db,sid,owner); expected(row,body.revision)
            if row['owner_id']!=owner['id'] or row['status'] not in ('draft','needs_info'):
                raise HTTPException(409,'仅本人草稿或待补充投稿可以修改')
            db.execute('UPDATE submissions SET payload=?,revision=revision+1,updated_at=? WHERE id=?',(packed(value),int(time.time()),sid))
            event(db,sid,owner,'edited',body.entry.model_dump())
        return {'revision':body.revision+1}

    @app.post('/api/submissions/{sid}/submit')
    def submit(sid:str,body:Revision,request:Request):
        owner=actor(request); data,cars,basis=reference(reference_root)
        with store.connect() as db:
            db.execute('BEGIN IMMEDIATE'); row=get_row(db,sid,owner); expected(row,body.revision)
            if row['owner_id']!=owner['id'] or row['status'] not in ('draft','needs_info'):
                raise HTTPException(409,'此状态不能重复提交或修改')
            value=normalize(Score(**json.loads(row['payload'])),data,cars)
            if value['tier']=='理论' and not value['unlisted'] and not value['notes'] and not value['video_url'] and not db.execute('SELECT 1 FROM submission_images WHERE submission_id=? AND active=1',(sid,)).fetchone():
                raise HTTPException(422,'理论成绩请补充来源说明、证据图片或视频链接')
            db.execute("UPDATE submissions SET payload=?,target_key=?,status='pending',review_score=NULL,baseline=?,revision=revision+1,updated_at=? WHERE id=?",
                       (packed(value),identity(value),packed(basis),int(time.time()),sid))
            event(db,sid,owner,'submitted')
        return {'revision':body.revision+1,'status':'pending'}

    @app.post('/api/admin/submissions/{sid}/preview')
    def preview(sid:str,body:Edit,request:Request):
        owner=actor(request,True)
        with store.connect() as db:
            row=get_row(db,sid,owner); expected(row,body.revision)
            if row['status']!='pending': raise HTTPException(409,'只有待审核投稿可预览采纳内容')
        data,cars,basis=reference(reference_root); candidate=normalize(body.entry,data,cars)
        compare=comparison(candidate,data)
        return {'candidate':candidate,'comparison':compare,'basis':basis,'revision':body.revision}

    @app.post('/api/admin/submissions/{sid}/review')
    def review(sid:str,body:Review,request:Request):
        owner=actor(request,True)
        with store.connect() as db:
            db.execute('BEGIN IMMEDIATE'); row=get_row(db,sid,owner); expected(row,body.revision)
            if body.action=='reopen':
                if row['status'] not in ('accepted','ignored') or not body.reason.strip():
                    raise HTTPException(422,'仅已采纳或已忽略投稿可重新审核，且需填写原因')
                original=json.loads(row['payload'])
                db.execute("UPDATE submissions SET status='pending',review_score=NULL,accepted_payload=NULL,target_key=?,decision_reason=?,revision=revision+1,updated_at=? WHERE id=?",
                           (identity(original),body.reason.strip(),int(time.time()),sid))
                event(db,sid,owner,'reopened')
                return {'revision':body.revision+1,'status':'pending'}
            if row['status']!='pending': raise HTTPException(409,'投稿已处理，不能重复审核')
            reason=body.reason.strip(); candidate=None; basis=None
            status={'accept':'accepted','needs_info':'needs_info','ignore':'ignored'}[body.action]
            if body.action=='accept':
                if body.entry is None: raise HTTPException(422,'缺少拟采纳内容')
                data,cars,basis=reference(reference_root)
                if body.basis!=basis: raise HTTPException(409,'参考数据或车辆规则已变化，请重新预览并确认')
                candidate=normalize(body.entry,data,cars)
                if candidate['unlisted']: raise HTTPException(422,'未收录建议需先维护规则；本轮不可直接采纳入库')
                compare=comparison(candidate,data)
                if compare['kind']=='slower' and not body.slower_confirmed: raise HTTPException(422,'较慢成绩需要逐条明确确认')
                if (candidate!=json.loads(row['payload']) or compare['kind']=='slower') and not reason:
                    raise HTTPException(422,'修改后采纳或较慢成绩必须填写审核原因')
                # Another accepted proposal for the same target must not silently coexist.
                duplicate=db.execute("SELECT id FROM submissions WHERE target_key=? AND status='accepted' AND id!=?",(identity(candidate),sid)).fetchone()
                if duplicate: raise HTTPException(409,'该目标已有已采纳投稿：'+duplicate['id']+'；请先处理冲突，不能重复采纳')
                # No writes to reference files, no mirror or cross-zone synchronization here.
            elif not reason:
                raise HTTPException(422,'要求补充或忽略时请填写反馈原因')
            db.execute('UPDATE submissions SET status=?,accepted_payload=?,decision_reason=?,review_score=?,baseline=COALESCE(?,baseline),target_key=COALESCE(?,target_key),revision=revision+1,updated_at=? WHERE id=?',
                       (status,packed(candidate) if candidate else None,reason,body.review_score,packed(basis) if basis else None,identity(candidate) if candidate else None,int(time.time()),sid))
            event(db,sid,owner,body.action)
        return {'revision':body.revision+1,'status':status}

    @app.post('/api/submissions/{sid}/images')
    def upload(sid:str,body:Picture,request:Request):
        owner=actor(request)
        store.throttle('images:'+owner['id'],30)
        # Check authorization before decoding potentially expensive input.
        with store.connect() as db:
            row=get_row(db,sid,owner); expected(row,body.revision)
            if row['owner_id']!=owner['id'] or row['status'] not in ('draft','needs_info'): raise HTTPException(409,'只可为本人草稿或待补充投稿上传图片')
        try:
            raw=base64.b64decode(body.data,validate=True)
            if len(raw)>2*1024*1024: raise ValueError()
            with warnings.catch_warnings():
                warnings.simplefilter('error',Image.DecompressionBombWarning)
                with Image.open(io.BytesIO(raw)) as image:
                    if image.format not in ('PNG','JPEG','WEBP') or image.width*image.height>16000000 or getattr(image,'n_frames',1)!=1: raise ValueError()
                    image.load(); image=image.convert('RGB'); image.thumbnail((2400,2400))
                    output=io.BytesIO(); image.save(output,format='JPEG',quality=90); content=output.getvalue()
        except (ValueError,OSError,UnidentifiedImageError,Image.DecompressionBombError,Image.DecompressionBombWarning):
            raise HTTPException(422,'仅支持2MB以内静态PNG/JPEG/WebP图片，最多1600万像素')
        with store.connect() as db:
            db.execute('BEGIN IMMEDIATE'); row=get_row(db,sid,owner); expected(row,body.revision)
            if row['owner_id']!=owner['id'] or row['status'] not in ('draft','needs_info'): raise HTTPException(409,'投稿状态已变化')
            if db.execute('SELECT count(*) FROM submission_images WHERE submission_id=? AND active=1',(sid,)).fetchone()[0]>=3: raise HTTPException(422,'每条投稿最多3张证据图片')
            if db.execute('SELECT count(*) FROM submission_images WHERE submission_id=?',(sid,)).fetchone()[0]>=10: raise HTTPException(422,'每条投稿累计最多10张图片（含历史），请使用来源链接补充')
            iid=secrets.token_hex(16)
            db.execute('INSERT INTO submission_images(id,submission_id,content,digest,created_at) VALUES (?,?,?,?,?)',(iid,sid,content,hashlib.sha256(content).hexdigest(),int(time.time())))
            db.execute('UPDATE submissions SET revision=revision+1,updated_at=? WHERE id=?',(int(time.time()),sid))
            event(db,sid,owner,'image_added')
        return {'id':iid,'revision':body.revision+1}

    @app.delete('/api/submissions/{sid}/images/{iid}')
    def remove_image(sid:str,iid:str,body:Revision,request:Request):
        owner=actor(request)
        with store.connect() as db:
            db.execute('BEGIN IMMEDIATE'); row=get_row(db,sid,owner); expected(row,body.revision)
            if row['owner_id']!=owner['id'] or row['status'] not in ('draft','needs_info'): raise HTTPException(409,'只可编辑本人草稿或待补充证据')
            if not db.execute('SELECT 1 FROM submission_images WHERE id=? AND submission_id=? AND active=1',(iid,sid)).fetchone(): raise HTTPException(404)
            db.execute('UPDATE submission_images SET active=0 WHERE id=?',(iid,))
            db.execute('UPDATE submissions SET revision=revision+1,updated_at=? WHERE id=?',(int(time.time()),sid))
            event(db,sid,owner,'image_removed')
        return {'revision':body.revision+1}

    @app.get('/api/submissions/{sid}/images/{iid}')
    def image(sid:str,iid:str,request:Request):
        owner=actor(request,header=False)
        with store.connect() as db:
            get_row(db,sid,owner)
            row=db.execute('SELECT content FROM submission_images WHERE id=? AND submission_id=?',(iid,sid)).fetchone()
            if not row: raise HTTPException(404)
        return Response(row['content'],media_type='image/jpeg',headers={'Content-Disposition':'inline; filename="evidence.jpg"','Cross-Origin-Resource-Policy':'same-origin'})
