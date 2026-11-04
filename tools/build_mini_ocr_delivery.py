"""Build a sealed local source-snapshot delivery; never invent a Git commit."""
import argparse
import ast
import hashlib
import io
import json
from pathlib import Path
import shutil
import subprocess
import zipfile
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from production_release_tools import pack,read_bundle,APP_FILES,OCR_CODE_FILES,OCR_ASSET_FILES

GUEST=('__init__','mini_auth','mini_api','mini_result','mini_snapshot','mini_guest_service',
       'mini_ocr_guest_service','mini_bridge_port','ocr_queue_bridge','map_recognition','image_safety_aliyun')
BRIDGE=('__init__','mini_auth','mini_result','mini_snapshot','ocr_queue_bridge','map_recognition','map_ocr_production',
        'image_safety_aliyun','image_safety_sdk')
TESTS=('test_image_safety_aliyun','test_image_safety_sdk','test_ocr_queue_bridge','test_mini_ocr_guest_service',
       'test_mini_guest_service','test_mini_api','test_mini_production','test_map_recognition','test_map_ocr_production')
CONFIGS=('aliyun-baseline.config.example.json','aliyun-baseline.ram-policy.example.json',
         'ocr-queue-bridge.config.example.json','mini-ocr.config.example.json')
LOCKS={'web':'requirements-linux-py312.lock','guest':'requirements-mini-ocr-guest.lock',
       'bridge':'requirements-ocr-bridge.lock','validation':'requirements-mini-ocr-validation.lock'}


def sha(raw):return hashlib.sha256(raw).hexdigest()
def encode(value):return (json.dumps(value,sort_keys=True,ensure_ascii=False,indent=2)+'\n').encode()
def canonical(value):return json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()


def test_modules():
    selected=set(TESTS);pending=list(selected)
    while pending:
        module=pending.pop()
        tree=ast.parse((ROOT/'backend'/(module+'.py')).read_text(encoding='utf-8'))
        for node in ast.walk(tree):
            names=[]
            if isinstance(node,ast.ImportFrom):
                if node.module=='backend':names=[a.name for a in node.names]
                elif node.module and node.module.startswith('backend.test_'):names=[node.module.split('.')[1]]
            elif isinstance(node,ast.Import):names=[a.name.split('.')[1] for a in node.names if a.name.startswith('backend.test_')]
            for name in names:
                if name.startswith('test_') and name not in selected:selected.add(name);pending.append(name)
    return selected


