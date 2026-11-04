"""Pure fixed-snapshot loader; no HTTP, account or OCR model imports."""
import hashlib
import ipaddress
import json
from pathlib import Path
import re
from types import SimpleNamespace
from urllib.parse import urlsplit

FILES = ('cars.json', 'gauntlet_data.json', 'cars.global.json',
         'gauntlet_data.global.json', 'global-data-manifest.json')
KIND = 'racepick-mini-guest-snapshot-v1'
PREFIX = '/api/mini/v1'


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(',', ':'), allow_nan=False).encode('utf-8')


def safe_path(value):
    path = Path(value).absolute()
    if path.resolve() != path or path.is_symlink():
        raise ValueError('Paths must not contain symlinks')
    return path


def validate_origin(value):
    parsed = urlsplit(value)
    if (parsed.scheme != 'https' or parsed.username or parsed.password
            or parsed.path or parsed.query or parsed.fragment
            or not parsed.hostname or parsed.port not in (None, 443)
            or parsed.netloc != parsed.netloc.lower()
            or not re.fullmatch(r'[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?', parsed.hostname)
            or '.' not in parsed.hostname or '..' in parsed.hostname):
        raise ValueError('An explicit HTTPS DNS origin without an API path is required')
    try:
        ipaddress.ip_address(parsed.hostname)
    except ValueError:
        return value
    raise ValueError('Use a verified DNS origin, not an IP address')


class FrozenWriter:
    def __init__(self, server, records, contents):
        self.contents = dict(contents)
        self.version = digest(canonical({'kind': KIND, 'server': server,
                                         'files': records}))[:32]

    def current(self):
        return {'id': self.version}, dict(self.contents)


def load_snapshot(directory):
    directory = safe_path(directory)
    if {p.name for p in directory.iterdir()} != {*FILES, 'snapshot.json'}:
        raise ValueError('Snapshot must contain exactly five runtime files and its manifest')
    manifest = json.loads((directory/'snapshot.json').read_bytes())
    if manifest.get('kind') != KIND or set(manifest.get('files', {})) != set(FILES):
        raise ValueError('Unknown snapshot manifest')
    contents = {}
    parsed = {}
    for name in FILES:
        path = safe_path(directory/name)
        if not path.is_file() or path.stat().st_nlink != 1 or path.stat().st_size > 8*1024*1024:
            raise ValueError('Invalid snapshot file')
        raw = path.read_bytes()
        if manifest['files'][name] != {'sha256': digest(raw), 'bytes': len(raw)}:
            raise ValueError('Snapshot byte binding mismatch: '+name)
        parsed[name] = json.loads(raw.decode('utf-8'))
        if name != FILES[-1] and not isinstance(parsed[name].get(
                'cars' if name.startswith('cars') else 'tracks'), list):
            raise ValueError('Invalid snapshot data structure')
        contents[name] = raw
    global_manifest = parsed[FILES[-1]]
    meta = global_manifest.get('_meta', {})
    if meta.get('server_id') != 'global' or meta.get('schema_version') != 1:
        raise ValueError('Invalid international snapshot metadata')
    for name in FILES[2:4]:
        entry = global_manifest.get('files', {}).get(name, {})
        if (parsed[name].get('_meta') != meta
                or entry.get('sha256') != digest(contents[name])
                or entry.get('bytes') != len(contents[name])):
            raise ValueError('International snapshot files are not atomic')
    writers = {}
    for server, names in [('cn', FILES[:2]), ('global', FILES[2:])]:
        writers[server] = FrozenWriter(server,
            {n: manifest['files'][n] for n in names}, {n: contents[n] for n in names})
    return SimpleNamespace(score_versions=writers['cn'],
                           global_score_versions=writers['global']), manifest
