"""Read-only strict inventory, SHA and nested website-manifest verification."""
import hashlib
import json
from pathlib import Path
import sys
import zipfile


def canonical(value):return json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()
def sha(raw):return hashlib.sha256(raw).hexdigest()


def verify(root):
    root=Path(root).resolve()
    release=json.loads((root/'RELEASE.json').read_bytes())
    identity=release['id'];declared={k:v for k,v in release.items() if k!='id'}
    if sha(canonical(declared))[:24]!=identity:raise ValueError('Release identity mismatch')
    expected=set(release['files'])|{'RELEASE.json','SHA256SUMS.txt'}
    actual={p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()}
    if actual!=expected:raise ValueError('Unexpected/missing delivery files: '+repr(actual^expected))
    for name,record in release['files'].items():
        path=root/name
        if path.is_symlink() or not path.resolve().is_relative_to(root):raise ValueError('Unsafe member')
        raw=path.read_bytes()
        if record!={'sha256':sha(raw),'bytes':len(raw)}:raise ValueError('File mismatch: '+name)
    lines=(root/'SHA256SUMS.txt').read_text().splitlines();seen=set()
    for line in lines:
        digest,name=line.split('  ',1)
        if name not in expected or name in seen or name=='SHA256SUMS.txt':raise ValueError('Invalid checksum inventory')
        seen.add(name)
        if sha((root/name).read_bytes())!=digest:raise ValueError('Checksum mismatch: '+name)
    if seen!=expected-{'SHA256SUMS.txt'}:raise ValueError('Incomplete checksum inventory')
    sys.path.insert(0,str(root/'website'))
    from production_release_tools import read_bundle
    contents,website=read_bundle(root/'website/racepick-accounts-release.zip')
    if website['id']!=release['website_release_id']:raise ValueError('Nested website identity mismatch')
    source=json.loads((root/'SOURCE.json').read_bytes())
    if sha(canonical(source['files']))!=source['tree_sha256'] or source['tree_sha256']!=release['source']['tree_sha256']:
        raise ValueError('Source tree binding mismatch')
    for name,record in source['files'].items():
        value=(root/'source'/name).read_bytes()
        if record!={'sha256':sha(value),'bytes':len(value)}:raise ValueError('Source snapshot mismatch: '+name)
    snapshot=json.loads((root/'snapshot/snapshot.json').read_bytes())
    data=json.loads((root/'DATA_SOURCE.json').read_bytes())
    for name,record in snapshot['files'].items():
        value=(root/'snapshot'/name).read_bytes()
        if record!={'sha256':sha(value),'bytes':len(value)} or contents[name]!=value:
            raise ValueError('Frozen snapshot/website seed mismatch')
        if data['data_runtime'][name]['sha256']!=sha(value):raise ValueError('Frozen source mismatch')
    dependencies=json.loads((root/'DEPENDENCIES.json').read_bytes())
    for group,items in dependencies['groups'].items():
        expected_lock=''.join(n+'=='+r['version']+' --hash=sha256:'+r['sha256']+'\n' for n,r in sorted(items.items()))
        if (root/'locks'/(group+'.lock')).read_text()!=expected_lock:raise ValueError('Lock mismatch: '+group)
        for record in items.values():
            if sha((root/'wheels'/record['name']).read_bytes())!=record['sha256']:raise ValueError('Locked wheel mismatch')
    if json.loads((root/'guest/production/mini-ocr.config.example.json').read_bytes())['image_policy']!='disabled':
        raise ValueError('Guest image policy must remain disabled in delivery')
    if json.loads((root/'bridge/production/ocr-queue-bridge.config.example.json').read_bytes())['enabled'] is not False:
        raise ValueError('Bridge must remain disabled in delivery')
    return {'verified':True,'release_id':identity,'files':len(expected),
            'website_release_id':website['id'],'production_operations':False}


if __name__=='__main__':
    print(json.dumps(verify(Path(__file__).resolve().parent.parent),ensure_ascii=False))
