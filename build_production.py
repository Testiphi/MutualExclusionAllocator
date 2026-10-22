"""Build a complete delivery folder from clean code and separately pinned official JSON."""
import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
from production_release_tools import pack,read_bundle
from validate_data import validate_data

ROOT=Path(__file__).resolve().parent

def git(path,*args):return subprocess.check_output(['git','-C',str(path),*args],text=True,encoding='utf-8').strip()
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--data-source',type=Path,required=True);p.add_argument('--wheels',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 if git(ROOT,'status','--porcelain'):raise ValueError('先提交代码，发布包必须绑定干净版本')
 if git(a.data_source,'status','--porcelain','--','gauntlet_data.json','cars.json'):raise ValueError('数据JSON有未提交修改，请先核对，不能默默打包')
 data_commit=git(a.data_source,'rev-parse','HEAD')
 data_contents={n:subprocess.check_output(['git','-C',str(a.data_source),'show',data_commit+':'+n]) for n in ('gauntlet_data.json','cars.json')}
 errors,_=validate_data(json.loads(data_contents['gauntlet_data.json']),json.loads(data_contents['cars.json']))
 if errors:raise ValueError(str(errors))
 wheel_hashes={hashlib.sha256(f.read_bytes()).hexdigest() for f in a.wheels.glob('*.whl')}
 lock_hashes={line.split('--hash=sha256:')[1].strip() for line in (ROOT/'production/requirements-linux-py312.lock').read_text().splitlines() if line.strip()}
 if wheel_hashes!=lock_hashes:raise ValueError('离线依赖与锁定清单不一致')
 a.output.mkdir(parents=True,exist_ok=False)
 provenance={'code_commit':git(ROOT,'rev-parse','HEAD'),'data_commit':data_commit,'created_local':datetime.now().isoformat(timespec='seconds')}
 info=pack(ROOT,a.data_source,a.wheels,a.output/'racepick-accounts-release.zip',provenance,data_contents=data_contents);read_bundle(a.output/'racepick-accounts-release.zip')
 for name in ('deploy_production.py','production_release_tools.py','PRODUCTION_DEPLOYMENT.md','SCORE_PRODUCTION_DEPLOYMENT.md','COMMUNITY_DEPLOYMENT.md','CONTRIBUTIONS_PRODUCTION.md','FEEDBACK_PRODUCTION.md'):shutil.copyfile(ROOT/name,a.output/name)
 (a.output/'RELEASE.json').write_text(json.dumps(info,ensure_ascii=False,indent=2),encoding='utf-8')
 checks=[f'{hashlib.sha256(f.read_bytes()).hexdigest()}  {f.name}' for f in sorted(a.output.iterdir()) if f.is_file()]
 (a.output/'SHA256SUMS.txt').write_text('\n'.join(checks)+'\n',encoding='utf-8')
 print('release_id='+info['id']);print(a.output.resolve())
if __name__=='__main__':main()
