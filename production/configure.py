"""Run as root on the server; hide SMTP password input and never print secrets."""
import getpass
import json
import os
from pathlib import Path
import re
import warnings

def main():
    if os.name!='posix' or os.geteuid()!=0:raise SystemExit('请在Ubuntu服务器上以root执行')
    import grp
    group=grp.getgrnam('racepick').gr_gid
    os.umask(0o077);folder=Path('/etc/racepick');folder.mkdir(mode=0o750,exist_ok=True)
    config=folder/'production.json';secret=folder/'smtp-password'
    if config.exists() or secret.exists():raise SystemExit('配置已存在，不覆盖；更新时请先备份')
    owner=input('超级管理员主邮箱（必须随后注册验证）：').strip().lower()
    if not re.fullmatch(r'[a-z0-9.!#$%&\'*+/=?^_`{|}~-]+@[a-z0-9.-]+\.[a-z]{2,}',owner):raise SystemExit('邮箱格式错误')
    with warnings.catch_warnings():
        warnings.simplefilter('error',getpass.GetPassWarning)
        password=getpass.getpass('阿里云SMTP专用密码（隐藏输入）：')
        confirm=getpass.getpass('再次输入SMTP专用密码：')
    if not password or password!=confirm:raise SystemExit('密码为空或两次不一致，未保存')
    secret.write_text(password,encoding='utf-8');secret.chmod(0o600)
    config.write_text(json.dumps({'origin':'https://racepick.cn','data_dir':'/var/lib/racepick','owner_email':owner,'mail_daily_limit':100},ensure_ascii=False,indent=2),encoding='utf-8')
    os.chown(folder,0,group);folder.chmod(0o750);os.chown(config,0,group);config.chmod(0o640)
    print('配置已保存；SMTP密码未写入命令历史或发布包')

if __name__=='__main__':main()
