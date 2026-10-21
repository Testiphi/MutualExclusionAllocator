"""Local-only release workflow with immutable score files and a transactional active pointer."""
import json
from pathlib import Path
import secrets
import time
from fastapi import HTTPException, Request
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel, ConfigDict, Field, StrictBool
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, InvalidHashError
from backend.previews import ROOT, Pick, build_preview, load_source, LOADED_ENGINE, engine_hashes
from backend.score_repository import Versions, validate_lab, encode, digest, write_new, FILES
from backend.manage import copy_database

EXTRA=('backend/score_versions.py','backend/score_repository.py')
LOADED_EXTRA={n:digest((ROOT/n).read_bytes()) for n in EXTRA}
HASHER=PasswordHasher()
def reject(text):raise HTTPException(409,text)

class Prepare(BaseModel):
    model_config=ConfigDict(extra='forbid')
    request_key:str=Field(pattern=r'^[A-Za-z0-9_-]{16,80}$')
    items:list[Pick]=Field(min_length=1,max_length=50)
class Approval(BaseModel):
    model_config=ConfigDict(extra='forbid')
    submission_id:str
    confirmed:StrictBool
    slower_confirmed:StrictBool=False
    slower_reason:str=Field(default='',max_length=2000)
class Confirm(BaseModel):
    model_config=ConfigDict(extra='forbid')
    digest:str=Field(max_length=64)
    effects_confirmed:StrictBool
    items:list[Approval]=Field(min_length=1,max_length=50)
class Reason(BaseModel):
    model_config=ConfigDict(extra='forbid')
    reason:str=Field(min_length=1,max_length=2000)
class Reauth(BaseModel):
    model_config=ConfigDict(extra='forbid')
    password:str=Field(min_length=1,max_length=128)

