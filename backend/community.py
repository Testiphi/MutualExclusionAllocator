"""Announcements, per-account preferences, and superadministrator account controls."""
import argparse
import json
import secrets
import time
from fastapi import HTTPException,Request
from fastapi.responses import FileResponse
from pydantic import BaseModel,ConfigDict,Field,StrictInt,StrictBool
from typing import Literal

SCHEMA=1
TABLES=(
 'CREATE TABLE community_schema(version INTEGER PRIMARY KEY)',
 'CREATE TABLE account_controls(user_id TEXT PRIMARY KEY REFERENCES users(id),disabled INTEGER NOT NULL CHECK(disabled IN(0,1)),revision INTEGER NOT NULL,updated_at INTEGER NOT NULL)',
 'CREATE TABLE account_login_stats(user_id TEXT PRIMARY KEY REFERENCES users(id),last_login INTEGER NOT NULL)',
 "CREATE TABLE announcements(id TEXT PRIMARY KEY,title TEXT NOT NULL,body TEXT NOT NULL,release_label TEXT NOT NULL,state TEXT NOT NULL CHECK(state IN('draft','published','withdrawn')),revision INTEGER NOT NULL,created_at INTEGER NOT NULL,published_at INTEGER,updated_at INTEGER NOT NULL,actor_id TEXT NOT NULL REFERENCES users(id))",
 'CREATE TABLE announcement_preferences(user_id TEXT PRIMARY KEY REFERENCES users(id),muted INTEGER NOT NULL CHECK(muted IN(0,1)),revision INTEGER NOT NULL)',
 'CREATE TABLE announcement_dismissals(user_id TEXT NOT NULL REFERENCES users(id),announcement_id TEXT NOT NULL REFERENCES announcements(id),created_at INTEGER NOT NULL,PRIMARY KEY(user_id,announcement_id))',
 'CREATE TABLE announcement_events(id INTEGER PRIMARY KEY,announcement_id TEXT NOT NULL,actor_id TEXT NOT NULL,action TEXT NOT NULL,created_at INTEGER NOT NULL)')

def migrate(db):
    if db.execute("SELECT 1 FROM sqlite_master WHERE name='community_schema'").fetchone():
        if db.execute('SELECT max(version) FROM community_schema').fetchone()[0]!=SCHEMA:raise ValueError('账号管理/公告版本不兼容')
        return
    for sql in TABLES:db.execute(sql)
    db.execute('INSERT INTO community_schema VALUES(?)',(SCHEMA,))

def disabled(db,uid):
    row=db.execute('SELECT disabled FROM account_controls WHERE user_id=?',(uid,)).fetchone()
    return bool(row and row[0])

class AccountAction(BaseModel):
    model_config=ConfigDict(extra='forbid')
    action:Literal['disable','restore','logout']
    revision:StrictInt=Field(ge=0)
    reason:str=Field(min_length=1,max_length=200)
class Announcement(BaseModel):
    model_config=ConfigDict(extra='forbid')
    title:str=Field(min_length=1,max_length=120)
    body:str=Field(min_length=1,max_length=6000)
    release_label:str=Field(default='',max_length=80)
class AnnouncementEdit(Announcement):
    revision:StrictInt=Field(ge=1)
class Publish(BaseModel):
    model_config=ConfigDict(extra='forbid')
    action:Literal['publish','withdraw']
    revision:StrictInt=Field(ge=1)
class Preferences(BaseModel):
    model_config=ConfigDict(extra='forbid')
    muted:StrictBool
    revision:StrictInt=Field(ge=0)