def build(args):
    output=args.output.resolve()
    if output.exists() or output.with_suffix('.zip').exists():raise ValueError('Use a new delivery path')
    original_raw=args.website.read_bytes()
    if sha(original_raw)!='1159c9c0abd72caa7ccdb0b127ee4738a822d4121626eeb62cb5f10637b1f07d':
        raise ValueError('Use the approved a933 seed source')
    original,old=read_bundle(args.website)
    if old['id']!='a933c9b746c2e276a9b68d14':raise ValueError('Wrong seed release')
    names=('cars.json','gauntlet_data.json','cars.global.json','gauntlet_data.global.json','global-data-manifest.json')
    seeds={n:original[n] for n in names}
    provenance={k:v for k,v in old['provenance'].items() if k.startswith('data_') or k in ('national_keys','international_runtime_entries')}
    if provenance.get('data_freeze_id')!='b57d97a8f4e484be69238ab0' or provenance.get('data_commit') is not None:
        raise ValueError('Wrong frozen data source')
    payload={};source={}
    def add(name,value):payload[name]=value
    def source_file(name):
        raw=(ROOT/name).read_bytes();source[name]={'sha256':sha(raw),'bytes':len(raw)}
        payload['source/'+name]=raw
        return raw
    for group,modules in [('guest',GUEST),('bridge',BRIDGE)]:
        for module in modules:add(group+'/backend/'+module+'.py',source_file('backend/'+module+'.py'))
    for name in CONFIGS:
        group='guest' if name=='mini-ocr.config.example.json' else 'bridge'
        add(group+'/production/'+name,source_file('production/'+name))
    snapshot=json.loads(args.snapshot_manifest.read_bytes())
    for n,raw in seeds.items():
        if snapshot['files'][n]!={'sha256':sha(raw),'bytes':len(raw)}:raise ValueError('Snapshot source drift')
        add('snapshot/'+n,raw)
    add('snapshot/snapshot.json',args.snapshot_manifest.read_bytes())
    versions={}
    for server,group in [('cn',names[:2]),('global',names[2:])]:
        versions[server]=sha(canonical({'kind':snapshot['kind'],'server':server,
            'files':{n:snapshot['files'][n] for n in group}}))[:32]
    maps=[{'big':r['大地图'],'small':r['小地图']} for r in json.loads(seeds['gauntlet_data.json'])['tracks']]
    expected={'versions':versions,'files':snapshot['files'],'dataset':json.loads(seeds['global-data-manifest.json'])['_meta']['dataset_version'],
        'accounts_enabled':False,'B_E_enabled':False,'is_current_public_state':False}
    add('DEFAULT_EXPECTATIONS.json',encode(expected|{'image_policy':'disabled',
        'cn_map_recognition':False,'cn_catalog_version':None,'global_map_recognition':False,'global_catalog_version':None}))
    add('OCR_EXPECTATIONS.json',encode(expected|{'when':'only after separately authorized enablement and actual ready checks',
        'image_policy':'aliyun_baseline','cn_map_recognition':True,
        'cn_catalog_version':sha((versions['cn']+':').encode()+seeds['gauntlet_data.json']),
        'maps':maps,'maps_sha256':sha(json.dumps(maps,ensure_ascii=False,sort_keys=True).encode()),
        'content_safety':'required_approval','global_map_recognition':False,'global_catalog_version':None}))
    dependency=json.loads(args.dependencies.read_bytes())
    for group,name in LOCKS.items():
        source_file('production/'+name)
        items=dependency['groups'][group]
        lock=''.join(n+'=='+r['version']+' --hash=sha256:'+r['sha256']+'\n' for n,r in sorted(items.items()))
        add('locks/'+group+'.lock',lock.encode())
    for group,items in dependency['groups'].items():
        for record in items.values():
            raw=Path(record['path']).read_bytes()
            if sha(raw)!=record['sha256']:raise ValueError('Wheel source mismatch')
            add('wheels/'+record['name'],raw)
    # Include complete reviewable implementation source and synthetic-only validation tests.
    for n in set(APP_FILES)|set(OCR_CODE_FILES):
        path=('docs/'+n if n.endswith('.md') or n=='MINI_FEATURES_OPENAPI_20261103.json' else n)
        raw=seeds[n] if n in seeds else source_file(path)
        add('source/'+path,raw)
    for module in set(GUEST)|set(BRIDGE)|test_modules()|{'image_safety_local'}:
        add('source/backend/'+module+'.py',source_file('backend/'+module+'.py'))
    source_file('tests/__init__.py');source_file('tests/test_mini_ocr_release.py')
    for n,raw in seeds.items():add('source/'+n,raw)
    for name in ('ALIYUN_OCR_RELEASE_PREPARATION_20261104.md','MINI_API_CONTRACT_20261102.md'):
        add('docs/'+name,source_file('docs/'+name))
    for name in ('verify_mini_ocr_delivery.py','lock_mini_ocr_dependencies.py','build_mini_ocr_delivery.py','validate_mini_ocr_linux.py','build_crcmod_pure_wheel.py'):
        add('tools/'+name,source_file('tools/'+name))
    inputs=args.dependencies.parent
    add('build-inputs/crcmod-pure-build.json',(inputs/'crcmod-pure-build.json').read_bytes())
    add('build-inputs/crcmod-1.7.tar.gz',(inputs/'sdists/crcmod-1.7.tar.gz').read_bytes())
    for file in (ROOT/'production/mini-ocr').rglob('*'):
        if file.is_file():add('templates/'+file.relative_to(ROOT/'production/mini-ocr').as_posix(),source_file(file.relative_to(ROOT).as_posix()))
    add('VALIDATION.json',args.validation.read_bytes())
    add('DEPENDENCIES.json',encode({'target':'Ubuntu24.04 CPython3.12 x86_64',
        'groups':{g:{n:{k:v for k,v in r.items() if k!='path'} for n,r in rows.items()} for g,rows in dependency['groups'].items()}}))
    add('DATA_SOURCE.json',encode(provenance|{'use':'immutable mini-test snapshot and package seeds only; never import existing score-state'}))
    add('README_FIRST.md',source_file('docs/ALIYUN_OCR_README_FIRST_20261104.md'))
    source_file('production_release_tools.py');source_file('deploy_production.py')
    source_tree_sha=sha(canonical(source))
    source_info={'kind':'sealed_uncommitted_source_snapshot','source_commit':None,
        'base_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        'tree_sha256':source_tree_sha,'files':source,'git_operations_authorized':False}
    add('SOURCE.json',encode(source_info))
    output.mkdir(parents=True)
    build_dir=output.parent/(output.name+'-build-inputs');build_dir.mkdir(exist_ok=False)
    assets=build_dir/'assets';assets.mkdir();wheels=build_dir/'wheels';wheels.mkdir()
    for n in OCR_ASSET_FILES:
        p=assets/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(original[n])
    for record in dependency['groups']['web'].values():shutil.copyfile(record['path'],wheels/record['name'])
    website_dir=output/'website';website_dir.mkdir()
    # Preserve the accepted website/UI. Apply ONLY the shared-code compatibility overlay.
    code=build_dir/'website-code';code.mkdir()
    for name,value in original.items():
        if name.startswith('wheels/'):continue
        path=code/('docs/'+name if name.endswith('.md') or name=='MINI_FEATURES_OPENAPI_20261103.json' else name)
        path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(value)
    overlay=('backend/map_recognition.py','backend/mini_api.py','backend/mini_auth.py',
             'backend/mini_result.py','production_release_tools.py','production/score-capability.json')
    for name in overlay:
        path=code/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes((ROOT/name).read_bytes())
    site_provenance=provenance|{'code_commit':None,'source_kind':'sealed_uncommitted_source_snapshot',
        'source_base_commit':source_info['base_commit'],'source_tree_sha256':source_tree_sha,
        'website_base_release':old['id'],'website_base_code_commit':old['provenance']['code_commit'],
        'website_overlay':{n:sha((ROOT/n).read_bytes()) for n in overlay},
        'maintenance_release':{'required':False,'mode':'existing-independent-score-state-preserved'}}
    website_info=pack(code,ROOT,wheels,website_dir/'racepick-accounts-release.zip',site_provenance,data_contents=seeds,ocr_assets=assets)
    shipped,_=read_bundle(website_dir/'racepick-accounts-release.zip')
    changed={n for n in set(shipped)|set(original) if shipped.get(n)!=original.get(n)}
    if not changed<=set(overlay):raise ValueError('Unexpected website scope change: '+repr(changed))
    add('website/CODE_DIFF.json',encode({'base_release':old['id'],'changed_files':sorted(changed),
        'ui_assets_unchanged':True,'maintenance_data_imported':False,'allowed_overlay':list(overlay)}))
    add('website/racepick-accounts-release.zip',(website_dir/'racepick-accounts-release.zip').read_bytes())
    add('website/RELEASE.json',encode(website_info))
    for name in ('production_release_tools.py','deploy_production.py'):
        add('website/'+name,(ROOT/name).read_bytes())
    release={'schema':'racepick.mini-ocr-complete-local-candidate.v1','target':'ubuntu24.04-x86_64-python3.12',
        'source':source_info|{'files':None},'freeze_id':provenance['data_freeze_id'],
        'website_release_id':website_info['id'],'guest_image_policy':'disabled','bridge_enabled':False,
        'accounts_and_B_E_enabled':False,'production_operations':False,
        'files':{n:{'sha256':sha(v),'bytes':len(v)} for n,v in sorted(payload.items())}}
    release['id']=sha(canonical(release))[:24];add('RELEASE.json',encode(release))
    add('SHA256SUMS.txt',''.join(sha(v)+'  '+n+'\n' for n,v in sorted(payload.items())).encode())
    for name,value in payload.items():
        p=output/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(value)
    archive=output.with_suffix('.zip')
    with zipfile.ZipFile(archive,'x',zipfile.ZIP_DEFLATED) as z:
        for n,v in sorted(payload.items()):z.writestr(n,v)
    archive.with_suffix('.zip.sha256').write_text(sha(archive.read_bytes())+'  '+archive.name+'\n',encoding='utf-8')
    print(json.dumps({'release_id':release['id'],'website_release_id':website_info['id'],
        'source_sha256':source_tree_sha,'archive':str(archive),'bytes':archive.stat().st_size,'sha256':sha(archive.read_bytes())},ensure_ascii=False))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('website','snapshot-manifest','dependencies','validation','output'):p.add_argument('--'+name,required=True,type=Path)
    build(p.parse_args())
