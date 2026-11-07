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

from backend.mini_snapshot import (FILES,KIND,PREFIX,digest,canonical,safe_path,
                                   validate_origin,FrozenWriter,load_snapshot)


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
