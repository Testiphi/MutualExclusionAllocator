"""Explicit local administrator assignment; no web self-promotion endpoint."""
import argparse
import time
from pathlib import Path
from backend.app import Store, ROOT


def set_role(directory,email,role):
    if role not in ('player','admin'): raise ValueError('角色无效')
    # Never bootstrap an empty database due to a mistyped directory.
    if not (Path(directory)/'accounts.sqlite3').is_file(): raise ValueError('本地账号数据库不存在')
    store=Store(directory)
    with store.connect() as db:
        db.execute('BEGIN IMMEDIATE')
        row=db.execute('SELECT id,role,verified FROM users WHERE email=?',(email.strip().lower(),)).fetchone()
        if not row or not row['verified']: raise ValueError('账号不存在或邮箱未验证')
        if row['role']==role: return False
        db.execute('UPDATE users SET role=? WHERE id=?',(role,row['id']))
        db.execute('INSERT INTO role_events(user_id,old_role,new_role,changed_at) VALUES (?,?,?,?)',(row['id'],row['role'],role,int(time.time())))
        db.execute('DELETE FROM sessions WHERE user_id=?',(row['id'],))
    return True


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-dir',type=Path,default=ROOT/'.local-accounts')
    parser.add_argument('--email',required=True)
    parser.add_argument('--role',choices=['admin','player'],required=True)
    args=parser.parse_args()
    try:
        print('角色已更新，旧会话已失效，请重新登录。' if set_role(args.data_dir,args.email,args.role) else '角色已是目标值，无变更。')
    except ValueError as error: parser.exit(1,str(error)+'\n')
if __name__=='__main__': main()
