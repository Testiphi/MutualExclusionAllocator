"""Isolated A account test service. No production DB, OCR, SMTP or auto migrations."""
import argparse
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

from fastapi.responses import JSONResponse
from backend.mini_account_boundary import AccountBoundary, AccountBoundaryOptions
from backend.mini_account_isolation import private, preflight, provision, service_lock, backup_stopped, restore_stopped
from backend.mini_api import MiniGateway
from backend.mini_snapshot import load_snapshot, validate_origin, FILES

KIND='racepick-mini-account-service-v1'
ASSETS={'styles.css','config.js','api.js','app_state.js','allocator.js','race_scores.js','selection_core.js',
        'home_presenter.js','home_theme.json','auth.js','profile_store.js','accounts.css','ui.css','theme.css',
        'notifications.js','announcements.js',*FILES}
WEB_READ={('GET','/'),('HEAD','/'),('GET','/api/auth/me'),('GET','/api/me/profile')}
WEB_AUTH={('POST','/api/auth/login'),('POST','/api/auth/logout')}
HEALTH='/_account-test/health'


def provenance():
    root=Path(__file__).resolve().parents[1]
    manifest=root/'CANDIDATE.json'
    if not manifest.exists():return {'delivery_id':None,'source_commit':None,'fixed_delivery':False}
    declaration=json.loads(manifest.read_bytes())
    for name,record in declaration['files'].items():
        path=root/name
        if (Path(name).is_absolute() or '..' in Path(name).parts or not path.is_file() or path.is_symlink() or path.resolve()!=path.absolute()
                or path.stat().st_size!=record['bytes'] or hashlib.sha256(path.read_bytes()).hexdigest()!=record['sha256']):
            raise ValueError('Candidate delivery file integrity mismatch')
    return {'delivery_id':declaration['delivery_id'],'source_commit':declaration['source_commit'],'fixed_delivery':True}


def settings(path):
    data=json.loads(private(path).read_bytes())
    required={'kind','origin','state_root','mini_config','enabled','cloud_writes'}
    if not required<=set(data)<=required|{'registration','wechat_binding'} or data['kind']!=KIND:
        raise ValueError('Strict account service declaration required')
    validate_origin(data['origin'])
    AccountBoundaryOptions(data['enabled'],data['cloud_writes'],data.get('registration',False),data.get('wechat_binding',False))
    if not isinstance(data['state_root'],str) or not Path(data['state_root']).is_absolute():
        raise ValueError('Explicit absolute isolated state root required')
    if not isinstance(data['mini_config'],str) or not Path(data['mini_config']).is_absolute():
        raise ValueError('Explicit absolute private platform config required')
    return data


async def reply(scope,receive,send,status,code):
    response=JSONResponse({'schema_version':1,'code':code},status_code=status,
                          headers={'Cache-Control':'no-store','X-Content-Type-Options':'nosniff','Referrer-Policy':'no-referrer'})
    return await response(scope,receive,send)


