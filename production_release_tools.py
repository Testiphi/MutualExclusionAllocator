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
FEEDBACK_FILES=('backend/feedback.py','backend/feedback_production.py','feedback.html','feedback.js','FEEDBACK_PRODUCTION.md')
GLOBAL_FILES=('cars.global.json','gauntlet_data.global.json','global-data-manifest.json','tools/build_global_data.py')
NOTIFICATION_FILES=('backend/notifications.py','backend/notification_production.py','notifications.js','NOTIFICATIONS_LOCAL.md')
USAGE_FILES=('backend/usage.py','backend/usage_production.py','usage.js','usage_admin.js','usage.html','usage.css','USAGE_LOCAL.md')
COVERAGE_FILES=('backend/coverage.py','backend/coverage_production.py','coverage.html','coverage.js','coverage.css','COVERAGE_DEPLOYMENT.md')
THEME_FILES=('theme.css',)
SCOPED_FILES=('backend/score_scopes.py','backend/global_scores.py','backend/global_score_production.py','GLOBAL_SUBMISSIONS_DEPLOYMENT.md')
COMPONENT_GROUPS=(SCOPED_FILES,COVERAGE_FILES,THEME_FILES,SCORE_FILES,COMMUNITY_FILES,CONTRIBUTION_FILES,FEEDBACK_FILES,GLOBAL_FILES,NOTIFICATION_FILES,USAGE_FILES)
SELECTION_FILES=('selection_core.js',)
MINI_FILES=('backend/mini_auth.py','backend/mini_api.py','production/mini-config.example.json','production/mini.env.example','MINI_API_CONTRACT_20261102.md','MINI_DEPLOYMENT_20261102.md')
MINI_ACCOUNT_FILES=('backend/mini_accounts.py','production/mini-account-config.example.json','MINI_ACCOUNT_CONTRACT_A_20261103.md')
GLOBAL_PROFILE_FILES=('backend/global_profiles.py','GLOBAL_PROFILE_CLOUD_20261103.md')
MIRROR_FILES=('backend/mini_features.py','MINI_FEATURES_COMMON_20261103.md','MINI_BATCH_B_20261103.md','MINI_BATCH_C_20261103.md','MINI_BATCH_D_20261103.md','MINI_BATCH_E_20261103.md','MINI_FEATURES_OPENAPI_20261103.json')
HOME_FILES=('home_presenter.js','home_theme.json','HOME_PRESENTER_CONTRACT_20261103.md')
MAINTENANCE_FILES=('backend/maintenance_release.py','production_release_tools.py','MAINTENANCE_RELEASE_20261103.md')
COMPONENT_GROUPS=COMPONENT_GROUPS+(MINI_FILES,MINI_ACCOUNT_FILES,GLOBAL_PROFILE_FILES,MIRROR_FILES,HOME_FILES,MAINTENANCE_FILES)
APP_FILES=BASE_FILES+SCOPED_FILES+COVERAGE_FILES+THEME_FILES+SCORE_FILES+COMMUNITY_FILES+CONTRIBUTION_FILES+FEEDBACK_FILES+GLOBAL_FILES+NOTIFICATION_FILES+USAGE_FILES+SELECTION_FILES+MINI_FILES+MINI_ACCOUNT_FILES+GLOBAL_PROFILE_FILES+MIRROR_FILES+HOME_FILES+MAINTENANCE_FILES+('backend/mini_result.py',)
ISOLATED_ACCOUNT_FILES=('backend/mini_account_boundary.py','backend/mini_account_isolation.py','backend/mini_account_service.py','backend/mini_snapshot.py')
APP_FILES+=ISOLATED_ACCOUNT_FILES
COMPONENT_GROUPS+=(ISOLATED_ACCOUNT_FILES,)
ROUTE_VIDEO_FILES=('backend/route_videos.py','backend/route_video_release.py','route_videos.js',
                  'route-video-seed.json','ROUTE_VIDEO_RELEASE.md')
APP_FILES+=ROUTE_VIDEO_FILES
COMPONENT_GROUPS+=(ROUTE_VIDEO_FILES,)
OCR_CODE_FILES=('backend/map_layout.py','backend/map_recognition.py','backend/map_ocr_engine.py','backend/map_ocr_worker.py',
 'backend/map_ocr_production.py','backend/map_ocr_supervisor.py','map_recognition.js','map_recognition.css',
 'production/ocr-models.json','production/ocr-assets.json','production/ocr-selfcheck.py','production/racepick-map-ocr.service',
 'MAP_OCR_DEPLOYMENT.md')
