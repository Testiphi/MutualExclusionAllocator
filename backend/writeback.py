"""Recoverable multi-file writes, strictly limited to provisioned disposable labs."""
from contextlib import contextmanager
import json
import os
from pathlib import Path
import secrets
import time
from fastapi import HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, Field, StrictBool
from backend.previews import ROOT, Pick, build_preview, load_source, sha, encoded, engine_hashes, LOADED_ENGINE
from backend.writeback_lab import validate_lab, FILES
from export_xlsx import build_workbook
from xlsx_tools import load_workbook_data
from data_tools import parse_column

EXTRA=('backend/writeback.py','backend/writeback_lab.py','export_xlsx.py','xlsx_tools.py')
LOADED_EXTRA={n:sha((ROOT/n).read_bytes()) for n in EXTRA}

def fail(message):raise HTTPException(409,message)
def filehash(p):return sha(p.read_bytes())
def hashes(folder):return {n:filehash(folder/n) for n in FILES}
def save(path,raw):
    temp=path.with_name(path.name+'.tmp')
    with temp.open('wb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
    os.replace(temp,path)

def check_workbook(path,data):
    """Compare all represented nonempty cells independently with JSON values."""
    parsed=load_workbook_data(path);actual={}
    if len(parsed)!=12:raise ValueError('工作簿工作表不完整')
    for sheet in parsed.values():
        for row,cells in sheet['rows'].items():
            for column,value in cells.items():
                name,stars=parse_column(column)
                key=(row[0],row[1],sheet['zone'],sheet['tier'],name,stars,row[2] if sheet['sc'] else None)
                actual[key]=value
    expected={}
    for track in data['tracks']:
        for zone in ('四区','五区'):
            for tier in ('理论','高手','普通','自动'):
                for e in track[zone][tier]:
                    value='✓' if tier in ('普通','自动') else e.get('time')
                    if value is None:continue
                    for car in e['cars']:
                        key=(track['大地图'],track['小地图'],zone,tier,car['name'],car.get('stars'),e.get('sc_type') or 'sc' if e.get('sc') else None)
                        expected[key]=value
    if actual!=expected:raise ValueError('工作簿往返校验不一致，阻止替换')

class Prepare(BaseModel):
    model_config=ConfigDict(extra='forbid')
    preview_id:str=Field(pattern=r'^[a-f0-9]{32}$')
    items:list[Pick]=Field(min_length=1,max_length=50)
    request_key:str=Field(pattern=r'^[a-zA-Z0-9_-]{16,80}$')
class Approval(BaseModel):
    model_config=ConfigDict(extra='forbid')
    submission_id:str=Field(pattern=r'^[a-f0-9]{32}$')
    confirmed:StrictBool
    slower_confirmed:StrictBool=False
    slower_reason:str=Field(default='',max_length=2000)
class Confirm(BaseModel):
    model_config=ConfigDict(extra='forbid')
    digest:str
    items:list[Approval]=Field(max_length=50)
    effects_confirmed:StrictBool
class Reason(BaseModel):
    model_config=ConfigDict(extra='forbid')
    reason:str=Field(min_length=1,max_length=2000)

class LabWriter:
    def __init__(self,lab,store,source):
        self.lab,self.marker=validate_lab(lab,store.directory,source)
        self.store=store;self.data=self.lab/'data'
        with store.connect() as db:
            db.executescript('''CREATE TABLE IF NOT EXISTS write_batches(
                id TEXT PRIMARY KEY, actor TEXT NOT NULL, request_key TEXT NOT NULL, request_hash TEXT NOT NULL,
                state TEXT NOT NULL, manifest TEXT NOT NULL, UNIQUE(actor,request_key));
                CREATE TABLE IF NOT EXISTS write_receipts(submission_id TEXT PRIMARY KEY,batch_id TEXT NOT NULL,state TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS write_baseline(id INTEGER PRIMARY KEY CHECK(id=1), hashes TEXT NOT NULL);''')
            db.execute('INSERT OR IGNORE INTO write_baseline VALUES(1,?)',(encoded(self.marker['baseline']),))

    @contextmanager
    def lock(self):
        validate_lab(self.lab,self.store.directory,self.data)
        with (self.lab/'maintenance.lock').open('a+b') as f:
            if f.tell()==0:f.write(b'0');f.flush()
            f.seek(0)
            try:
                if os.name=='nt':
                    import msvcrt;msvcrt.locking(f.fileno(),msvcrt.LK_NBLCK,1)
                else:
                    import fcntl;fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
            except OSError:fail('已有批次正在维护，请稍后重试')
            try:yield
            finally:
                f.seek(0)
                if os.name=='nt':msvcrt.locking(f.fileno(),msvcrt.LK_UNLCK,1)
                else:fcntl.flock(f,fcntl.LOCK_UN)

    def guard(self,db,sid):
        if db.execute("SELECT 1 FROM write_batches WHERE state IN ('applying','rolling_back','recovery_required')").fetchone():fail('存在未完成批次，先恢复再审核或应用')
        if db.execute('SELECT 1 FROM write_receipts WHERE submission_id=?',(sid,)).fetchone():fail('该投稿已有应用/回滚回执；请新建投稿，不可改写历史')

    def idle(self,db):
        if db.execute("SELECT 1 FROM write_batches WHERE state IN ('applying','rolling_back','recovery_required')").fetchone():fail('存在未完成批次，请先恢复')

    def row(self,db,bid):
        row=db.execute('SELECT * FROM write_batches WHERE id=?',(bid,)).fetchone()
        if not row:raise HTTPException(404,'批次不存在')
        return row,json.loads(row['manifest'])

    def put(self,db,bid,state,m):
        db.execute('UPDATE write_batches SET state=?,manifest=? WHERE id=?',(state,encoded(m),bid))

    def tools(self):
        if engine_hashes()!=LOADED_ENGINE or {n:filehash(ROOT/n) for n in EXTRA}!=LOADED_EXTRA:fail('工具代码变化，请重启并重新预览')

    def selected(self,db,items):
        rows=[]
        for item in items:
            sid=item['submission_id'];self.guard(db,sid)
            row=db.execute('SELECT * FROM submissions WHERE id=?',(sid,)).fetchone()
            if not row or row['status']!='accepted' or row['revision']!=item['revision'] or sha((row['accepted_payload'] or '').encode())!=item['accepted_hash']:fail('投稿审核版本变化，请重新预览')
            rows.append(row)
        return rows

    def prepare(self,actor,body):
        with self.lock(),self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE');self.idle(db);self.tools()
            fingerprint=sha(encoded(body.model_dump()).encode())
            old=db.execute('SELECT * FROM write_batches WHERE actor=? AND request_key=?',(actor,body.request_key)).fetchone()
            if old:
                if old['request_hash']!=fingerprint:fail('请求标识已用于其他选择')
                return self.detail(old['id'])
            row=db.execute('SELECT * FROM preview_batches WHERE id=?',(body.preview_id,)).fetchone()
            if not row:fail('预览不存在')
            prior=json.loads(row['result_json'])
            data,cars,basis=load_source(self.data)
            if prior['state']!='ready' or basis!=prior['source'] or prior['engine']!=LOADED_ENGINE:fail('预览已过期')
            wanted={(p.id,p.revision) for p in body.items}
            if len(wanted)!=len(body.items):fail('重复选择投稿')
            items=[i for i in prior['items'] if (i['submission_id'],i['revision']) in wanted]
            if len(items)!=len(wanted):fail('选择不属于原预览')
            rows=self.selected(db,items)
            result,preview=build_preview(rows,data,cars,basis)
            if result['state']!='ready' or not result['changes']['changes']:fail('没有可执行改动或存在冲突')
            before=hashes(self.data)
            if before!=json.loads(db.execute('SELECT hashes FROM write_baseline WHERE id=1').fetchone()[0]):fail('测试数据或工作簿有未处理编辑，禁止覆盖；请新建测试环境或先处理编辑')
            bid=secrets.token_hex(16);folder=self.lab/'batches'/bid;folder.mkdir()
            (folder/'before').mkdir();(folder/'after').mkdir()
            for n in FILES:
                raw=(self.data/n).read_bytes();save(folder/'before'/n,raw)
                if sha(raw)!=before[n]:fail('备份期间文件变化')
            save(folder/'before/cars.json',(self.data/'cars.json').read_bytes())
            save(folder/'after/gauntlet_data.json',preview.encode())
            updated=json.loads(preview)
            for n in FILES[1:]:
                check_workbook(folder/'before'/n,data)
                book,_=build_workbook(updated['tracks'])
                try:book.save(folder/'after'/n)
                finally:book.close()
                check_workbook(folder/'after'/n,updated)
            if hashes(self.data)!=before or load_source(self.data)[2]!=basis:fail('准备期间来源变化')
            m={'id':bid,'preview_id':body.preview_id,'actor':actor,'created_at':int(time.time()),'result':result,
               'before':before,'after':hashes(folder/'after'),'extra_tools':LOADED_EXTRA,'events':[], 'lab_only':True}
            m['digest']=sha(encoded(m).encode())
            db.execute('INSERT INTO write_batches VALUES(?,?,?,?,?,?)',(bid,actor,body.request_key,fingerprint,'prepared',encoded(m)))
            return {**m,'state':'prepared'}

    def detail(self,bid):
        with self.store.connect() as db:row,m=self.row(db,bid)
        return {**m,'state':row['state']}

    def replace(self,folder,name):save(self.data/name,(folder/name).read_bytes())

    def restore_files(self,bid,m):
        folder=self.lab/'batches'/bid/'before'
        if filehash(self.data/'cars.json')!=m['result']['source']['cars_sha256']:fail('车辆规则已有后续修改，禁止自动恢复')
        if hashes(folder)!=m['before']:fail('备份校验失败，保留现场，禁止恢复')
        current=hashes(self.data)
        if any(current[n] not in (m['before'][n],m['after'][n]) for n in FILES):fail('检测到批次外改动，保留现场，禁止覆盖恢复')
        for n in reversed(FILES):
            if filehash(self.data/n)!=m['before'][n]:self.replace(folder,n)
        if hashes(self.data)!=m['before']:fail('恢复校验失败')

    def execute(self,actor,bid,body):
        with self.lock():
            with self.store.connect() as db:
                db.execute('BEGIN IMMEDIATE');row,m=self.row(db,bid)
                if row['state']=='applied':return {**m,'state':'applied'}
                self.idle(db);self.tools()
                if row['state']!='prepared' or body.digest!=m['digest']:fail('批次不是待确认状态或摘要已变化')
                rows=self.selected(db,m['result']['items'])
                expected={i['submission_id']:i for i in m['result']['items'] if i['kind']!='unchanged'}
                approvals={i.submission_id:i for i in body.items}
                if len(approvals)!=len(body.items) or set(approvals)!=set(expected) or not body.effects_confirmed:fail('请逐项确认所有改动及镜像/工作簿影响')
                for sid,i in expected.items():
                    a=approvals[sid]
                    if not a.confirmed:fail('存在未确认条目')
                    if i.get('slower') and (not a.slower_confirmed or not a.slower_reason.strip()):fail('更慢成绩必须再次勾选确认并填写原因')
                data,cars,basis=load_source(self.data)
                if basis!=m['result']['source'] or hashes(self.data)!=m['before'] or m['extra_tools']!=LOADED_EXTRA or m['result']['engine']!=LOADED_ENGINE:fail('数据、工作簿或工具变化，确认失效')
                result,preview=build_preview(rows,data,cars,basis)
                folder=self.lab/'batches'/bid
                if result['state']!='ready' or sha(preview.encode())!=m['after']['gauntlet_data.json'] or hashes(folder/'after')!=m['after'] or hashes(folder/'before')!=m['before']:fail('暂存/备份文件校验失败')
                for n in FILES[1:]:check_workbook(folder/'after'/n,json.loads(preview))
                m['approval']={'actor':actor,'time':int(time.time()),**body.model_dump()}
                m['events'].append({'action':'apply_started','at':int(time.time())})
                self.put(db,bid,'applying',m)
            # Durable intent precedes filesystem changes. All review mutations are blocked until resolved.
            try:
                with self.store.connect() as db:
                    db.execute('BEGIN IMMEDIATE')
                    if hashes(self.data)!=m['before'] or load_source(self.data)[2]!=m['result']['source']:fail('执行前来源变化')
                    for n in FILES:self.replace(folder/'after',n)
                    if hashes(self.data)!=m['after']:fail('写入后校验失败')
                    for i in m['result']['items']:
                        if i['kind']=='unchanged':continue
                        db.execute('INSERT INTO write_receipts VALUES(?,?,?)',(i['submission_id'],bid,'applied'))
                    db.execute('UPDATE write_baseline SET hashes=? WHERE id=1',(encoded(m['after']),))
                    m['events'].append({'action':'applied','at':int(time.time())});self.put(db,bid,'applied',m)
            except Exception as e:
                self.recover_locked(actor,bid,'应用失败自动恢复：'+type(e).__name__)
                raise HTTPException(409,'应用失败，已尝试恢复；请查看批次状态后再操作') from e
            return {**m,'state':'applied'}

    def recover_locked(self,actor,bid,reason):
        with self.store.connect() as db:
            row,m=self.row(db,bid)
            if row['state'] not in ('applying','rolling_back','recovery_required'):fail('此批次不需要恢复')
        try:self.restore_files(bid,m)
        except Exception:
            with self.store.connect() as db:self.put(db,bid,'recovery_required',m)
            raise
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            state='rolled_back' if m.get('rollback') else 'failed_restored'
            db.execute('UPDATE write_baseline SET hashes=? WHERE id=1',(encoded(m['before']),))
            db.execute("UPDATE write_receipts SET state='rolled_back' WHERE batch_id=?",(bid,))
            m['events'].append({'action':state,'actor':actor,'reason':reason,'at':int(time.time())});self.put(db,bid,state,m)
        return {**m,'state':state}

    def rollback(self,actor,bid,reason):
        if not reason.strip():fail('必须填写回滚原因')
        with self.lock():
            with self.store.connect() as db:
                db.execute('BEGIN IMMEDIATE');self.idle(db);row,m=self.row(db,bid)
                if row['state']=='rolled_back':return {**m,'state':'rolled_back'}
                if row['state']!='applied':fail('只允许回滚已应用批次')
                if hashes(self.data)!=m['after'] or load_source(self.data)[2]['cars_sha256']!=m['result']['source']['cars_sha256']:fail('应用后已有数据或工作簿修改，禁止覆盖回滚')
                folder=self.lab/'batches'/bid/'rollback-current';folder.mkdir(exist_ok=True)
                for n in FILES:save(folder/n,(self.data/n).read_bytes())
                if hashes(folder)!=m['after']:fail('回滚前备份失败')
                m['rollback']={'actor':actor,'reason':reason,'at':int(time.time())};self.put(db,bid,'rolling_back',m)
            return self.recover_locked(actor,bid,reason)


def install(app,store,root,user,lab,source):
    writer=LabWriter(lab,store,source);app.state.writeback=writer
    def owner(request):
        actor=user(request)
        if request.headers.get('x-account-id')!=actor['id']:raise HTTPException(401,'账号变化，请刷新')
        if actor['role']!='superadmin' or not actor['verified']:raise HTTPException(403,'仅已验证超级管理员可操作测试写回')
        return actor['id']
    def safely(fn,*args):
        try:return fn(*args)
        except (OSError,ValueError,KeyError) as error:
            raise HTTPException(409,'文件校验或操作失败，未完成；请检查文件占用并查看批次恢复状态：'+str(error)) from error
    @app.get('/writeback-lab')
    def page():return FileResponse(root/'writeback_lab.html')
    @app.get('/api/admin/writeback')
    def listing(request:Request):
        owner(request)
        with store.connect() as db:rows=db.execute('SELECT id,state FROM write_batches ORDER BY rowid DESC').fetchall()
        return {'lab':str(writer.lab),'items':[dict(r) for r in rows]}
    @app.post('/api/admin/writeback')
    def prepare(body:Prepare,request:Request):return safely(writer.prepare,owner(request),body)
    @app.get('/api/admin/writeback/{bid}')
    def detail(bid:str,request:Request):owner(request);return writer.detail(bid)
    @app.post('/api/admin/writeback/{bid}/execute')
    def execute(bid:str,body:Confirm,request:Request):return safely(writer.execute,owner(request),bid,body)
    @app.post('/api/admin/writeback/{bid}/rollback')
    def rollback(bid:str,body:Reason,request:Request):return safely(writer.rollback,owner(request),bid,body.reason)
    @app.post('/api/admin/writeback/{bid}/recover')
    def recover(bid:str,body:Reason,request:Request):
        actor=owner(request)
        if not body.reason.strip():fail('必须填写恢复原因')
        with writer.lock():return safely(writer.recover_locked,actor,bid,body.reason)
