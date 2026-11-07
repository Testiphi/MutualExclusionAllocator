"""Lock separate CPython3.12/Linux/x86_64 environments from reviewed wheels."""
import argparse
from email.parser import BytesParser
import hashlib
import json
from pathlib import Path
import zipfile
from packaging.markers import default_environment
from packaging.requirements import Requirement
from packaging.utils import canonicalize_name

ROOT=Path(__file__).resolve().parents[1]
ENV={**default_environment(),'python_version':'3.12','python_full_version':'3.12.16',
     'sys_platform':'linux','os_name':'posix','platform_system':'Linux',
     'platform_machine':'x86_64','extra':''}


def inventory(folder):
    result={}
    for path in sorted(Path(folder).glob('*.whl')):
        raw=path.read_bytes()
        with zipfile.ZipFile(path) as z:
            message=BytesParser().parsebytes(z.read(next(n for n in z.namelist() if n.endswith('.dist-info/METADATA'))))
        result[canonicalize_name(message['Name'])]={'path':str(path.resolve()),'name':path.name,
            'version':message['Version'],'sha256':hashlib.sha256(raw).hexdigest(),
            'requires':message.get_all('Requires-Dist',[])}
    return result


def closure(available,requirements):
    selected={};pending=[Requirement(r) for r in requirements]
    while pending:
        r=pending.pop();name=canonicalize_name(r.name)
        if r.marker is not None and not r.marker.evaluate(ENV):continue
        if name not in available or available[name]['version'] not in r.specifier:
            raise ValueError('Missing/incompatible offline wheel: '+str(r))
        if name in selected:continue
        selected[name]=available[name]
        pending.extend(Requirement(d) for d in available[name]['requires'])
    return selected


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--web-wheels',required=True,type=Path);p.add_argument('--sdk-wheels',required=True,type=Path)
    p.add_argument('--test-wheels',required=True,type=Path);p.add_argument('--receipt',required=True,type=Path)
    args=p.parse_args();web=inventory(args.web_wheels);sdk=inventory(args.sdk_wheels);tests=inventory(args.test_wheels)
    groups={'guest':closure(web,['fastapi==0.138.1','uvicorn==0.49.0','pillow==12.2.0']),
        'bridge':closure(web|sdk,['alibabacloud-green20220302==3.6.9','oss2==2.19.1','pillow==12.2.0']),
        'validation':closure(web|sdk|tests,['alibabacloud-green20220302==3.6.9','oss2==2.19.1',
            'fastapi==0.138.1','uvicorn==0.49.0','argon2-cffi==25.1.0','pillow==12.2.0',
            'httpx==0.28.1','packaging==26.3','setuptools==80.9.0','wheel==0.45.1'])}
    groups['web']=web
    locks={'guest':'requirements-mini-ocr-guest.lock','bridge':'requirements-ocr-bridge.lock',
           'validation':'requirements-mini-ocr-validation.lock'}
    for group,name in locks.items():
        raw=''.join(n+'=='+r['version']+' --hash=sha256:'+r['sha256']+'\n' for n,r in sorted(groups[group].items()))
        (ROOT/'production'/name).write_text(raw,encoding='utf-8',newline='\n')
    args.receipt.write_text(json.dumps({'target':ENV,'groups':groups},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({name:len(items) for name,items in groups.items()}))


if __name__=='__main__':main()