OCR_ASSET_FILES=('ocr/v5_det.onnx','ocr/v5_rec.onnx','ocr/v5_keys.txt','licenses/MaaCommonAssets-MIT.txt',
 'licenses/MaaCommonAssets-OCR.md','licenses/PaddleOCR-Apache-2.0.txt','production/ocr-provenance.json','licenses/THIRD_PARTY_NOTICES.md')
OCR_FILES=OCR_CODE_FILES+OCR_ASSET_FILES
COMPONENT_GROUPS=COMPONENT_GROUPS+(OCR_FILES,)

def verify_ocr(contents):
 if not set(contents)&set(OCR_FILES):return
 if not set(OCR_FILES)<=set(contents):raise ValueError('发布包缺少识图组件')
 assets=json.loads(contents['production/ocr-assets.json'])
 if set(assets)!=set(OCR_ASSET_FILES):raise ValueError('识图资产白名单不匹配')
 for name,record in assets.items():
  if digest(contents[name])!=record['sha256'] or len(contents[name])!=record['bytes']:raise ValueError('识图资产哈希不匹配')
 models=json.loads(contents['production/ocr-models.json'])['models']
 if set(models)!= {'det','rec','keys'} or any(item['path'] not in assets or item['sha256']!=assets[item['path']]['sha256'] for item in models.values()):raise ValueError('识图模型与固定资产不一致')

def verify_global_data(contents):
 if not set(contents)&set(GLOBAL_FILES):return # Historical releases remain readable.
 if not set(GLOBAL_FILES)<=set(contents):raise ValueError('发布包缺少国际服组件')
 catalog,scores,declared=(json.loads(contents[n]) for n in GLOBAL_FILES[:3])
 meta=catalog.get('_meta')
 if not isinstance(meta,dict) or meta.get('server_id')!='global' or meta.get('schema_version')!=1 or meta!=scores.get('_meta') or meta!=declared.get('_meta'):raise ValueError('国际服数据版本不一致')
 if set(declared.get('files',{}))!=set(GLOBAL_FILES[:2]):raise ValueError('国际服数据文件集合不一致')
 binding={'server_id':'global','schema_version':1}
 canonical=lambda value:json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode('utf-8')
 for name,value,field in zip(GLOBAL_FILES[:2],(catalog,scores),('catalog_payload_sha256','scores_payload_sha256')):
  raw=contents[name];record=declared['files'][name]
  payload_hash=digest(canonical({k:v for k,v in value.items() if k!='_meta'}));binding[field]=payload_hash
  if record.get('sha256')!=digest(raw) or record.get('bytes')!=len(raw) or record.get('payload_sha256')!=payload_hash or meta.get(field)!=payload_hash:raise ValueError('国际服数据哈希不一致')
 if meta.get('dataset_version')!=digest(canonical(binding)):raise ValueError('国际服数据集版本校验失败')

def digest(raw):return hashlib.sha256(raw).hexdigest()
def allowed(name):return name in APP_FILES or name in OCR_FILES or bool(re.fullmatch(r'wheels/[A-Za-z0-9_.+\-]+\.whl',name))

def verify_selection(contents):
 if set(contents)&set(ROUTE_VIDEO_FILES):
  if not set(ROUTE_VIDEO_FILES)<=set(contents):raise ValueError('发布包缺少跑法参考组件')
  seed=json.loads(contents['route-video-seed.json'])
  if len(seed.get('videos',[]))!=sum(item['videos'] for item in seed['totals'].values()):raise ValueError('跑法参考数量不一致')
 if b'from backend.mini_result import native_result' in contents.get('backend/mini_api.py',b'') and 'backend/mini_result.py' not in contents:
  raise ValueError('发布包缺少原生结果校验组件')
 if b'from backend import mini_features' in contents.get('backend/mini_accounts.py',b'') and not set(MIRROR_FILES)<=set(contents):raise ValueError('发布包缺少原生B-E组件')
 if b'home_presenter.js' in contents['index.html'] and not set(HOME_FILES)<=set(contents):raise ValueError('发布包缺少主页presenter组件')
 if 'home_theme.json' in contents:
  theme=json.loads(contents['home_theme.json'])
  for name,item in theme['sources'].items():
   if digest(item['text'].encode('utf-8'))!=item['sha256_utf8_lf']:raise ValueError('主题导出内容校验失败')
   if name in contents and digest(contents[name].replace(b'\r\n',b'\n'))!=item['sha256_utf8_lf']:raise ValueError('主题导出与当前CSS不一致')
 if b'from backend.global_profiles import state as global_profile_state' in contents.get('backend/app.py',b'') and not set(GLOBAL_PROFILE_FILES)<=set(contents):
  raise ValueError('发布包缺少国际账号车库组件')
 if b'from backend.mini_accounts import make_native_account' in contents.get('backend/mini_api.py',b'') and not set(MINI_ACCOUNT_FILES)<=set(contents):
  raise ValueError('发布包缺少原生账号适配组件')
 if b'from backend.mini_api import MiniGateway' in contents.get('backend/app.py',b'') and not set(MINI_FILES)<=set(contents):
  raise ValueError('发布包缺少原生适配组件')
 # New pages must carry their dependency; historical pages/bundles remain verifiable.
 if re.search(rb'<script\b[^>]*\bsrc\s*=\s*[\"\'](?:\./)?selection_core\.js[\"\']',contents['index.html']) and 'selection_core.js' not in contents:
  raise ValueError('网页缺少共享选择核心')
