"""Build a new, source-bound offline A account candidate; never deploy or copy state."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import zipfile

from backend.mini_snapshot import load_snapshot, FILES
from backend.mini_account_service import ASSETS

RUNTIME={'annotated-doc','annotated-types','anyio','click','fastapi','h11','idna','pillow','pydantic',
         'pydantic-core','starlette','typing-extensions','typing-inspection','uvicorn',
         'argon2-cffi','argon2-cffi-bindings','cffi','pycparser'}
VALIDATION={'httpx','httpcore','certifi'}
NEW_BACKEND={'mini_account_boundary.py','mini_account_isolation.py','mini_account_service.py'}
TOP={'index.html','data_tools.py','apply_changes.py','format_json.py','validate_data.py',*(ASSETS-set(FILES))}


def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
def record(path):return {'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'bytes':path.stat().st_size}
def normalized(value):return re.sub(r'[-_.]+','-',value).lower()


def build(source,output,snapshot_dir,binding,wheels):
    source=Path(source).resolve();output=Path(output).resolve()
    snapshot_dir=Path(snapshot_dir).resolve();binding=Path(binding).resolve();wheels=Path(wheels).resolve()
    if output.exists() or output.resolve()!=output or output.is_relative_to(source) or source.is_relative_to(output):
        raise ValueError('Candidate must be a new independent directory')
    frozen,manifest=load_snapshot(snapshot_dir)
    binding_data=json.loads(Path(binding).read_bytes())
    if manifest['files']!=binding_data['files'] or binding_data['snapshot_versions']!={'cn':frozen.score_versions.version,'global':frozen.global_score_versions.version}:
        raise ValueError('Fixed snapshot/binding mismatch')
    output.parent.mkdir(parents=True,exist_ok=True)
    output.mkdir(mode=0o700)
    def copy(src,name):
        target=output/name;target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(src,target)
    tracked=subprocess.check_output(['git','-C',str(source),'ls-files','backend/*.py'],text=True).splitlines()
    names={name for name in tracked if not Path(name).name.startswith('test_')}
    names|={'backend/'+name for name in NEW_BACKEND}
    names|=TOP|{'tools/build_global_data.py','tools/validate_mini_account_delivery.py'}
    for name in sorted(names):
        copy(source/name,name)
    for name in (*FILES,'snapshot.json'):copy(Path(snapshot_dir)/name,'snapshot/'+name)
    copy(binding,'docs/FIXED_SNAPSHOT_BINDING.json')
    for path in sorted((source/'production/mini-account').iterdir()):
        if path.is_file():copy(path,'templates/'+path.name)
    copy(source/'docs/MINI_ACCOUNT_LOCAL_CANDIDATE_20261105.md','docs/README.md')
    locks={}
    for filename in ('requirements-linux-py312.lock','requirements-mini-ocr-validation.lock'):
        for line in (source/'production'/filename).read_text('utf-8').splitlines():
            match=re.fullmatch(r'([a-zA-Z0-9_.-]+)==([^ ]+) --hash=sha256:([a-f0-9]{64})',line)
            if match:
                key=normalized(match[1])
                if key not in locks:locks[key]=(line,match[2],match[3])
    for selected,filename in ((RUNTIME,'runtime.lock'),(RUNTIME|VALIDATION,'validation.lock')):
        (output/filename).write_text('\n'.join(locks[name][0] for name in sorted(selected))+'\n',encoding='utf-8')
    for name in sorted(RUNTIME|VALIDATION):
        _,version,sha=locks[name]
        candidates=[p for p in Path(wheels).glob('*.whl') if normalized(p.name.split('-')[0])==name and p.name.split('-')[1]==version]
        candidates=[p for p in candidates if record(p)['sha256']==sha]
        if len(candidates)!=1:raise ValueError('Missing or ambiguous hash-bound wheel: '+name)
        copy(candidates[0],'wheels/'+candidates[0].name)
    files={p.relative_to(output).as_posix():record(p) for p in sorted(output.rglob('*')) if p.is_file()}
    base=subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()
    core={'kind':'racepick-mini-account-candidate-v1','source_commit':None,'source_base_commit':base,
          'defaults':{'enabled':False,'cloud_writes':False},'files':files,
          'snapshot_versions':binding_data['snapshot_versions'],'runtime':'Linux x86_64 CPython 3.12',
          'production_deployed':False,'state_or_credentials_included':False}
    declaration={**core,'delivery_id':hashlib.sha256(canonical(core)).hexdigest()[:24]}
    (output/'CANDIDATE.json').write_text(json.dumps(declaration,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    archive=output.with_suffix('.zip')
    if archive.exists():raise ValueError('Archive already exists; retain previous candidate')
    with zipfile.ZipFile(archive,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as package:
        for path in sorted(output.rglob('*')):
            if path.is_file():package.write(path,path.relative_to(output).as_posix())
    with zipfile.ZipFile(archive) as package:
        if package.testzip() is not None:raise ValueError('Candidate archive CRC failed')
    return {'delivery_id':declaration['delivery_id'],'source_commit':None,'source_base_commit':base,
            'candidate_dir':str(output),'zip':str(archive),**record(archive),'files':len(files)+1,
            'wheel_count':len(RUNTIME|VALIDATION),'deployed':False}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--snapshot-dir',type=Path,required=True);p.add_argument('--binding',type=Path,required=True)
    p.add_argument('--wheels',type=Path,required=True);args=p.parse_args()
    print(json.dumps(build(args.source,args.output,args.snapshot_dir,args.binding,args.wheels),ensure_ascii=False))