def install(app,store,root,user):
    def actor(request,admin=False):
        current=user(request)
        if request.headers.get('x-account-id')!=current['id']:raise HTTPException(401,'账号变化，请刷新')
        if not current['verified'] or (admin and current['role']!='superadmin'):raise HTTPException(403,'需要已验证的超级管理员权限' if admin else '请先验证邮箱')
        return current
    @app.get('/admin-accounts')
    def accounts_page():return FileResponse(root/'admin_accounts.html')
    @app.get('/api/admin/accounts')
    def accounts(request:Request,q:str='',role:Literal['all','player','admin','superadmin']='all',verified:Literal['all','yes','no']='all',status:Literal['all','active','disabled']='all',offset:int=0,activity:Literal['all','today','week','month','inactive','never']='all',order:Literal['registered','interaction','visit']='registered'):
        actor(request,True)
        if len(q)>254 or offset<0:raise HTTPException(422,'筛选参数不正确')
        if not app.state.usage and (activity!='all' or order!='registered'):raise HTTPException(422,'此环境尚未启用活动统计')
        with store.connect() as db:
            has_nickname=bool(db.execute("SELECT 1 FROM sqlite_master WHERE name='contribution_preferences'").fetchone())
            nickname="COALESCE(p.nickname,'')" if has_nickname else "''"
            anonymous="COALESCE(p.anonymous,1)" if has_nickname else '1'
            conditions=['1=1'];args=[]
            if q:
                conditions.append("(u.email LIKE ? ESCAPE '\\' OR "+nickname+" LIKE ? ESCAPE '\\')")
                term='%'+q.strip().replace('\\','\\\\').replace('%','\\%').replace('_','\\_')+'%'
                args.extend([term,term])
            effective="CASE WHEN sa.user_id IS NOT NULL THEN 'superadmin' ELSE u.role END"
            if role!='all':conditions.append(effective+'=?');args.append(role)
            if verified!='all':conditions.append('u.verified=?');args.append(int(verified=='yes'))
            if status!='all':conditions.append('COALESCE(c.disabled,0)=?');args.append(int(status=='disabled'))
            if app.state.usage:
                # Server-owned fixed path, SELECTs only; neither database is changed.
                db.execute('ATTACH DATABASE ? AS usage_stats',(str(app.state.usage.path),))
                from datetime import datetime,timedelta
                from backend.usage import BJ
                today=datetime.now(BJ).replace(hour=0,minute=0,second=0,microsecond=0)
                days={'today':1,'week':7,'month':30,'inactive':30}
                if activity in days:
                    cutoff=int((today-timedelta(days=days[activity]-1)).timestamp())
                    conditions.append('ua.last_interaction'+(' < ?' if activity=='inactive' else ' >= ?'));args.append(cutoff)
                elif activity=='never':conditions.append('ua.last_interaction IS NULL')
            source='FROM users u LEFT JOIN account_controls c ON c.user_id=u.id LEFT JOIN super_admins sa ON sa.user_id=u.id LEFT JOIN account_login_stats ls ON ls.user_id=u.id '
            if has_nickname:source+='LEFT JOIN contribution_preferences p ON p.user_id=u.id '
            if app.state.usage:source+="LEFT JOIN usage_stats.usage_people ua ON ua.actor='a:'||u.id "
            source+='WHERE '+' AND '.join(conditions)
            total=db.execute('SELECT count(*) '+source,args).fetchone()[0]
            activity_fields=',ua.first_seen,ua.last_visit,ua.last_interaction' if app.state.usage else ''
            sorting={'registered':'u.created_at DESC,u.id','interaction':'ua.last_interaction DESC,ua.last_visit DESC,u.created_at DESC,u.id','visit':'ua.last_visit DESC,u.created_at DESC,u.id'}[order]
            rows=db.execute('SELECT u.id,u.email,u.verified,u.created_at,'+nickname+' AS nickname,'+anonymous+' AS leaderboard_anonymous,'+effective+" AS role,COALESCE(c.disabled,0) AS disabled,COALESCE(c.revision,0) AS revision,ls.last_login,(SELECT count(*) FROM submissions s WHERE s.owner_id=u.id) AS submissions "+activity_fields+' '+source+' ORDER BY '+sorting+' LIMIT 50 OFFSET ?',args+[offset]).fetchall()
        return {'total':total,'items':[dict(r) for r in rows]}
    @app.post('/api/admin/accounts/{uid}/control')
    def control(uid:str,body:AccountAction,request:Request):
        owner=actor(request,True)
        if not body.reason.strip():raise HTTPException(422,'请填写操作原因')
        with store.connect() as db:
            db.execute('BEGIN IMMEDIATE');app.state.require_active_session(request,db)
            target=db.execute('SELECT id FROM users WHERE id=?',(uid,)).fetchone()
            if not target:raise HTTPException(404,'账号不存在')
            if db.execute('SELECT 1 FROM super_admins WHERE user_id=?',(uid,)).fetchone():raise HTTPException(403,'超级管理员主号受保护，不能执行此操作')
            old=db.execute('SELECT * FROM account_controls WHERE user_id=?',(uid,)).fetchone();revision=old['revision'] if old else 0
            if revision!=body.revision:raise HTTPException(409,'账号状态已变化，请刷新后重试')
            state=int(body.action=='disable') if body.action!='logout' else int(bool(old and old['disabled']))
            db.execute('INSERT INTO account_controls VALUES(?,?,?,?) ON CONFLICT(user_id) DO UPDATE SET disabled=excluded.disabled,revision=excluded.revision,updated_at=excluded.updated_at',(uid,state,revision+1,int(time.time())))
            if body.action in ('disable','logout'):db.execute('DELETE FROM sessions WHERE user_id=?',(uid,))
            if body.action=='disable':db.execute('DELETE FROM auth_tokens WHERE user_id=?',(uid,))
            db.execute('INSERT INTO access_events(actor_id,target_id,action,reason,created_at) VALUES(?,?,?,?,?)',(owner['id'],uid,body.action,body.reason.strip(),int(time.time())))
        return {'revision':revision+1,'message':'操作完成，账号资料和投稿历史保留'}
    @app.get('/api/admin/accounts/{uid}/events')
    def account_events(uid:str,request:Request):
        actor(request,True)
        with store.connect() as db:rows=db.execute('SELECT action,reason,created_at FROM access_events WHERE target_id=? ORDER BY id DESC LIMIT 30',(uid,)).fetchall()
        return {'items':[dict(r) for r in rows]}
    @app.get('/api/announcements')
    def announcements(offset:int=0):
        if offset<0:raise HTTPException(422,'页码无效')
        with store.connect() as db:
            rows=db.execute("SELECT id,title,body,release_label,revision,published_at FROM announcements WHERE state='published' ORDER BY published_at DESC,id DESC LIMIT 20 OFFSET ?",(offset,)).fetchall()
            total=db.execute("SELECT count(*) FROM announcements WHERE state='published'").fetchone()[0]
        return {'total':total,'items':[dict(r) for r in rows]}
    @app.get('/api/me/announcement-preferences')
    def preferences(request:Request):
        current=actor(request)
        with store.connect() as db:
            row=db.execute('SELECT muted,revision FROM announcement_preferences WHERE user_id=?',(current['id'],)).fetchone()
            ignored=[r[0] for r in db.execute('SELECT announcement_id FROM announcement_dismissals WHERE user_id=?',(current['id'],))]
        return {'muted':bool(row and row['muted']),'revision':row['revision'] if row else 0,'ignored':ignored}
    @app.put('/api/me/announcement-preferences')
    def update_preferences(body:Preferences,request:Request):
        current=actor(request)
        with store.connect() as db:
            db.execute('BEGIN IMMEDIATE');app.state.require_active_session(request,db)
            row=db.execute('SELECT revision FROM announcement_preferences WHERE user_id=?',(current['id'],)).fetchone()
            if (row['revision'] if row else 0)!=body.revision:raise HTTPException(409,'提醒设置已在其他窗口修改，请刷新')
            db.execute('INSERT INTO announcement_preferences VALUES(?,?,?) ON CONFLICT(user_id) DO UPDATE SET muted=excluded.muted,revision=excluded.revision',(current['id'],int(body.muted),body.revision+1))
        return {'revision':body.revision+1,'muted':body.muted}
    @app.post('/api/me/announcements/{aid}/dismiss')
    def dismiss(aid:str,request:Request):
        current=actor(request)
        with store.connect() as db:
            db.execute('BEGIN IMMEDIATE');app.state.require_active_session(request,db)
            if not db.execute("SELECT 1 FROM announcements WHERE id=? AND state='published'",(aid,)).fetchone():raise HTTPException(404,'公告不存在或已撤下')
            db.execute('INSERT OR IGNORE INTO announcement_dismissals VALUES(?,?,?)',(current['id'],aid,int(time.time())))
        return {'ignored':True}
    @app.delete('/api/me/announcements/{aid}/dismiss')
    def undo_dismiss(aid:str,request:Request):
        current=actor(request)
        with store.connect() as db:
            db.execute('BEGIN IMMEDIATE');app.state.require_active_session(request,db)
            db.execute('DELETE FROM announcement_dismissals WHERE user_id=? AND announcement_id=?',(current['id'],aid))
        return {'ignored':False}
    @app.get('/api/admin/announcements')
    def admin_announcements(request:Request):
        actor(request,True)
        with store.connect() as db:rows=db.execute('SELECT * FROM announcements ORDER BY created_at DESC,id DESC LIMIT 100').fetchall()
        return {'items':[dict(r) for r in rows]}
    def text_fields(body):
        title=body.title.strip();content=body.body.strip()
        if not title or not content:raise HTTPException(422,'公告标题与正文不能为空')
        return title,content,body.release_label.strip()
    @app.post('/api/admin/announcements')
    def create(body:Announcement,request:Request):
        owner=actor(request,True);title,content,label=text_fields(body);aid=secrets.token_hex(16);now=int(time.time())
        with store.connect() as db:
            db.execute('BEGIN IMMEDIATE');app.state.require_active_session(request,db)
            db.execute("INSERT INTO announcements VALUES(?,?,?,?,'draft',1,?,NULL,?,?)",(aid,title,content,label,now,now,owner['id']))
            db.execute('INSERT INTO announcement_events(announcement_id,actor_id,action,created_at) VALUES(?,?,?,?)',(aid,owner['id'],'create',now))
        return {'id':aid,'revision':1}
    @app.put('/api/admin/announcements/{aid}')
    def edit(aid:str,body:AnnouncementEdit,request:Request):
        owner=actor(request,True);title,content,label=text_fields(body)
        with store.connect() as db:
            db.execute('BEGIN IMMEDIATE');app.state.require_active_session(request,db)
            row=db.execute('SELECT revision FROM announcements WHERE id=?',(aid,)).fetchone()
            if not row:raise HTTPException(404,'公告不存在')
            if row['revision']!=body.revision:raise HTTPException(409,'公告已变化，请重新载入')
            db.execute('UPDATE announcements SET title=?,body=?,release_label=?,revision=revision+1,updated_at=? WHERE id=?',(title,content,label,int(time.time()),aid))
            db.execute('INSERT INTO announcement_events(announcement_id,actor_id,action,created_at) VALUES(?,?,?,?)',(aid,owner['id'],'edit',int(time.time())))
        return {'revision':body.revision+1}
    @app.post('/api/admin/announcements/{aid}/state')
    def publish(aid:str,body:Publish,request:Request):
        owner=actor(request,True)
        with store.connect() as db:
            db.execute('BEGIN IMMEDIATE');app.state.require_active_session(request,db)
            row=db.execute('SELECT revision,published_at FROM announcements WHERE id=?',(aid,)).fetchone()
            if not row:raise HTTPException(404,'公告不存在')
            if row['revision']!=body.revision:raise HTTPException(409,'公告已变化，请刷新')
            state='published' if body.action=='publish' else 'withdrawn';now=int(time.time())
            db.execute('UPDATE announcements SET state=?,revision=revision+1,published_at=?,updated_at=? WHERE id=?',(state,row['published_at'] or (now if state=='published' else None),now,aid))
            db.execute('INSERT INTO announcement_events(announcement_id,actor_id,action,created_at) VALUES(?,?,?,?)',(aid,owner['id'],body.action,now))
        return {'revision':body.revision+1,'state':state}

if __name__=='__main__':
    from pathlib import Path
    from backend.production import settings,require_database,service_lock
    parser=argparse.ArgumentParser(description='停服备份后迁移公告及账号管理元数据，不改账号和成绩')
    parser.add_argument('--config',type=Path,default=Path('/etc/racepick/production.json'))
    args=parser.parse_args();config=settings(args.config);path=require_database(config,require_community=False)
    # Backup uses the previous release while it is still selected; this CLI uses direct consistent copy.
    from backend.manage import copy_database
    from backend.production import stamp
    with service_lock(path):
        folder=path/'backups';folder.mkdir(exist_ok=True)
        saved=copy_database(path/'accounts.sqlite3',folder/('pre-community-'+stamp()+'.sqlite3'))
        saved.chmod(0o600)
        import sqlite3
        from contextlib import closing
        with closing(sqlite3.connect(path/'accounts.sqlite3')) as db,db:
            db.execute('PRAGMA foreign_keys=ON');db.execute('BEGIN IMMEDIATE');migrate(db)
        print('公告/账号管理元数据迁移完成；旧账号资料保持；迁移前备份：',saved)
