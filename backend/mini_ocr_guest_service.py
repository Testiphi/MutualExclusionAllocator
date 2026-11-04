"""Isolated guest HTTP gateway with an opt-in socket-only OCR queue port."""
import argparse
import json
from pathlib import Path
import re

from backend.mini_api import MiniGateway
from backend.mini_auth import load_config
from backend.mini_guest_service import (GuestOnlyGateway,load_snapshot,safe_path,
                                         validate_origin,digest,PREFIX)


class OcrGuestGateway(GuestOnlyGateway):
    def __init__(self,config,source,origin,service=None):
        if (config.get('fixture') is not False or config.get('account_store') is not None
                or config.get('mirror_fixture_writes') or config.get('image_policy') not in ('disabled','aliyun_baseline')):
            raise ValueError('Only real guest auth and a disabled/baseline image policy are accepted')
        self.images=config['image_policy']=='aliyun_baseline'
        if self.images and not getattr(service,'is_bridge',False):
            raise ValueError('Baseline images require the socket queue port')
        self.gateway=MiniGateway(self.unavailable,config=config,source=source,
            service=service if self.images else None,origin=validate_origin(origin),production=True)

    async def __call__(self,scope,receive,send):
        if scope['type']=='http':
            method,path=scope['method'],scope['path']
            allowed={('POST',PREFIX+'/session'),('GET',PREFIX+'/snapshot')}
            if self.images:
                allowed|={('GET',PREFIX+'/map-recognition/catalog'),('POST',PREFIX+'/map-recognition/jobs'),
                          ('GET',PREFIX+'/map-recognition/jobs/by-request')}
                if method in ('GET','DELETE') and re.fullmatch(re.escape(PREFIX)+r'/map-recognition/jobs/[a-f0-9]{32}',path):
                    allowed.add((method,path))
            known=any(candidate==path for _,candidate in allowed)
            if (method,path) in allowed or (method=='OPTIONS' and known):
                return await self.gateway(scope,receive,send)
        return await super().__call__(scope,receive,send)


def make_app(snapshot_dir,mini_config,origin,*,client_factory=None):
    source,manifest=load_snapshot(snapshot_dir)
    path=safe_path(mini_config)
    declaration=json.loads(path.read_bytes())
    fields={'kind','state_dir','appid','app_secret_file','image_policy','bridge_socket'}
    if (set(declaration)!=fields or declaration['image_policy'] not in ('disabled','aliyun_baseline')
            or not isinstance(declaration['bridge_socket'],str) or not declaration['bridge_socket'].startswith('/')
            or '..' in declaration['bridge_socket'].split('/') or '\\' in declaration['bridge_socket']):
        raise ValueError('Strict guest/OCR configuration required; account/queue/provider paths forbidden')
    state=safe_path(declaration['state_dir']);snapshot=safe_path(snapshot_dir)
    code=Path(__file__).resolve().parents[1]
    if any(a.is_relative_to(b) or b.is_relative_to(a) for a,b in [(state,snapshot),(state,code)]):
        raise ValueError('Guest state must be independent of code and snapshot')
    config=load_config(path,image_bridge=True)
    port=None
    if declaration['image_policy']=='aliyun_baseline':
        from backend.ocr_queue_bridge import QueueBridgeClient
        from backend.mini_bridge_port import BridgeRecognitionPort
        info,contents=source.score_versions.current()
        catalog={'server':'cn','version':digest((info['id']+':').encode()+contents['gauntlet_data.json']),
            'maps':[{'big':r['大地图'],'small':r['小地图']} for r in json.loads(contents['gauntlet_data.json'])['tracks']]}
        port=BridgeRecognitionPort((client_factory or QueueBridgeClient)(declaration['bridge_socket']),catalog)
    return OcrGuestGateway(config,source,origin,port),manifest


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['inspect','check','serve'])
    parser.add_argument('--snapshot-dir',required=True,type=Path)
    parser.add_argument('--mini-config',type=Path)
    parser.add_argument('--origin');parser.add_argument('--port',type=int,default=8011)
    args=parser.parse_args()
    if not 1024<=args.port<=65535:parser.error('Use an unprivileged loopback port')
    source,manifest=load_snapshot(args.snapshot_dir)
    if args.action!='inspect':
        if not args.mini_config or not args.origin:parser.error('Explicit private config and HTTPS origin required')
        app,_=make_app(args.snapshot_dir,args.mini_config,args.origin)
    print(json.dumps({'stage':2,'files':manifest['files'],'accounts_enabled':False,
        'business_database_opened':False,'ocr_model_started':False,'provider_credentials_loaded':False,
        'public_ocr_verified':False,'image_policy':'inspect-only' if args.action=='inspect' else ('aliyun_baseline' if app.images else 'disabled')}))
    if args.action=='serve':
        import uvicorn
        uvicorn.run(app,host='127.0.0.1',port=args.port,proxy_headers=False,access_log=False,
                    log_level='warning',server_header=False,lifespan='off',limit_concurrency=32,
                    backlog=64,timeout_keep_alive=5,h11_max_incomplete_event_size=16384)


if __name__=='__main__':main()