class ScoreWriter:
    def __init__(self,lab,store):
        self.lab,self.marker=validate_lab(lab,store.directory);self.store=store;self.versions=Versions(self.lab)
        with self.versions.lock(),store.connect() as db:
            db.executescript('''CREATE TABLE IF NOT EXISTS score_current(slot INTEGER PRIMARY KEY CHECK(slot=1),version TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS score_batches(id TEXT PRIMARY KEY,actor TEXT NOT NULL,request_key TEXT NOT NULL,request_hash TEXT NOT NULL,state TEXT NOT NULL,manifest TEXT NOT NULL,UNIQUE(actor,request_key));
            CREATE TABLE IF NOT EXISTS write_receipts(submission_id TEXT PRIMARY KEY,batch_id TEXT NOT NULL,state TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS score_reauth(session_hash TEXT PRIMARY KEY,user_id TEXT NOT NULL,expires INTEGER NOT NULL);''')
            db.execute('INSERT OR IGNORE INTO score_current VALUES(1,?)',(self.marker['initial'],))
        self.current()  # Refuse unsupported or corrupted data instead of silently reseeding.
    def current_id(self,db):return db.execute('SELECT version FROM score_current WHERE slot=1').fetchone()[0]
    def current(self):
        with self.store.connect() as db:identity=self.current_id(db)
        info,contents=self.versions.read(identity)
        if info['files']['cars.json']!=self.marker['cars_sha256']:reject('本阶段禁止修改车辆规则')
        return info,contents
    def current_dir(self):return self.versions.root/self.current()[0]['id']
    def idle(self,db):
        if db.execute("SELECT 1 FROM score_batches WHERE state IN ('applying','rolling_back','recovery_required')").fetchone():reject('存在未完成批次，请先恢复')
    def guard(self,db,sid):
        self.idle(db)
        if db.execute('SELECT 1 FROM write_receipts WHERE submission_id=?',(sid,)).fetchone():reject('已有应用/回滚回执，请新建投稿')
    def tools(self):
        if engine_hashes()!=LOADED_ENGINE or {n:digest((ROOT/n).read_bytes()) for n in EXTRA}!=LOADED_EXTRA:reject('维护工具变化，请重启并重新生成预览')
    def selected(self,db,picks):
        if len({p.id for p in picks})!=len(picks):reject('不能重复选择同一投稿')
        rows=[]
        for pick in picks:
            self.guard(db,pick.id)
            row=db.execute('SELECT * FROM submissions WHERE id=?',(pick.id,)).fetchone()
            if not row or row['status']!='accepted' or row['revision']!=pick.revision:reject('投稿审核状态或版本变化')
            rows.append(row)
        return rows
    def get(self,db,bid):
        row=db.execute('SELECT * FROM score_batches WHERE id=?',(bid,)).fetchone()
        if not row:raise HTTPException(404,'批次不存在')
        return row,json.loads(row['manifest'])
    def put(self,db,bid,state,m):db.execute('UPDATE score_batches SET state=?,manifest=? WHERE id=?',(state,encode(m),bid))
    def prepare(self,actor,body):
        with self.versions.lock(),self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE');self.idle(db);self.tools()
            fingerprint=digest(encode(body.model_dump()).encode())
            old=db.execute('SELECT id,request_hash FROM score_batches WHERE actor=? AND request_key=?',(actor,body.request_key)).fetchone()
            if old:
                if old['request_hash']!=fingerprint:reject('请求标识已用于其他选择')
                row,m=self.get(db,old['id']);return {**m,'state':row['state']}
            rows=self.selected(db,body.items);base=self.current_id(db);info,contents=self.versions.read(base)
            data,cars,source=load_source(self.versions.root/base);source['version']=base
            result,preview=build_preview(rows,data,cars,source)
            if result['state']!='ready' or not result['changes']['changes']:reject('没有有效改动或存在冲突')
            bid=secrets.token_hex(16)
            target=self.versions.create({'gauntlet_data.json':preview.encode(),'cars.json':contents['cars.json']},base,'apply',bid)
            m={'id':bid,'actor':actor,'created_at':int(time.time()),'base':base,'target':target,'result':result,'engine':LOADED_ENGINE,'extra':LOADED_EXTRA,'events':[]}
            m['digest']=digest(encode(m).encode())
            db.execute('INSERT INTO score_batches VALUES(?,?,?,?,?,?)',(bid,actor,body.request_key,fingerprint,'prepared',encode(m)))
            return {**m,'state':'prepared','stale_reasons':[]}
    def fresh(self,db,m):
        self.tools()
        if m['engine']!=LOADED_ENGINE or m['extra']!=LOADED_EXTRA:reject('工具版本变化，确认失效')
        if self.current_id(db)!=m['base']:reject('当前数据版本变化，请重新预览')
        rows=self.selected(db,[Pick(id=i['submission_id'],revision=i['revision']) for i in m['result']['items']])
        for row,item in zip(rows,m['result']['items']):
            if digest((row['accepted_payload'] or '').encode())!=item['accepted_hash']:reject('拟采纳内容变化')
        _,contents=self.versions.read(m['base']);target,_=self.versions.read(m['target'])
        if target['parent']!=m['base'] or target['files']['cars.json']!=self.marker['cars_sha256']:reject('目标版本来源异常')
        data,cars,source=load_source(self.versions.root/m['base']);source['version']=m['base']
        result,preview=build_preview(rows,data,cars,source)
        if result['state']!='ready' or digest(preview.encode())!=target['files']['gauntlet_data.json']:reject('候选内容已变化')
    def recent(self,db,actor,session_hash):
        row=db.execute('''SELECT 1 FROM score_reauth r JOIN sessions s ON s.token_hash=r.session_hash AND s.user_id=r.user_id
            JOIN users u ON u.id=r.user_id JOIN super_admins a ON a.user_id=u.id
            WHERE r.session_hash=? AND r.user_id=? AND r.expires>? AND s.expires_at>? AND u.verified=1''',(session_hash,actor,int(time.time()),int(time.time()))).fetchone()
        if not row:raise HTTPException(403,'请重新验证超级管理员密码（有效期5分钟）')
    def reauthenticate(self,actor,session_hash,password):
        self.store.throttle('score-reauth:'+actor,5)
        with self.store.connect() as db:
            row=db.execute('SELECT password_hash FROM users WHERE id=?',(actor,)).fetchone()
            try:HASHER.verify(row['password_hash'],password)
            except (VerificationError,InvalidHashError):raise HTTPException(401,'密码不正确') from None
            expiry=int(time.time())+300
            db.execute('DELETE FROM score_reauth WHERE expires<=?',(int(time.time()),))
            db.execute('INSERT OR REPLACE INTO score_reauth VALUES(?,?,?)',(session_hash,actor,expiry))
        return {'expires_at':expiry}
    def backup(self,bid,version,operation):
        info,contents=self.versions.read(version)
        folder=self.lab/'backups'/(bid+'-'+operation+'-'+secrets.token_hex(6));folder.mkdir()
        for name in FILES:write_new(folder/name,contents[name])
        copy_database(self.store.path,folder/'accounts.sqlite3')
        manifest={'version':version,'files':{n:digest((folder/n).read_bytes()) for n in (*FILES,'accounts.sqlite3')}}
        write_new(folder/'manifest.json',encode(manifest).encode())
        return {'folder':folder.name,'manifest_hash':digest(encode(manifest).encode()),'version':version}
    def verify_backup(self,receipt):
        folder=self.lab/'backups'/receipt['folder'];raw=(folder/'manifest.json').read_bytes()
        if digest(raw)!=receipt['manifest_hash']:reject('备份清单已变化')
        info=json.loads(raw)
        if info['version']!=receipt['version'] or any(digest((folder/n).read_bytes())!=info['files'][n] for n in (*FILES,'accounts.sqlite3')):reject('备份校验失败')
    def checkpoint(self,name):pass  # Fault injection seam; no public fault-control endpoint.
    def detail(self,bid):
        with self.store.connect() as db:
            row,m=self.get(db,bid);reasons=[]
            if row['state']=='prepared':
                try:self.fresh(db,m)
                except (HTTPException,ValueError,OSError) as e:reasons.append(str(e.detail if isinstance(e,HTTPException) else e))
            return {**m,'state':row['state'],'stale_reasons':reasons}
    def execute(self,actor,session_hash,bid,body):
        with self.versions.lock():
            with self.store.connect() as db:
                row,m=self.get(db,bid);self.recent(db,actor,session_hash)
                if row['state']=='applied':return {**m,'state':'applied'}
                if row['state']!='prepared' or body.digest!=m['digest']:reject('批次状态或确认摘要不匹配')
                self.fresh(db,m)
                expected={i['submission_id']:i for i in m['result']['items'] if i['kind']!='unchanged'}
                approvals={i.submission_id:i for i in body.items}
                if len(approvals)!=len(body.items) or set(approvals)!=set(expected) or not body.effects_confirmed:reject('请逐项确认本批次全部改动及普通镜像')
                for sid,item in expected.items():
                    a=approvals[sid]
                    if not a.confirmed:reject('存在未勾选条目')
                    if item.get('slower') and (not a.slower_confirmed or not a.slower_reason.strip()):reject('更慢成绩必须再次确认并填写原因')
            backup=self.backup(bid,m['base'],'apply');self.verify_backup(backup)
            with self.store.connect() as db:
                db.execute('BEGIN IMMEDIATE');self.fresh(db,m);self.recent(db,actor,session_hash)
                m['backup']=backup;m['approval']={'actor':actor,'at':int(time.time()),**body.model_dump()}
                m['events'].append({'action':'apply_started','at':int(time.time())});self.put(db,bid,'applying',m)
            try:
                self.checkpoint('apply_intent')
                with self.store.connect() as db:
                    db.execute('BEGIN IMMEDIATE')
                    self.recent(db,actor,session_hash)
                    if self.current_id(db)!=m['base']:reject('执行前版本变化')
                    self.versions.read(m['target']);self.verify_backup(backup)
                    db.execute('UPDATE score_current SET version=? WHERE slot=1',(m['target'],))
                    for i in m['result']['items']:
                        if i['kind']!='unchanged':db.execute('INSERT INTO write_receipts VALUES(?,?,?)',(i['submission_id'],bid,'applied'))
                    m['events'].append({'action':'applied','actor':actor,'at':int(time.time())});self.put(db,bid,'applied',m)
                    self.checkpoint('apply_before_commit')
                self.checkpoint('apply_after_commit')
            except Exception:
                self.recover_locked(actor,bid,'应用异常，终止未提交批次')
                raise HTTPException(409,'操作异常，请查看批次状态；未提交的写入已终止') from None
            return {**m,'state':'applied'}
    def rollback(self,actor,session_hash,bid,reason):
        if not reason.strip():reject('回滚必须填写原因')
        with self.versions.lock():
            with self.store.connect() as db:
                row,m=self.get(db,bid);self.recent(db,actor,session_hash);self.idle(db)
                if row['state']=='rolled_back':return {**m,'state':'rolled_back'}
                if row['state']!='applied' or self.current_id(db)!=m['target']:reject('已存在后续版本，禁止覆盖回滚；需要新的反向变更批次')
            self.verify_backup(m['backup'])
            backup=self.backup(bid,m['target'],'rollback');self.verify_backup(backup)
            _,old=self.versions.read(m['base'])
            rollback_version=self.versions.create(old,m['target'],'rollback',bid)
            with self.store.connect() as db:
                db.execute('BEGIN IMMEDIATE');self.idle(db);self.recent(db,actor,session_hash)
                if self.current_id(db)!=m['target']:reject('回滚前版本变化')
                m['rollback']={'version':rollback_version,'actor':actor,'reason':reason,'backup':backup,'at':int(time.time())}
                self.put(db,bid,'rolling_back',m)
            self.checkpoint('rollback_intent')
            return self.recover_locked(actor,bid,reason,session_hash)
    def recover_locked(self,actor,bid,reason,session_hash=None):
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE');row,m=self.get(db,bid)
            if session_hash is not None:self.recent(db,actor,session_hash)
            original=json.loads(row['manifest'])
            if row['state'] in ('applied','rolled_back','aborted'):return {**m,'state':row['state']}
            if row['state'] not in ('applying','rolling_back','recovery_required'):reject('此批次无需恢复')
            try:
                if m.get('rollback'):
                    if self.current_id(db)!=m['target']:reject('恢复发现后续版本，保留现场')
                    self.verify_backup(m['backup']);self.verify_backup(m['rollback']['backup']);self.versions.read(m['rollback']['version'])
                    db.execute('UPDATE score_current SET version=? WHERE slot=1',(m['rollback']['version'],))
                    db.execute("UPDATE write_receipts SET state='rolled_back' WHERE batch_id=?",(bid,));state='rolled_back'
                else:
                    if self.current_id(db)!=m['base']:reject('当前版本不符合执行日志，保留现场')
                    self.versions.read(m['base']);state='aborted'
                m['events'].append({'action':state,'actor':actor,'reason':reason,'at':int(time.time())})
                self.put(db,bid,state,m);self.checkpoint('recovery_before_commit')
            except (HTTPException,ValueError,OSError) as error:
                # No pointer writes occur before all validation; commit only the blocked state.
                db.rollback()
                with self.store.connect() as blocked:self.put(blocked,bid,'recovery_required',original)
                raise error
            return {**m,'state':state}