def manifest(contents,provenance):
 files={n:{'sha256':digest(v),'size':len(v)} for n,v in sorted(contents.items())}
 info={'version':1,'target':'ubuntu24.04-x86_64-python3.12','files':files,'provenance':provenance}
 info['id']=digest(json.dumps(info,sort_keys=True).encode())[:24];return info

def pack(code,data,wheels,output,provenance,data_contents=None,ocr_assets=None):
 code,data,wheels,output=map(Path,(code,data,wheels,output))
 if output.exists():raise ValueError('输出文件已存在，不覆盖')
 snapshot_sets=({'cars.json','gauntlet_data.json'},{'cars.json','gauntlet_data.json',*GLOBAL_FILES[:3]})
 if data_contents is not None and set(data_contents) not in snapshot_sets:raise ValueError('数据快照必须为两份国服JSON或完整五份双服JSON')
 content={n:(data_contents[n] if data_contents is not None and n in data_contents else ((data if n in ('cars.json','gauntlet_data.json') else code)/('docs/'+n if n.endswith('.md') or n=='MINI_FEATURES_OPENAPI_20261103.json' else n)).read_bytes()) for n in APP_FILES}
 if ocr_assets is not None:
  content.update({n:(code/('docs/'+n if n.endswith('.md') or n=='MINI_FEATURES_OPENAPI_20261103.json' else n)).read_bytes() for n in OCR_CODE_FILES})
  content.update({n:(Path(ocr_assets)/n).read_bytes() for n in OCR_ASSET_FILES})
 verify_ocr(content)
 content.update({'wheels/'+p.name:p.read_bytes() for p in wheels.glob('*.whl')})
 if not any(n.startswith('wheels/') for n in content):raise ValueError('缺少离线依赖')
 verify_global_data(content)
 verify_selection(content)
 info=manifest(content,provenance)
 with zipfile.ZipFile(output,'x',zipfile.ZIP_DEFLATED) as z:
  for n,v in content.items():z.writestr(n,v)
  z.writestr('manifest.json',json.dumps(info,ensure_ascii=False,indent=2))
 return info

def read_bundle(bundle):
 with zipfile.ZipFile(bundle) as z:
  names=z.namelist()
  if len(names)!=len(set(names)) or 'manifest.json' not in names or not set(BASE_FILES)<=set(names) or any(n!='manifest.json' and not allowed(n) for n in names):raise ValueError('发布包文件白名单不匹配')
  if any(i.file_size>128*1024*1024 for i in z.infolist()) or sum(i.file_size for i in z.infolist())>512*1024*1024:raise ValueError('包体积异常')
  for group in COMPONENT_GROUPS:
   if set(names)&set(group) and not set(group)<=set(names):raise ValueError('发布包缺少必要组件')
  contents={n:z.read(n) for n in names if n!='manifest.json'};info=json.loads(z.read('manifest.json'))
 if info!=manifest(contents,info['provenance']):raise ValueError('发布包校验失败')
 verify_global_data(contents)
 verify_ocr(contents)
 verify_selection(contents)
 return contents,info

