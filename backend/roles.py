"""Local owner bootstrap and email-bound, one-use administrator invitations."""
import argparse
import hashlib
from pathlib import Path
import secrets
import time
from typing import Literal

from fastapi import HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel, ConfigDict, Field, StrictInt, field_validator

ROOT=Path(__file__).resolve().parents[1]


def migrate_roles(db):
    version=db.execute('SELECT max(version) FROM schema_version').fetchone()[0]
    if version in (5,6):return
    if version!=4:raise RuntimeError('权限迁移需要数据库v4')
    # Keep existing users rows and foreign keys intact. The singleton owns the
    # effective superadmin role; users.role retains its original compatibility enum.
    statements=[
        '''CREATE TABLE IF NOT EXISTS super_admins(
            slot INTEGER PRIMARY KEY CHECK(slot=1), user_id TEXT NOT NULL UNIQUE REFERENCES users(id), created_at INTEGER NOT NULL)''',
        '''CREATE TABLE IF NOT EXISTS admin_invitations(
            id TEXT PRIMARY KEY, code_hash TEXT NOT NULL UNIQUE, email TEXT NOT NULL,
            issuer_id TEXT NOT NULL REFERENCES users(id), status TEXT NOT NULL
            CHECK(status IN ('open','reserved','used','revoked','expired')),
            reserved_user_id TEXT REFERENCES users(id), used_by TEXT REFERENCES users(id),
            expires_at INTEGER NOT NULL, created_at INTEGER NOT NULL, updated_at INTEGER NOT NULL,
            revision INTEGER NOT NULL DEFAULT 1)''',
        '''CREATE TABLE IF NOT EXISTS invitation_events(
            id INTEGER PRIMARY KEY AUTOINCREMENT, invitation_id TEXT NOT NULL REFERENCES admin_invitations(id),
            actor_id TEXT REFERENCES users(id), action TEXT NOT NULL, created_at INTEGER NOT NULL)''',
        '''CREATE TABLE IF NOT EXISTS access_events(id INTEGER PRIMARY KEY AUTOINCREMENT, actor_id TEXT NOT NULL REFERENCES users(id), target_id TEXT NOT NULL REFERENCES users(id), action TEXT NOT NULL, reason TEXT NOT NULL, created_at INTEGER NOT NULL)''',
        'CREATE INDEX IF NOT EXISTS invitations_email ON admin_invitations(email,status)',
    ]
    for sql in statements:db.execute(sql)
    db.execute('INSERT INTO schema_version VALUES (5)')


def effective_role(db,uid,base_role):
    return 'superadmin' if db.execute('SELECT 1 FROM super_admins WHERE user_id=?',(uid,)).fetchone() else base_role


def event(db,iid,actor,action):
    db.execute('INSERT INTO invitation_events(invitation_id,actor_id,action,created_at) VALUES (?,?,?,?)',(iid,actor,action,int(time.time())))


def valid_invitation(db,code,email):
    row=db.execute('SELECT * FROM admin_invitations WHERE code_hash=?',(hashlib.sha256(code.strip().encode()).hexdigest(),)).fetchone()
    if not row or row['email']!=email.strip().lower() or row['status']!='open' or row['expires_at']<=int(time.time()):
        raise HTTPException(400,'邀请码无效、已使用、已过期或与邮箱不匹配，请联系超级管理员')
    return row


def reserve(db,code,email,uid):
    row=valid_invitation(db,code,email)
    db.execute("UPDATE admin_invitations SET status='reserved',reserved_user_id=?,updated_at=?,revision=revision+1 WHERE id=?",(uid,int(time.time()),row['id']))
    event(db,row['id'],uid,'reserved')


def grant(db,row,uid):
    account=db.execute('SELECT role FROM users WHERE id=?',(uid,)).fetchone()
    if effective_role(db,uid,account['role'])!='player':raise HTTPException(409,'账号已具备管理权限，无需兑换')
    db.execute("UPDATE users SET role='admin' WHERE id=?",(uid,))
    db.execute('INSERT INTO role_events(user_id,old_role,new_role,changed_at) VALUES (?,?,?,?)',(uid,account['role'],'admin',int(time.time())))
    db.execute("UPDATE admin_invitations SET status='used',used_by=?,updated_at=?,revision=revision+1 WHERE id=?",(uid,int(time.time()),row['id']))
    db.execute('DELETE FROM sessions WHERE user_id=?',(uid,))
    event(db,row['id'],uid,'activated')


