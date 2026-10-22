"""Allowlisted account-release bundle; excludes user data, workbooks and writeback lab."""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import tempfile
import zipfile

APP_FILES=('ui.css','index.html','styles.css','config.js','app_state.js','api.js','allocator.js','race_scores.js','gauntlet_data.json','cars.json',
 'auth.js','profile_store.js','accounts.css','submissions.html','submissions.js','submissions.css','admin_access.html','admin_access.js',
 'backend/contributions.py','backend/__init__.py','backend/app.py','backend/mailing.py','backend/roles.py','backend/submissions.py','backend/manage.py','backend/previews.py','backend/production.py',
 'apply_changes.py','format_json.py','data_tools.py','validate_data.py',
 'production/racepick-accounts.service','production/racepick-backup.service','production/racepick-backup.timer','production/nginx-rate.conf','production/nginx-https-location.conf',
 'production/configure.py','production/requirements-linux-py312.lock','production/install-runtime.sh','production/selfcheck.py','PRODUCTION_DEPLOYMENT.md')

BASE_FILES=APP_FILES
SCORE_FILES=('backend/score_repository.py','backend/score_versions.py','backend/score_production.py',
                     'score_versions.html','score_versions.js','production/score-capability.json','SCORE_PRODUCTION_DEPLOYMENT.md')
COMMUNITY_FILES=('backend/community.py','announcements.js','admin_accounts.html','admin_accounts.js')
CONTRIBUTION_FILES=('backend/contribution_production.py','leaderboard.html','leaderboard.js','leaderboard.css','CONTRIBUTIONS_PRODUCTION.md')
APP_FILES=BASE_FILES+SCORE_FILES+COMMUNITY_FILES+CONTRIBUTION_FILES

def digest(raw):return hashlib.sha256(raw).hexdigest()
def allowed(name):return name in APP_FILES or bool(re.fullmatch(r'wheels/[A-Za-z0-9_.+\-]+\.whl',name))
def manifest(contents,provenance):
 files={n:{'sha256':digest(v),'size':len(v)} for n,v in sorted(contents.items())}
 info={'version':1,'target':'ubuntu24.04-x86_64-python3.12','files':files,'provenance':provenance}
 info['id']=digest(json.dumps(info,sort_keys=True).encode())[:24];return info

def pack(code,data,wheels,output,provenance,data_contents=None):
 code,data,wheels,output=map(Path,(code,data,wheels,output))
 if output.exists():raise ValueError('输出文件已存在，不覆盖')
 if data_contents is not None and set(data_contents)!={'cars.json','gauntlet_data.json'}:raise ValueError('数据快照必须且只能包含两份JSON')
 content={n:(data_contents[n] if data_contents is not None and n in data_contents else ((data if n in ('cars.json','gauntlet_data.json') else code)/n).read_bytes()) for n in APP_FILES}
 content.update({'wheels/'+p.name:p.read_bytes() for p in wheels.glob('*.whl')})
 if not any(n.startswith('wheels/') for n in content):raise ValueError('缺少离线依赖')
 info=manifest(content,provenance)
 with zipfile.ZipFile(output,'x',zipfile.ZIP_DEFLATED) as z:
  for n,v in content.items():z.writestr(n,v)
  z.writestr('manifest.json',json.dumps(info,ensure_ascii=False,indent=2))
 return info

def read_bundle(bundle):
 with zipfile.ZipFile(bundle) as z:
  names=z.namelist()
  if len(names)!=len(set(names)) or 'manifest.json' not in names or not set(BASE_FILES)<=set(names) or any(n!='manifest.json' and not allowed(n) for n in names):raise ValueError('发布包文件白名单不匹配')
  if any(i.file_size>40*1024*1024 for i in z.infolist()) or sum(i.file_size for i in z.infolist())>200*1024*1024:raise ValueError('包体积异常')
  for group in (SCORE_FILES,COMMUNITY_FILES,CONTRIBUTION_FILES):
   if set(names)&set(group) and not set(group)<=set(names):raise ValueError('发布包缺少必要组件')
  contents={n:z.read(n) for n in names if n!='manifest.json'};info=json.loads(z.read('manifest.json'))
 if info!=manifest(contents,info['provenance']):raise ValueError('发布包校验失败')
 return contents,info