def verify(target):
 target=Path(target)
 if target.is_symlink():raise ValueError('版本目录不能是链接')
 info=json.loads((target/'manifest.json').read_text(encoding='utf-8'))
 if not set(BASE_FILES)<=set(info['files']) or any(not allowed(n) for n in info['files']):raise ValueError('版本文件白名单异常')
 for group in COMPONENT_GROUPS:
  if set(info['files'])&set(group) and not set(group)<=set(info['files']):raise ValueError('发布目录缺少必要组件')
 contents={n:(target/n).read_bytes() for n in info['files']}
 if any((target/n).is_symlink() for n in info['files']) or info!=manifest(contents,info['provenance']) or target.name!=info['id']:raise ValueError('版本校验失败')
 verify_global_data(contents)
 verify_ocr(contents)
 verify_selection(contents)
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
 queue_db=Path(data_dir).resolve()/'map-recognition'/'recognition.sqlite3'
 if queue_db.is_file():
  with closing(sqlite3.connect(queue_db.as_uri()+'?mode=ro',uri=True)) as queue:
   tables={row[0] for row in queue.execute("SELECT name FROM sqlite_master WHERE type='table'")}
   if 'safety_schema' in tables or 'safety_checks' in tables:
    rows=queue.execute('SELECT version FROM safety_schema').fetchall() if 'safety_schema' in tables else []
    cap=Path(target)/'production/score-capability.json'
    if rows!=[(1,)] or 'safety_checks' not in tables or 'production/score-capability.json' not in info['files'] or not cap.is_file() or json.loads(cap.read_text()).get('ocr_queue_safety_schema')!=1:
     raise ValueError('识图安全队列已准备或状态异常，禁止切回不计算checking容量的旧应用')
 account_db=Path(data_dir).resolve()/'accounts.sqlite3'
 if (Path(data_dir).resolve()/'usage.sqlite3').exists():
  cap=Path(target)/'production/score-capability.json'
  if not set(USAGE_FILES)<=set(info['files']) or 'production/score-capability.json' not in info['files'] or json.loads(cap.read_text()).get('usage_schema')!=1:raise ValueError('统计库已启用，禁止切回不兼容旧程序')
 if account_db.exists():
  with closing(sqlite3.connect(account_db.as_uri()+'?mode=ro',uri=True)) as db:
   if db.execute("SELECT 1 FROM sqlite_master WHERE name='maintenance_releases'").fetchone():
    active=any(json.loads(row[0]).get('state')=='applied' for row in db.execute('SELECT receipt FROM maintenance_releases'))
    cap=Path(target)/'production/score-capability.json'
    if active and (not set(MAINTENANCE_FILES)<=set(info['files']) or not cap.is_file() or json.loads(cap.read_text()).get('maintenance_release')!=1):raise ValueError('维护版本及车辆规则已发布，禁止切回不兼容旧应用；须先定点回退维护版本')
   if db.execute("SELECT 1 FROM sqlite_master WHERE name='global_profile_schema'").fetchone():
    rows=db.execute('SELECT version FROM global_profile_schema').fetchall();cap=Path(target)/'production/score-capability.json'
    if len(rows)!=1 or rows[0][0]!=1 or not set(GLOBAL_PROFILE_FILES)<=set(info['files']) or 'production/score-capability.json' not in info['files'] or json.loads(cap.read_text()).get('global_profile_schema')!=1:raise ValueError('国际账号车库已启用，禁止切回不兼容旧应用')
   if db.execute("SELECT 1 FROM sqlite_master WHERE name='global_score_control'").fetchone():
    cap=Path(target)/'production/score-capability.json'
    if not set(SCOPED_FILES)<=set(info['files']) or 'production/score-capability.json' not in info['files'] or json.loads(cap.read_text()).get('global_score_schema')!=1:raise ValueError('国际成绩状态已启用，禁止切回不兼容旧程序')
   if db.execute("SELECT 1 FROM sqlite_master WHERE name='coverage_schema'").fetchone():
    rows=db.execute('SELECT version FROM coverage_schema').fetchall()
    cap=Path(target)/'production/score-capability.json'
    if len(rows)!=1 or not set(COVERAGE_FILES)<=set(info['files']) or 'production/score-capability.json' not in info['files'] or json.loads(cap.read_text()).get('coverage_schema')!=rows[0][0]:raise ValueError('成绩表权限已启用，禁止切回不兼容旧程序')
   if db.execute("SELECT 1 FROM sqlite_master WHERE name='notification_schema'").fetchone():
    rows=db.execute('SELECT version FROM notification_schema').fetchall()
    cap=Path(target)/'production/score-capability.json'
    if len(rows)!=1 or not set(NOTIFICATION_FILES)<=set(info['files']) or 'production/score-capability.json' not in info['files'] or json.loads(cap.read_text()).get('notification_schema')!=rows[0][0]:raise ValueError('未读状态已启用，禁止切回不能处理未读状态的旧应用')
   if db.execute("SELECT 1 FROM sqlite_master WHERE name='feedback_schema'").fetchone():
    rows=db.execute('SELECT version FROM feedback_schema').fetchall()
    cap=Path(target)/'production/score-capability.json'
    if len(rows)!=1 or not set(FEEDBACK_FILES)<=set(info['files']) or 'production/score-capability.json' not in info['files'] or json.loads(cap.read_text()).get('feedback_schema')!=rows[0][0]:raise ValueError('反馈schema已启用，禁止切回不能处理反馈的旧应用')
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