def install(app,writer,root,user,session):
    def owner(request):
        actor=user(request)
        if actor['role']!='superadmin' or not actor['verified']:raise HTTPException(403,'仅已验证超级管理员可发布或回滚测试成绩')
        if request.headers.get('x-account-id')!=actor['id']:raise HTTPException(401,'账号变化，请刷新')
        return actor['id'],session(request)['token_hash']
    def safely(fn,*args):
        try:return fn(*args)
        except (OSError,ValueError) as error:raise HTTPException(409,'校验或文件操作失败：'+str(error)) from error
    @app.get('/score-versions')
    def page():return FileResponse(root/'score_versions.html')
    @app.get('/api/scores/snapshot')
    def snapshot():
        info,contents=safely(writer.current)
        return {'version':info['id'],'data':json.loads(contents['gauntlet_data.json']),'cars':json.loads(contents['cars.json'])}
    @app.get('/api/admin/score-versions')
    def listing(request:Request):
        owner(request);info,_=safely(writer.current)
        with writer.store.connect() as db:
            pending=db.execute("SELECT id,revision,accepted_payload FROM submissions WHERE status='accepted' AND NOT EXISTS(SELECT 1 FROM write_receipts WHERE submission_id=submissions.id) ORDER BY updated_at DESC,id LIMIT 100").fetchall()
            batches=db.execute('SELECT id,state,manifest FROM score_batches ORDER BY rowid DESC LIMIT 50').fetchall()
        return {'current':info,'lab':str(writer.lab),'items':[{**dict(r),'accepted_payload':json.loads(r['accepted_payload'])} for r in pending],
                'batches':[{'id':r['id'],'state':r['state'],'created_at':json.loads(r['manifest'])['created_at']} for r in batches]}
    @app.post('/api/admin/score-versions/reauth')
    def reauth(body:Reauth,request:Request):return writer.reauthenticate(*owner(request),body.password)
    @app.post('/api/admin/score-versions')
    def prepare(body:Prepare,request:Request):return safely(writer.prepare,owner(request)[0],body)
    @app.get('/api/admin/score-versions/{bid}')
    def detail(bid:str,request:Request):owner(request);return safely(writer.detail,bid)
    @app.post('/api/admin/score-versions/{bid}/execute')
    def execute(bid:str,body:Confirm,request:Request):return safely(writer.execute,*owner(request),bid,body)
    @app.post('/api/admin/score-versions/{bid}/rollback')
    def rollback(bid:str,body:Reason,request:Request):return safely(writer.rollback,*owner(request),bid,body.reason)
    @app.post('/api/admin/score-versions/{bid}/recover')
    def recover(bid:str,body:Reason,request:Request):
        actor,key=owner(request)
        if not body.reason.strip():reject('恢复必须填写原因')
        with writer.versions.lock():
            with writer.store.connect() as db:writer.recent(db,actor,key)
            return safely(writer.recover_locked,actor,bid,body.reason,key)
