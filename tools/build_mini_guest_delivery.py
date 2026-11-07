"""Build a NEW isolated guest delivery from committed code and a verified website ZIP."""
import argparse
from email.parser import BytesParser
import hashlib
import io
import json
from pathlib import Path
import subprocess
import zipfile

from packaging.markers import default_environment
from packaging.requirements import Requirement
from packaging.utils import canonicalize_name

ROOT = Path(__file__).resolve().parents[1]
FILES = ('cars.json', 'gauntlet_data.json', 'cars.global.json',
         'gauntlet_data.global.json', 'global-data-manifest.json')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def encode(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2)+'\n').encode('utf-8')


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--website-bundle', type=Path, required=True)
    p.add_argument('--website-sha256', required=True)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    raw = args.website_bundle.read_bytes()
    if sha(raw) != args.website_sha256:
        raise ValueError('Website archive SHA mismatch')
    from production_release_tools import read_bundle
    website, release = read_bundle(args.website_bundle)
    provenance = release['provenance']
    if (release['id'] != 'a933c9b746c2e276a9b68d14'
            or provenance['data_freeze_id'] != 'b57d97a8f4e484be69238ab0'
            or provenance['data_freeze_manifest_sha256'] != '940f8660585c495a780390b709dfd52e80f7610f57e0179c5da937c53c4e4282'
            or provenance['data_commit'] is not None):
        raise ValueError('Use the approved website/frozen data source')
    payload = {}
    commit = git('rev-parse', 'HEAD').decode().strip()
    names = ['backend/__init__.py', 'backend/mini_auth.py', 'backend/mini_api.py',
             'backend/mini_guest_service.py', 'docs/MINI_GUEST_STAGE1_20261103.md']
    names += git('ls-tree', '-r', '--name-only', commit, 'production/mini-guest').decode().splitlines()
    for name in names:
        value = git('show', commit+':'+name)
        if (ROOT/name).read_bytes().replace(b'\r\n', b'\n') != value.replace(b'\r\n', b'\n'):
            raise ValueError('Uncommitted source changes: '+name)
        payload[name] = value
    records = {}
    for name in FILES:
        value = website[name]
        if sha(value) != provenance['data_runtime'][name]['sha256']:
            raise ValueError('Frozen runtime SHA mismatch')
        records[name] = {'sha256': sha(value), 'bytes': len(value)}
        payload['snapshot/'+name] = value
    snapshot = {'kind': 'racepick-mini-guest-snapshot-v1', 'files': records,
                'freeze_id': provenance['data_freeze_id'],
                'freeze_manifest_sha256': provenance['data_freeze_manifest_sha256'],
                'source_website_release': release['id'],
                'source_data_commit': None,
                'identity_basis': 'isolated immutable test snapshot; not production score pointers'}
    payload['snapshot/snapshot.json'] = encode(snapshot)

    # Resolve the Linux3.12 *minimal* dependency closure using the already verified wheels.
    wheels = {}
    metadata = {}
    for name, value in website.items():
        if name.startswith('wheels/') and name.endswith('.whl'):
            with zipfile.ZipFile(io.BytesIO(value)) as wheel:
                message = BytesParser().parsebytes(wheel.read(next(
                    n for n in wheel.namelist() if n.endswith('.dist-info/METADATA'))))
            key = canonicalize_name(message['Name'])
            wheels[key] = (name, value)
            metadata[key] = message
    environment = {**default_environment(), 'python_version': '3.12',
        'python_full_version': '3.12.3', 'sys_platform': 'linux', 'os_name': 'posix',
        'platform_system': 'Linux', 'platform_machine': 'x86_64', 'extra': ''}
    selected = set()
    pending = [Requirement('fastapi'), Requirement('uvicorn')]
    while pending:
        requirement = pending.pop()
        key = canonicalize_name(requirement.name)
        if key not in metadata or metadata[key]['Version'] not in requirement.specifier:
            raise ValueError('Missing/incompatible offline dependency: '+key)
        if key in selected:
            continue
        selected.add(key)
        for line in metadata[key].get_all('Requires-Dist', []):
            dependency = Requirement(line)
            if dependency.marker is None or dependency.marker.evaluate(environment):
                pending.append(dependency)
    lock = []
    for key in sorted(selected):
        name, value = wheels[key]
        payload[name] = value
        lock.append(key+'=='+metadata[key]['Version']+' --hash=sha256:'+sha(value))
    payload['production/mini-guest/requirements.lock'] = ('\n'.join(lock)+'\n').encode()
    payload['verify_delivery.py'] = b'''from pathlib import Path
import hashlib,json
root=Path(__file__).resolve().parent
m=json.loads((root/'DELIVERY.json').read_bytes())
for name,record in m['files'].items():
    p=(root/name).resolve()
    if not p.is_relative_to(root) or not p.is_file():raise ValueError('Invalid path')
    raw=p.read_bytes()
    if len(raw)!=record['bytes'] or hashlib.sha256(raw).hexdigest()!=record['sha256']:raise ValueError('SHA mismatch: '+name)
for line in (root/'SHA256SUMS.txt').read_text().splitlines():
    expected,name=line.split('  ',1)
    p=(root/name).resolve()
    if not p.is_relative_to(root) or hashlib.sha256(p.read_bytes()).hexdigest()!=expected:raise ValueError('Delivery SHA mismatch')
print(json.dumps({'all_checks_passed':True,'delivery_id':m['id'],'code_commit':m['code_commit'],'files':len(m['files']),'production_operations':False}))
'''
    payload['README_FIRST.md'] = '''# Stage-one mini guest isolation delivery

Preparation only: no DNS/certificate/Nginx/service/account creation is authorized by this package.
Verify SHA256SUMS.txt and run python3 -B verify_delivery.py before any later authorized staging.
Read docs/MINI_GUEST_STAGE1_20261103.md. Candidate host and paths are proposals, not live evidence.
Only POST session and GET snapshot; images disabled, no accounts/B-E/OCR worker.
Real App ID/AppSecret/session state/token keys are not present. Never copy production or old fixture databases.
Install-runtime.sh is only for a NEW isolated release directory and does not start or provision anything.
Server changes remain one approved step at a time. Existing website, OCR and backup scheduler remain unchanged.
'''.encode()
    identity = sha(encode({'code': commit, 'snapshot': snapshot,
                          'files': {n: sha(v) for n, v in payload.items()}}))[:24]
    delivery = {'schema': 'racepick.mini-guest-delivery.v1', 'id': identity,
        'code_commit': commit, 'website_release': release['id'],
        'website_code_commit': provenance['code_commit'],
        'website_bundle_sha256': args.website_sha256,
        'freeze_id': provenance['data_freeze_id'],
        'freeze_manifest_sha256': provenance['data_freeze_manifest_sha256'],
        'historical_website_data_commit': None,
        'candidate_origin': 'https://mini-test.racepick.cn',
        'candidate_origin_live_verified': False,
        'image_policy': 'disabled', 'accounts_enabled': False,
        'business_bridge_enabled': False, 'ocr_worker_started': False,
        'real_wechat_exchange_verified': False, 'offline_wheels': len(selected),
        'files': {n: {'sha256': sha(v), 'bytes': len(v)} for n, v in payload.items()}}
    payload['DELIVERY.json'] = encode(delivery)
    payload['SHA256SUMS.txt'] = ''.join(sha(v)+'  '+n+'\n' for n, v in sorted(payload.items())).encode()
    output = args.output.absolute()
    if output.exists() or output.with_suffix('.zip').exists():
        raise ValueError('Use a new output directory; preserve previous evidence')
    output.mkdir(parents=True)
    for name, value in payload.items():
        path = output/name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(value)
    archive = output.with_suffix('.zip')
    with zipfile.ZipFile(archive, 'x', zipfile.ZIP_DEFLATED) as z:
        for name, value in sorted(payload.items()):
            z.writestr(name, value)
    archive.with_suffix('.zip.sha256').write_text(sha(archive.read_bytes())+'  '+archive.name+'\n', encoding='utf-8')
    print(json.dumps({'delivery_id': identity, 'code_commit': commit,
        'offline_wheels': len(selected), 'archive': str(archive),
        'bytes': archive.stat().st_size, 'sha256': sha(archive.read_bytes()),
        'production_operations': False}, ensure_ascii=False))


if __name__ == '__main__':
    import sys
    sys.path.insert(0, str(ROOT))
    main()