class IsolatedAccountService:
    """Acquire exclusive state ownership at ASGI startup before opening any API state."""
    def __init__(self,declaration):
        self.config=declaration
        self.options=AccountBoundaryOptions(declaration['enabled'],declaration['cloud_writes'],declaration.get('registration',False),declaration.get('wechat_binding',False))
        self.lease=None;self.web=None;self.native=None;self.started=False

    def start(self):
        if self.started:raise ValueError('Service is already started')
        if not self.options.enabled:
            self.started=True
            return
        config=self.config;root=Path(config['state_root'])
        self.provenance=provenance()
        preflight(root,config['origin'])
        self.lease=service_lock(root);self.lease.__enter__()
        try:
            preflight(root,config['origin'])
            # Validate declaration BEFORE load_config opens keys or any optional stores.
            mini_path=private(config['mini_config'])
            raw=json.loads(mini_path.read_bytes())
            if (set(raw)!={'kind','state_dir','appid','app_secret_file','image_policy','account_state_dir'}
                    or raw['image_policy']!='disabled'
                    or Path(raw['state_dir'])!=root/'guests' or Path(raw['account_state_dir'])!=root/'native'):
                raise ValueError('Platform declaration must bind only this isolated guest/native state')
            secret=Path(raw['app_secret_file'])
            if secret.is_relative_to(root):raise ValueError('Platform credentials must remain outside state/backups')
            from backend.mini_auth import load_config
            mini=load_config(mini_path)
            mini['account_a_only']=True
            mini['isolated_player_registration']=self.options.registration
            from backend.app import create_app
            from backend.mailing import MailConfig
            self.web=create_app(root/'accounts',config['origin'],production=True,
                mail_config=MailConfig(isolated_file_limits=self.options.registration),isolated_account_root=root)
            snapshot,_=load_snapshot(root/'snapshot')
            if self.options.wechat_binding:
                from backend.mini_wechat_binding import bound
                bound(self.web.state.store, '')
                mini['isolated_wechat_binding']=True
            self.source=SimpleNamespace(**self.web.state._state,
                score_versions=snapshot.score_versions,global_score_versions=snapshot.global_score_versions)
            gateway=MiniGateway(self.web,config=mini,source=self.source,service=None,origin=config['origin'],production=True)
            self.native=AccountBoundary(lambda:gateway,self.options)
            def health():
                return {'kind':KIND,'status':'ok','mode':'isolated-account-test',
                    'enabled':True,'cloud_writes':self.options.cloud_writes,'mail_mode':'file',
                    'registration':self.options.registration,
                    **({'wechat_binding':True} if self.options.wechat_binding else {}),
                    'native_batches':{'A':'ready',**dict.fromkeys(('B','C','D','E'),'pending')},
                    'schemas':{'business':6,'global_profile':1,'guest':1,'native_account':1},
                    'coverage_schema':0,'global_score_schema':0,'ocr_enabled':False,'production_business':False,
                    'snapshot_versions':{'cn':snapshot.score_versions.version,'global':snapshot.global_score_versions.version},
                    **self.provenance}
            self.web.add_api_route(HEALTH,health,methods=['GET'])
            self.started=True
        except BaseException:
            self.stop()
            raise

    def stop(self):
        self.web=None;self.native=None;self.started=False
        if self.lease is not None:
            lease,self.lease=self.lease,None
            lease.__exit__(None,None,None)

    async def __call__(self,scope,receive,send):
        if scope['type']=='lifespan':
            while True:
                event=await receive()
                if event['type']=='lifespan.startup':
                    try:self.start()
                    except Exception:
                        await send({'type':'lifespan.startup.failed','message':'Isolated account startup rejected; check private config/state locally'})
                        return
                    await send({'type':'lifespan.startup.complete'})
                elif event['type']=='lifespan.shutdown':
                    self.stop();await send({'type':'lifespan.shutdown.complete'});return
        if scope['type']=='websocket':return await send({'type':'websocket.close','code':1008})
        if not self.started or not self.options.enabled:
            return await reply(scope,receive,send,404,'NATIVE_DISABLED')
        path,method=scope['path'],scope['method']
        if path=='/api/mini' or path.startswith('/api/mini/'):
            return await self.native(scope,receive,send)
        # Web login uses the same existing handlers/DB but keeps its own HTTPS Cookie/CSRF.
        if ((method,path) in WEB_READ|WEB_AUTH|{('GET',HEALTH)} or
                method in ('GET','HEAD') and path[1:] in ASSETS):
            return await self.web(scope,receive,send)
        if (method,path)==('PUT','/api/me/profile'):
            if self.options.cloud_writes:return await self.web(scope,receive,send)
            return await reply(scope,receive,send,503,'ACCOUNT_CLOUD_WRITE_DISABLED')
        # Do not expose app's installed submissions/community/admin/mail/health routes.
        return await reply(scope,receive,send,404,'ACCOUNT_ROUTE_PENDING')


def make_app(path):
    return IsolatedAccountService(settings(path))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='action',required=True)
    p=sub.add_parser('provision');p.add_argument('--state-root',type=Path,required=True)
    p.add_argument('--snapshot-dir',type=Path,required=True);p.add_argument('--binding',type=Path,required=True);p.add_argument('--origin',required=True);p.add_argument('--wechat-binding',action='store_true')
    p=sub.add_parser('check');p.add_argument('--config',type=Path,required=True)
    p=sub.add_parser('serve');p.add_argument('--config',type=Path,required=True);p.add_argument('--port',type=int,required=True)
    p=sub.add_parser('prepare-account-stopped');p.add_argument('--state-root',type=Path,required=True)
    p.add_argument('--email',required=True);p.add_argument('--confirm-new-isolated-account',action='store_true',required=True)
    for command in ('backup-stopped','restore-new'):
        p=sub.add_parser(command);p.add_argument('--source',type=Path,required=True);p.add_argument('--destination',type=Path,required=True)
    args=parser.parse_args()
    if args.action=='provision':
        result=provision(args.state_root,args.snapshot_dir,args.origin,args.binding,wechat_binding=args.wechat_binding)
    elif args.action=='prepare-account-stopped':
        import getpass,sys,warnings
        if not sys.stdin.isatty():parser.error('Interactive hidden password input required; no pipe or command-line password')
        from backend.mini_account_isolation import prepare_account_stopped
        with warnings.catch_warnings():
            warnings.simplefilter('error',getpass.GetPassWarning)
            password=getpass.getpass('New isolated account password (hidden): ')
            confirmation=getpass.getpass('Repeat password (hidden): ')
        if password!=confirmation:parser.error('Passwords differ; no account operation performed')
        result=prepare_account_stopped(args.state_root,args.email,password)
    elif args.action in ('backup-stopped','restore-new'):
        result=(backup_stopped if args.action=='backup-stopped' else restore_stopped)(args.source,args.destination)
    else:
        config=settings(args.config)
        if args.action=='check':
            # Disabled check doesn't read state or credentials, just the declaration.
            result={'enabled':config['enabled'],'cloud_writes':config['cloud_writes'],
                    'state_checked':False,'credentials_loaded':False}
            if config['enabled']:result.update(preflight(config['state_root'],config['origin']),state_checked=True)
        else:
            if not 1024<=args.port<=65535:parser.error('Use an unprivileged loopback port')
            import uvicorn
            uvicorn.run(IsolatedAccountService(config),host='127.0.0.1',port=args.port,proxy_headers=False,
                access_log=False,log_level='warning',server_header=False,lifespan='on',
                limit_concurrency=32,backlog=64,timeout_keep_alive=5,h11_max_incomplete_event_size=16384)
            return
    print(json.dumps(result,ensure_ascii=False))


if __name__=='__main__':main()