def complete_pending_invitation(db,uid):
    """Email verification succeeds even when an invite was revoked/expired."""
    row=db.execute('SELECT * FROM admin_invitations WHERE reserved_user_id=? ORDER BY created_at DESC,id DESC LIMIT 1',(uid,)).fetchone()
    if not row or row['status']=='used':return ''
    account=db.execute('SELECT email,role FROM users WHERE id=?',(uid,)).fetchone()
    if effective_role(db,uid,account['role'])!='player':return ''
    if row['status']!='reserved' or row['expires_at']<=int(time.time()):
        if row['status']=='reserved':
            db.execute("UPDATE admin_invitations SET status='expired',revision=revision+1,updated_at=? WHERE id=?",(int(time.time()),row['id']))
            event(db,row['id'],uid,'expired')
        return ' 邀请已失效，未授予管理员权限；可作为玩家登录后联系超级管理员重新邀请。'
    if account['email']!=row['email']:raise HTTPException(409,'邀请邮箱与账号不一致')
    grant(db,row,uid)
    return ' 管理员邀请已生效，请重新登录。'


def set_role(directory,email,role):
    if role not in ('player','admin','superadmin'):raise ValueError('角色无效')
    if not (Path(directory)/'accounts.sqlite3').is_file():raise ValueError('本地账号数据库不存在')
    from backend.app import Store
    store=Store(directory)
    with store.connect() as db:
        db.execute('BEGIN IMMEDIATE')
        row=db.execute('SELECT id,role,verified FROM users WHERE email=?',(email.strip().lower(),)).fetchone()
        if not row or not row['verified']:raise ValueError('账号不存在或邮箱未验证')
        current=effective_role(db,row['id'],row['role'])
        if current==role:return False
        if current=='superadmin':raise ValueError('主号超级管理员不可通过普通角色命令降级')
        if role=='superadmin':
            if db.execute('SELECT 1 FROM super_admins').fetchone():raise ValueError('本地库已有超级管理员，拒绝替换主号')
            db.execute('INSERT INTO super_admins VALUES (1,?,?)',(row['id'],int(time.time())))
            db.execute("UPDATE users SET role='admin' WHERE id=?",(row['id'],))
        else:db.execute('UPDATE users SET role=? WHERE id=?',(role,row['id']))
        db.execute('INSERT INTO role_events(user_id,old_role,new_role,changed_at) VALUES (?,?,?,?)',(row['id'],current,role,int(time.time())))
        db.execute('DELETE FROM sessions WHERE user_id=?',(row['id'],))
    return True


class InviteCreate(BaseModel):
    model_config=ConfigDict(extra='forbid')
    email: str=Field(max_length=254)
    expires_hours: StrictInt=Field(default=72,ge=1,le=168)

    @field_validator('email')
    @classmethod
    def valid_email(cls,value):
        from backend.app import Credentials
        return Credentials.email_valid(value)


class InviteRevision(BaseModel):
    model_config=ConfigDict(extra='forbid')
    revision: StrictInt=Field(ge=1)


class Redeem(BaseModel):
    model_config=ConfigDict(extra='forbid')
    invite_code: str=Field(min_length=20,max_length=128)


class MemberRevoke(BaseModel):
    model_config=ConfigDict(extra='forbid')
    reason: str=Field(min_length=1,max_length=200)


