"""Production entry point: HTTPS proxy, fresh persistent database, SMTP credentials."""
import argparse
from contextlib import contextmanager, closing
from datetime import datetime,timezone
import json
import os
from pathlib import Path
import sqlite3
import stat
from backend.app import Store, Credentials, create_app
from backend.mailing import MailConfig
from backend.manage import copy_database
from backend.roles import set_role


def settings(path):
    data=json.loads(Path(path).read_text(encoding='utf-8'))
    if set(data)!={'origin','data_dir','owner_email','mail_daily_limit'}:raise ValueError('生产配置字段不正确')
    if data['origin']!='https://racepick.cn':raise ValueError('本发布包只允许https://racepick.cn')
    data['owner_email']=Credentials.email_valid(data['owner_email'])
    directory=Path(data['data_dir'])
    if not directory.is_absolute() or directory.is_symlink():raise ValueError('数据目录必须是独立绝对路径')
    if directory.resolve().is_relative_to(Path(__file__).resolve().parents[1]):raise ValueError('生产数据不能位于发布目录')
    if type(data['mail_daily_limit']) is not int or not 1<=data['mail_daily_limit']<=10000:raise ValueError('发信额度不正确')
    return data

def marker(config):return {'kind':'racepick-production-v1','origin':config['origin'],'owner_email':config['owner_email']}

def require_database(config,require_community=True):
    path=Path(config['data_dir'])
    if json.loads((path/'production.json').read_text(encoding='utf-8'))!=marker(config):raise ValueError('生产库标记与配置不一致，禁止导入本地测试库')
    if not (path/'accounts.sqlite3').is_file():raise ValueError('生产数据库不存在')
    with closing(sqlite3.connect((path/'accounts.sqlite3').as_uri()+'?mode=ro',uri=True)) as db:
        if db.execute('SELECT max(version) FROM schema_version').fetchone()[0]!=6:raise ValueError('生产库版本不兼容，先备份并单独评估迁移')
        if require_community:
            if not db.execute("SELECT 1 FROM sqlite_master WHERE name='community_schema'").fetchone() or db.execute('SELECT max(version) FROM community_schema').fetchone()[0]!=1:raise ValueError('账号管理升级未完成，请先停服备份并运行backend.community迁移')
        if db.execute("SELECT 1 FROM sqlite_master WHERE name='write_batches'").fetchone():raise ValueError('禁止使用写回实验室数据库')
        if db.execute("SELECT 1 FROM sqlite_master WHERE name='score_current'").fetchone():
            if not db.execute("SELECT 1 FROM sqlite_master WHERE name='score_control'").fetchone() or not (path/'score-state/production-scores.json').is_file():raise ValueError('版本化成绩绑定缺失，不能回退到代码包数据')
    return path

def initialize(config):
    path=Path(config['data_dir']);path.mkdir(parents=True,exist_ok=True)
    # systemd may already have created an empty state directory. Never replace an existing database.
    if any(path.iterdir()):raise ValueError('初始化只接受空目录；不会覆盖或导入已有账号库')
    if os.name=='posix':path.chmod(0o700)
    Store(path)
    (path/'production.json').write_text(json.dumps(marker(config),ensure_ascii=False),encoding='utf-8')
    if os.name=='posix':
        for p in path.iterdir():p.chmod(0o600)

def make_app(config,password):
    path=require_database(config)
    score_state=path/'score-state' if (path/'score-state').exists() else None
    return create_app(path,config['origin'],score_state=score_state,mail_config=MailConfig('smtp','',password,production=True,daily_limit=config['mail_daily_limit']),production=True)

@contextmanager
def service_lock(path):
    if os.name!='posix':raise ValueError('生产服务和恢复工具只支持Linux；本地测试请使用测试入口')
    import fcntl
    with (path/'service.lock').open('a+b') as f:
        try:fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except OSError:raise ValueError('服务正在运行，请先停止racepick-accounts再执行恢复') from None
        try:yield
        finally:fcntl.flock(f,fcntl.LOCK_UN)

def stamp():return datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
def backup(config):
    path=require_database(config)
    if (path/'score-state').exists():
        from backend.score_production import backup as scores_backup
        return scores_backup(config)
    directory=path/'backups';directory.mkdir(exist_ok=True)
    return copy_database(path/'accounts.sqlite3',directory/('accounts-'+stamp()+'.sqlite3'))
def bootstrap(config):
    path=require_database(config)
    with closing(sqlite3.connect(path/'accounts.sqlite3')) as db:
        row=db.execute('SELECT verified FROM users WHERE email=?',(config['owner_email'],)).fetchone()
        if not row or not row[0]:raise ValueError('请先使用配置中的主邮箱注册并完成真实邮件验证')
    backup(config)
    set_role(path,config['owner_email'],'superadmin')

