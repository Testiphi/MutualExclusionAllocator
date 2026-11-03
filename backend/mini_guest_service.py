"""Isolated stage-one guest gateway: no website DB, account bridge or OCR imports."""
import argparse
import hashlib
import ipaddress
import json
from pathlib import Path
import re
from types import SimpleNamespace
from urllib.parse import urlsplit

from backend.mini_api import MiniGateway, error_response
from backend.mini_auth import MiniError, load_config

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


class GuestOnlyGateway:
    """An outer allowlist prevents accidental enablement of later protocol phases."""
    def __init__(self, config, source, origin):
        if (config.get('fixture') is not False or config.get('image_policy') != 'disabled'
                or config.get('account_store') is not None
                or config.get('mirror_fixture_writes')):
            raise ValueError('Stage one requires real verifier, images disabled and no accounts')
        self.gateway = MiniGateway(self.unavailable, config=config, source=source,
                                   service=None, origin=validate_origin(origin), production=True)

    @staticmethod
    async def unavailable(scope, receive, send):
        response = error_response(MiniError(404, 'NATIVE_DISABLED',
                                  'This endpoint is not enabled in stage one'))
        response.headers.update({'Cache-Control': 'no-store',
                                 'X-Content-Type-Options': 'nosniff',
                                 'Referrer-Policy': 'no-referrer'})
        return await response(scope, receive, send)

    async def __call__(self, scope, receive, send):
        if scope['type'] == 'lifespan':
            while True:
                message = await receive()
                if message['type'] == 'lifespan.startup':
                    await send({'type': 'lifespan.startup.complete'})
                elif message['type'] == 'lifespan.shutdown':
                    await send({'type': 'lifespan.shutdown.complete'})
                    return
        if scope['type'] == 'websocket':
            return await send({'type': 'websocket.close', 'code': 1008})
        if (scope['type'] == 'http' and scope['method'] == 'OPTIONS'
                and scope['path'] in (PREFIX+'/session', PREFIX+'/snapshot')):
            return await self.gateway(scope, receive, send)
        allowed = {('POST', PREFIX+'/session'), ('GET', PREFIX+'/snapshot')}
        if scope['type'] != 'http' or (scope['method'], scope['path']) not in allowed:
            return await self.unavailable(scope, receive, send)
        return await self.gateway(scope, receive, send)


def make_app(snapshot_dir, mini_config, origin):
    source, manifest = load_snapshot(snapshot_dir)
    path = safe_path(mini_config)
    # Reject later phases BEFORE load_config could open any optional account state.
    declaration = json.loads(path.read_bytes())
    if (set(declaration) != {'kind', 'state_dir', 'appid', 'app_secret_file', 'image_policy'}
            or declaration.get('image_policy') != 'disabled'):
        raise ValueError('Only disabled-image guest configuration is accepted')
    state = safe_path(declaration['state_dir'])
    snapshot = safe_path(snapshot_dir)
    code = Path(__file__).resolve().parents[1]
    if (state.is_relative_to(snapshot) or snapshot.is_relative_to(state)
            or state.is_relative_to(code) or code.is_relative_to(state)):
        raise ValueError('Guest state must be separate from release and snapshot')
    config = load_config(path)
    return GuestOnlyGateway(config, source, origin), manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['inspect', 'check', 'serve'])
    parser.add_argument('--snapshot-dir', type=Path, required=True)
    parser.add_argument('--mini-config', type=Path)
    parser.add_argument('--origin')
    parser.add_argument('--port', type=int, default=8011)
    args = parser.parse_args()
    if not 1024 <= args.port <= 65535:
        parser.error('Use an unprivileged loopback port')
    source, manifest = load_snapshot(args.snapshot_dir)
    if args.action != 'inspect':
        if not args.mini_config or not args.origin:
            parser.error('check/serve require a private mini config and explicit HTTPS origin')
        app, _ = make_app(args.snapshot_dir, args.mini_config, args.origin)
    print(json.dumps({'stage': 1, 'snapshot_kind': manifest['kind'],
        'versions': {'cn': source.score_versions.version,
                     'global': source.global_score_versions.version},
        'files': manifest['files'], 'image_policy': 'disabled',
        'accounts_enabled': False, 'business_bridge_enabled': False,
        'ocr_worker_started': False,
        'real_wechat_exchange_verified': False}), flush=True)
    if args.action == 'serve':
        import uvicorn
        uvicorn.run(app, host='127.0.0.1', port=args.port, proxy_headers=False,
                    access_log=False, log_level='warning', server_header=False,
                    lifespan='off', limit_concurrency=32, backlog=64,
                    timeout_keep_alive=5, h11_max_incomplete_event_size=16384)


if __name__ == '__main__':
    main()
