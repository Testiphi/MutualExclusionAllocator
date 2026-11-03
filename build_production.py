"""Build a complete delivery folder from clean code and separately pinned official JSON."""
import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import io
import zipfile
from production_release_tools import pack,read_bundle
from validate_data import validate_data

ROOT=Path(__file__).resolve().parent

def git(path,*args):return subprocess.check_output(['git','-C',str(path),*args],text=True,encoding='utf-8').strip()
def load_frozen_snapshot(path,expected_sha):
 raw=Path(path).read_bytes()
 if not expected_sha or hashlib.sha256(raw).hexdigest()!=expected_sha:raise ValueError('冻结清单SHA不匹配批准来源')
 freeze=json.loads(raw)
 names={'gauntlet_data.json','cars.json','cars.global.json','gauntlet_data.global.json','global-data-manifest.json'}
 if freeze.get('schema')!='racepick.local-working-tree-data-freeze.v1' or freeze.get('frozen') is not True or set(freeze.get('runtime',{}))!=names or freeze.get('data_commit') is not None:raise ValueError('不是批准的未提交数据冻结格式')
 source=freeze['source_archive'];archive_raw=Path(source['path']).read_bytes()
 if len(archive_raw)!=source['bytes'] or hashlib.sha256(archive_raw).hexdigest()!=source['sha256']:raise ValueError('冻结ZIP来源SHA/大小不匹配')
 with zipfile.ZipFile(io.BytesIO(archive_raw)) as archive:
  members=archive.namelist()
  if len(members)!=len(set(members)) or len(members)!=source['files'] or archive.testzip() is not None:raise ValueError('冻结ZIP成员/CRC无效')
  manifest=json.loads(archive.read('FREEZE_MANIFEST.json'))
  if manifest['freeze_id']!=freeze['freeze_id'] or manifest['runtime']!=freeze['runtime'] or set(members)!=set(manifest['members'])|{'FREEZE_MANIFEST.json'}:raise ValueError('冻结内外清单不一致')
  for name,item in manifest['members'].items():
   value=archive.read(name)
   if len(value)!=item['bytes'] or hashlib.sha256(value).hexdigest()!=item['sha256']:raise ValueError('冻结载荷损坏：'+name)
  contents={name:archive.read('runtime/'+name) for name in names}
 for name,value in contents.items():
  declared=freeze['runtime'][name]
  if hashlib.sha256(value).hexdigest()!=declared['sha256'] or len(value)!=declared['bytes']:raise ValueError('运行数据不匹配冻结：'+name)
 return contents,{'data_commit':None,'data_source_kind':'approved_local_freeze','data_freeze_id':freeze['freeze_id'],
   'data_freeze_manifest_sha256':expected_sha,'data_source_archive_sha256':source['sha256'],'data_runtime':freeze['runtime'],
   'national_keys':freeze['national_keys'],'international_runtime_entries':freeze['international_runtime_entries']}

def main():
 p=argparse.ArgumentParser(description=__doc__);data=p.add_mutually_exclusive_group(required=True);data.add_argument('--data-source',type=Path);data.add_argument('--data-freeze',type=Path);p.add_argument('--freeze-sha256');p.add_argument('--publish-maintenance',action='store_true');p.add_argument('--wheels',type=Path,required=True);p.add_argument('--ocr-assets',type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 if a.publish_maintenance and not a.data_freeze:p.error('正式维护发布范围必须绑定批准的--data-freeze')
 if git(ROOT,'status','--porcelain'):raise ValueError('先提交代码，发布包必须绑定干净版本')
 data_names=('gauntlet_data.json','cars.json','cars.global.json','gauntlet_data.global.json','global-data-manifest.json')
 if a.data_freeze:
  data_contents,data_provenance=load_frozen_snapshot(a.data_freeze,a.freeze_sha256)
 else:
  if git(a.data_source,'status','--porcelain','--',*data_names):raise ValueError('双服数据JSON有未提交修改，请先核对，不能默默打包')
  data_commit=git(a.data_source,'rev-parse','HEAD')
  data_contents={n:subprocess.check_output(['git','-C',str(a.data_source),'show',data_commit+':'+n]) for n in data_names}
  data_provenance={'data_commit':data_commit,'data_source_kind':'git_commit'}
 errors,_=validate_data(json.loads(data_contents['gauntlet_data.json']),json.loads(data_contents['cars.json']))
 if errors:raise ValueError(str(errors))
 wheel_hashes={hashlib.sha256(f.read_bytes()).hexdigest() for f in a.wheels.glob('*.whl')}
 lock_hashes={line.split('--hash=sha256:')[1].strip() for line in (ROOT/'production/requirements-linux-py312.lock').read_text().splitlines() if line.strip()}
 if wheel_hashes!=lock_hashes:raise ValueError('离线依赖与锁定清单不一致')
 a.output.mkdir(parents=True,exist_ok=False)
 provenance={'code_commit':git(ROOT,'rev-parse','HEAD'),**data_provenance,'created_local':datetime.now().isoformat(timespec='seconds')}
 if a.publish_maintenance:provenance['maintenance_release']={'required':True,'mode':'explicit-offline-versioned-import','servers':['cn','global'],'entrypoint':'backend.maintenance_release','startup_import':False}
 if a.ocr_assets:provenance['ocr_assets_sha256']=hashlib.sha256((ROOT/'production/ocr-assets.json').read_bytes()).hexdigest()
 info=pack(ROOT,a.data_source or ROOT,a.wheels,a.output/'racepick-accounts-release.zip',provenance,data_contents=data_contents,ocr_assets=a.ocr_assets);read_bundle(a.output/'racepick-accounts-release.zip')
 for name in ('deploy_production.py','production_release_tools.py','PRODUCTION_DEPLOYMENT.md','SCORE_PRODUCTION_DEPLOYMENT.md','COMMUNITY_DEPLOYMENT.md','CONTRIBUTIONS_PRODUCTION.md','FEEDBACK_PRODUCTION.md','GARAGE_DEPLOYMENT.md','LOCAL_INTERNATIONAL.md','INTERNATIONAL_DEPLOYMENT.md','SERVER_SWITCH_FIX.md','NOTIFICATIONS_LOCAL.md','USAGE_LOCAL.md','UNREAD_USAGE_DEPLOYMENT.md','COVERAGE_DEPLOYMENT.md','GLOBAL_SUBMISSIONS_DEPLOYMENT.md'):shutil.copyfile(ROOT/('docs/'+name if name.endswith('.md') else name),a.output/name)
 (a.output/'RELEASE.json').write_text(json.dumps(info,ensure_ascii=False,indent=2),encoding='utf-8')
 if a.ocr_assets:shutil.copyfile(ROOT/'docs/MAP_OCR_DEPLOYMENT.md',a.output/'MAP_OCR_DEPLOYMENT.md')
 checks=[f'{hashlib.sha256(f.read_bytes()).hexdigest()}  {f.name}' for f in sorted(a.output.iterdir()) if f.is_file()]
 (a.output/'SHA256SUMS.txt').write_text('\n'.join(checks)+'\n',encoding='utf-8')
 print('release_id='+info['id']);print(a.output.resolve())
if __name__=='__main__':main()
