"""Local account database backup/restore. Never replaces an existing file."""
import argparse
from pathlib import Path
import sqlite3
from backend.app import ROOT


def copy_database(source, target):
    source, target = Path(source).resolve(), Path(target).resolve()
    if not source.is_file(): raise ValueError('源数据库不存在')
    if target.exists(): raise ValueError('目标已存在，拒绝覆盖')
    target.parent.mkdir(parents=True,exist_ok=True)
    # Reserve a new file, so this utility cannot overwrite a user's database.
    with target.open('xb'): pass
    src=sqlite3.connect(source.as_uri()+'?mode=ro',uri=True)
    dst=sqlite3.connect(target)
    try:
        if src.execute('PRAGMA integrity_check').fetchone()[0]!='ok': raise ValueError('源数据库完整性检查失败')
        if src.execute('SELECT max(version) FROM schema_version').fetchone()[0] not in (1,2,3,4): raise ValueError('数据库版本不支持')
        src.backup(dst)
        if dst.execute('PRAGMA integrity_check').fetchone()[0]!='ok': raise ValueError('目标数据库完整性检查失败')
        if dst.execute('PRAGMA foreign_key_check').fetchall(): raise ValueError('数据库外键检查失败')
    finally:
        src.close(); dst.close()
    return target


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['backup','restore'])
    parser.add_argument('--data-dir',type=Path,default=ROOT/'.local-accounts')
    parser.add_argument('--file',type=Path,required=True,help='备份的输出文件，或恢复的输入文件')
    args=parser.parse_args()
    try:
        if args.action=='backup': result=copy_database(args.data_dir/'accounts.sqlite3',args.file)
        else: result=copy_database(args.file,args.data_dir/'accounts.sqlite3')
        print('已校验并完成：',result)
    except (ValueError,OSError,sqlite3.Error) as error: parser.exit(1,str(error)+'\n')

if __name__=='__main__': main()
