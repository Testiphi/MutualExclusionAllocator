"""Fixed-source and public GET checks only. No credentials, cookies or retries."""
import hashlib
import json
from pathlib import Path
import sys
import urllib.request
import zipfile

root = Path(__file__).resolve().parents[1]
workspace = root.parent
out = Path(sys.argv[1]).resolve()
if out.exists() or not out.is_relative_to(workspace / 'offline-evaluation'):
    raise SystemExit('Use a new offline-evaluation receipt path')
binding = json.loads((root / 'miniapp/services/account_readonly_binding.js').read_text().removeprefix('module.exports=').strip().removesuffix(';'))
docs = workspace / 'repo/docs'
manifest = json.loads((docs / 'MINI_ACCOUNT_A_READONLY_HANDOFF_SHA256_20261105.json').read_text())

def check(raw, expected):
    assert len(raw) == expected['bytes']
    assert hashlib.sha256(raw).hexdigest() == expected['sha256']

for name, entry in manifest['files'].items():
    check((docs / name).read_bytes(), entry)
handoff = json.loads((docs / 'MINI_ACCOUNT_A_READONLY_HANDOFF_20261105.json').read_text())
assert binding == dict(origin=handoff['origin'], source=handoff['source'],
                       fixed_runtime=handoff['fixed_runtime'], health=handoff['observed_public_samples']['health'])
candidate = workspace / 'offline-evaluation/mini-account-isolation-20261105-01/candidate-04.zip'
check(candidate.read_bytes(), dict(bytes=binding['source']['archive_bytes'], sha256=binding['source']['archive_sha256']))
with zipfile.ZipFile(candidate) as archive:
    assert archive.testzip() is None
    raw = archive.read('CANDIDATE.json')
    assert hashlib.sha256(raw).hexdigest() == binding['source']['candidate_manifest_sha256']
    cm = json.loads(raw)
    assert cm['source_commit'] is None
    assert cm['source_base_commit'] == binding['source']['source_base_commit']
    for name, entry in cm['files'].items():
        check(archive.read(name), entry)

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None

opener = urllib.request.build_opener(NoRedirect())
def get(path):
    with opener.open(binding['origin'] + path, timeout=30) as response:
        assert response.status == 200
        return response.read(2 * 1024 * 1024 + 1)

health = json.loads(get('/_account-test/health'))
assert health == binding['health'], 'Health/delivery changed; stop before guest/login'
files = {}
parsed = {}
for name, entry in binding['fixed_runtime']['files'].items():
    raw = get('/' + name)
    check(raw, entry)
    parsed[name] = json.loads(raw.decode('utf-8', errors='strict'))
    files[name] = dict(entry)
gm = parsed['global-data-manifest.json']
for name in ('cars.global.json', 'gauntlet_data.global.json'):
    meta = parsed[name]['_meta']
    for key in ('server_id', 'schema_version', 'dataset_version', 'catalog_payload_sha256', 'scores_payload_sha256', 'manifest_file'):
        assert meta[key] == gm['_meta'][key]
    assert meta['dataset_version'] == binding['fixed_runtime']['global_dataset']
    check_raw = binding['fixed_runtime']['files'][name]
    assert all(gm['files'][name][key] == check_raw[key] for key in ('sha256', 'bytes'))
    assert gm['files'][name]['payload_sha256'] == meta['catalog_payload_sha256' if name.startswith('cars') else 'scores_payload_sha256']
out.parent.mkdir(parents=True, exist_ok=True)
from datetime import datetime, timezone
out.write_text(json.dumps(dict(observed_at_utc=datetime.now(timezone.utc).isoformat(),
    source_commit=None, delivery_id=binding['source']['delivery_id'],
    handoff_hashes_verified=True, candidate_zip_and_all_manifest_files_verified=True,
    public_health_verified=True, public_files=files, global_trio_binding_verified=True,
    real_wechat=False, real_account_login=False, authenticated_profiles=False,
    cloud_writes=False, requests='6 HTTPS GET only; no retries'), indent=2) + '\n', encoding='utf-8')
print('PASS fixed handoff, ZIP/CANDIDATE and all manifest files; HTTPS health and five raw files; no login')