def install(app,store,root,user,production=False):
    def actor(request,owner_only=True):
        current=user(request)
        if request.headers.get('x-account-id')!=current['id']:raise HTTPException(401,'账号已切换，请刷新后重试')
        if not current['verified']:raise HTTPException(403,'请先验证邮箱')
        if owner_only and current['role']!='superadmin':raise HTTPException(403,'仅超级管理员可管理邀请码和管理员')
        return current

    @app.get('/admin-access')
    def page():
        if production:return HTMLResponse((root/'admin_access.html').read_text(encoding='utf-8').replace('本地开发版 · 管理员邀请码不改变公开网站。','管理员权限与邀请码管理'))
        return FileResponse(root/'admin_access.html')

    @app.get('/api/admin/invitations')
    def invitations(request:Request):
        actor(request)
        with store.connect() as db:
            rows=db.execute('SELECT id,email,status,expires_at,created_at,updated_at,revision FROM admin_invitations ORDER BY created_at DESC,id DESC LIMIT 200').fetchall()
        now=int(time.time())
        return {'items':[{**dict(row),'status':'expired' if row['status'] in ('open','reserved') and row['expires_at']<=now else row['status']} for row in rows]}

    @app.post('/api/admin/invitations')
    def create(body:InviteCreate,request:Request):
        current=actor(request)
        store.throttle('invite-create:'+current['id'],20)
        with store.connect() as db:
            db.execute('BEGIN IMMEDIATE');app.state.require_active_session(request,db)
            account=db.execute('SELECT id,role FROM users WHERE email=?',(body.email,)).fetchone()
            if account and effective_role(db,account['id'],account['role'])!='player':raise HTTPException(409,'该邮箱已具备管理权限')
            if db.execute("SELECT 1 FROM admin_invitations WHERE email=? AND status IN ('open','reserved') AND expires_at>?",(body.email,int(time.time()))).fetchone():
                raise HTTPException(409,'该邮箱已有有效邀请；需要替换时请先撤销旧邀请')
            code='rpa_'+secrets.token_urlsafe(32)
            iid=secrets.token_hex(16);now=int(time.time());expires=now+body.expires_hours*3600
            db.execute("INSERT INTO admin_invitations(id,code_hash,email,issuer_id,status,expires_at,created_at,updated_at) VALUES (?,?,?,?,'open',?,?,?)",(iid,hashlib.sha256(code.encode()).hexdigest(),body.email,current['id'],expires,now,now))
            event(db,iid,current['id'],'created')
        return {'id':iid,'code':code,'email':body.email,'expires_at':expires,'revision':1}

    @app.post('/api/admin/invitations/{iid}/revoke')
    def revoke(iid:str,body:InviteRevision,request:Request):
        current=actor(request)
        with store.connect() as db:
            db.execute('BEGIN IMMEDIATE');app.state.require_active_session(request,db);row=db.execute('SELECT * FROM admin_invitations WHERE id=?',(iid,)).fetchone()
            if not row:raise HTTPException(404,'邀请不存在')
            if row['revision']!=body.revision:raise HTTPException(409,'邀请状态已变化，请刷新后操作')
            if row['status'] not in ('open','reserved'):raise HTTPException(409,'该邀请不能撤销；已生效管理员需单独收回权限')
            db.execute("UPDATE admin_invitations SET status='revoked',updated_at=?,revision=revision+1 WHERE id=?",(int(time.time()),iid))
            event(db,iid,current['id'],'revoked')
        return {'message':'邀请已撤销，不能再激活管理员权限'}

    @app.post('/api/auth/redeem-invitation')
    def redeem(body:Redeem,request:Request):
        current=actor(request,False)
        store.throttle('invite-redeem:'+current['id'],10)
        with store.connect() as db:
            db.execute('BEGIN IMMEDIATE');app.state.require_active_session(request,db)
            row=valid_invitation(db,body.invite_code,current['email'])
            grant(db,row,current['id'])
        return {'message':'管理员权限已激活，旧会话已退出，请重新登录'}

    @app.get('/api/admin/members')
    def members(request:Request):
        actor(request)
        with store.connect() as db:
            rows=db.execute("SELECT id,email,role FROM users WHERE role='admin' ORDER BY created_at,id").fetchall()
            result=[{**dict(row),'role':effective_role(db,row['id'],row['role'])} for row in rows]
        return {'items':result}

    @app.post('/api/admin/members/{uid}/revoke')
    def revoke_member(uid:str,body:MemberRevoke,request:Request):
        current=actor(request)
        if not body.reason.strip():raise HTTPException(422,'请填写收回权限的原因')
        with store.connect() as db:
            db.execute('BEGIN IMMEDIATE');app.state.require_active_session(request,db);row=db.execute('SELECT role FROM users WHERE id=?',(uid,)).fetchone()
            if not row:raise HTTPException(404,'账号不存在')
            role=effective_role(db,uid,row['role'])
            if role=='superadmin':raise HTTPException(403,'主号超级管理员不可降级')
            if role!='admin':raise HTTPException(409,'该账号已不是管理员，请刷新')
            db.execute("UPDATE users SET role='player' WHERE id=?",(uid,))
            db.execute('DELETE FROM sessions WHERE user_id=?',(uid,))
            db.execute('INSERT INTO role_events(user_id,old_role,new_role,changed_at) VALUES (?,?,?,?)',(uid,'admin','player',int(time.time())))
            # Separate event records owner action and reason without changing the historical schema.
            db.execute('INSERT INTO access_events(actor_id,target_id,action,reason,created_at) VALUES (?,?,?,?,?)',(current['id'],uid,'revoke_admin',body.reason.strip(),int(time.time())))
        return {'message':'已收回管理员权限并注销其旧会话；账号、车库及投稿保留'}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-dir',type=Path,default=ROOT/'.local-accounts')
    parser.add_argument('--email',required=True)
    parser.add_argument('--role',choices=['admin','player','superadmin'],required=True)
    args=parser.parse_args()
    try:print('角色已更新，旧会话已失效，请重新登录。' if set_role(args.data_dir,args.email,args.role) else '角色已是目标值，无变更。')
    except ValueError as error:parser.exit(1,str(error)+'\n')
if __name__=='__main__':main()