def verify(target):
 target=Path(target)
 if target.is_symlink():raise ValueError('版本目录不能是链接')
 info=json.loads((target/'manifest.json').read_text(encoding='utf-8'))
 if not set(BASE_FILES)<=set(info['files']) or any(not allowed(n) for n in info['files']):raise ValueError('版本文件白名单异常')
 for group in (SCORE_FILES,COMMUNITY_FILES,CONTRIBUTION_FILES):
  if set(info['files'])&set(group) and not set(group)<=set(info['files']):raise ValueError('发布目录缺少必要组件')
 contents={n:(target/n).read_bytes() for n in info['files']}
 if any((target/n).is_symlink() for n in info['files']) or info!=manifest(contents,info['provenance']) or target.name!=info['id']:raise ValueError('版本校验失败')
 return info

def stage(bundle,base):
 contents,info=read_bundle(bundle);base=Path(base);base.mkdir(parents=True,exist_ok=True);base.chmod(0o755);target=base/info['id']
 if target.exists():verify(target);return target
 temp=Path(tempfile.mkdtemp(prefix='.stage-',dir=base))
 try:
  temp.chmod(0o755)
  for n,v in contents.items():
   p=temp/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(v);p.chmod(0o644)
  (temp/'manifest.json').write_text(json.dumps(info,indent=2),encoding='utf-8')
  for directory in temp.rglob('*'):
   if directory.is_dir():directory.chmod(0o755)
  (temp/'manifest.json').chmod(0o644)
  os.rename(temp,target)
 finally:
  if temp.exists():shutil.rmtree(temp)
 return target

def check_score_compatibility(target,info,data_dir):
 import sqlite3
 from contextlib import closing
 account_db=Path(data_dir).resolve()/'accounts.sqlite3'
 if account_db.exists():
  with closing(sqlite3.connect(account_db.as_uri()+'?mode=ro',uri=True)) as db:
   if db.execute("SELECT 1 FROM sqlite_master WHERE name='contribution_rules'").fetchone():
    rows=db.execute('SELECT version FROM contribution_rules').fetchall()
    cap=Path(target)/'production/score-capability.json'
    if len(rows)!=1 or not set(CONTRIBUTION_FILES)<=set(info['files']) or 'production/score-capability.json' not in info['files'] or json.loads(cap.read_text()).get('contribution_schema')!=rows[0][0]:raise ValueError('贡献规则已启用，禁止切回不能记录贡献的旧程序')
   if db.execute("SELECT 1 FROM sqlite_master WHERE name='community_schema'").fetchone():
    version=db.execute('SELECT max(version) FROM community_schema').fetchone()[0]
    cap=Path(target)/'production/score-capability.json'
    if 'backend/community.py' not in info['files'] or 'production/score-capability.json' not in info['files'] or json.loads(cap.read_text()).get('account_controls_schema')!=version:raise ValueError('账号管理已升级，禁止回退到不能执行停用权限的旧应用')
 root=Path(data_dir)/'score-state'
 if not root.exists():return
 capability=Path(target)/'production/score-capability.json'
 if 'production/score-capability.json' not in info['files']:raise ValueError('成绩已独立版本化，禁止切回不兼容旧应用')
 import sqlite3
 from contextlib import closing
 with closing(sqlite3.connect((Path(data_dir).resolve()/'accounts.sqlite3').as_uri()+'?mode=ro',uri=True)) as db:
  identity=db.execute('SELECT version FROM score_current WHERE slot=1').fetchone()[0]
 if not re.fullmatch('[a-f0-9]{32}',identity):raise ValueError('当前成绩版本指针无效')
 schema=json.loads((root/'scores/versions'/identity/'manifest.json').read_text())['schema']
 if json.loads(capability.read_text()).get('score_schema')!=schema:raise ValueError('目标应用不兼容当前成绩格式；禁止激活')

def activate(base,identity,data_dir=Path('/var/lib/racepick')):
 if os.name!='posix':raise ValueError('激活仅支持Linux')
 if not re.fullmatch('[a-f0-9]{24}',identity):raise ValueError('版本ID无效')
 base=Path(base).resolve();target=base/'releases'/identity;info=verify(target)
 check_score_compatibility(target,info,data_dir)
 if not (target/'.venv/bin/python').exists():raise ValueError('尚未安装并验证运行环境')
 current=base/'current'
 if current.exists() and not current.is_symlink():raise ValueError('current不是链接，禁止覆盖')
 previous=os.readlink(current) if current.is_symlink() else None
 temporary=base/('.current-'+os.urandom(6).hex());os.symlink('releases/'+identity,temporary);os.replace(temporary,current)
 return previous