def restore(config,source):
    path=require_database(config)
    with service_lock(path):
        if (path/'score-state').exists():raise ValueError('版本化成绩库不能只恢复SQLite；先校验成套备份并执行restore-drill，再按停服成套恢复流程处理')
        source=Path(source).resolve()
        if source==path/'accounts.sqlite3':raise ValueError('备份不能是正在使用的数据库')
        temp=path/('restore-'+stamp()+'.sqlite3')
        copy_database(source,temp)
        try:
            with closing(sqlite3.connect(temp)) as db, db:
                if db.execute('SELECT max(version) FROM schema_version').fetchone()[0]!=6:raise ValueError('只恢复兼容v6备份')
                if db.execute("SELECT 1 FROM sqlite_master WHERE name IN ('write_batches','score_current')").fetchone():raise ValueError('拒绝实验室或版本化数据库的单文件恢复')
                if not db.execute("SELECT 1 FROM sqlite_master WHERE name='community_schema'").fetchone() or db.execute("SELECT max(version) FROM community_schema").fetchone()[0]!=1:raise ValueError('备份缺少兼容的账号管理状态，禁止直接回退')
                owner=db.execute('SELECT email FROM users JOIN super_admins ON users.id=super_admins.user_id').fetchone()
                if owner and owner[0]!=config['owner_email']:raise ValueError('备份超级管理员与配置不同')
                db.execute('DELETE FROM sessions');db.execute('DELETE FROM auth_tokens')
            backup(config)
            if any((path/('accounts.sqlite3'+suffix)).exists() for suffix in ('-wal','-shm','-journal')):raise ValueError('存在数据库日志文件，需先核查，不覆盖恢复')
            os.replace(temp,path/'accounts.sqlite3')
        finally:temp.unlink(missing_ok=True)

def validate_credential_metadata(directory_info,file_info):
    # systemd may expose root-owned 0550/0440 copies using per-service ACLs.
    # These are not ordinary shared-group secret files: the directory below is fixed.
    if not stat.S_ISDIR(directory_info.st_mode) or directory_info.st_uid!=0 or stat.S_IMODE(directory_info.st_mode) not in (0o500,0o550):
        raise ValueError('systemd凭据目录权限或所有者异常')
    if not stat.S_ISREG(file_info.st_mode) or file_info.st_uid!=0 or stat.S_IMODE(file_info.st_mode) not in (0o400,0o440):
        raise ValueError('systemd凭据副本权限或所有者异常')

def load_smtp_credential():
    value=os.environ.get('CREDENTIALS_DIRECTORY')
    expected=Path('/run/credentials/racepick-accounts.service')
    if not value or Path(value)!=expected or expected.resolve()!=expected:
        raise ValueError('必须从本服务的systemd专用凭据目录读取SMTP密码')
    directory_info=expected.lstat()
    secret=expected/'smtp-password'
    fd=os.open(secret,os.O_RDONLY|os.O_NOFOLLOW)
    with os.fdopen(fd,'r',encoding='utf-8') as stream:
        validate_credential_metadata(directory_info,os.fstat(stream.fileno()))
        password=stream.read(4097)
    if len(password)>4096:raise ValueError('SMTP凭据长度异常')
    password=password.rstrip('\r\n')
    if not password:raise ValueError('SMTP凭据为空')
    return password

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['init','serve','bootstrap-owner','backup','restore'])
    parser.add_argument('--config',type=Path,default=Path('/etc/racepick/production.json'))
    parser.add_argument('--backup',type=Path)
    args=parser.parse_args();os.umask(0o077)
    try:
        config=settings(args.config)
        if args.action=='init':initialize(config);print('全新生产数据库已初始化，未创建测试账号')
        elif args.action=='bootstrap-owner':bootstrap(config);print('已验证主号已设为超级管理员；请重新登录')
        elif args.action=='backup':print(backup(config))
        elif args.action=='restore':
            if not args.backup:raise ValueError('恢复必须指定--backup')
            restore(config,args.backup);print('已恢复兼容备份并撤销会话及验证链接，请重启并验收')
        else:
            import uvicorn
            path=require_database(config)
            password=load_smtp_credential()
            with service_lock(path):uvicorn.run(make_app(config,password),host='127.0.0.1',port=8001,proxy_headers=False,access_log=False)
    except (OSError,ValueError,sqlite3.Error) as error:parser.exit(1,str(error)+'\n')

if __name__=='__main__':main()
