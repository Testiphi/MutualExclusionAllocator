"""Explicit B-E native whitelist; original typed handlers remain the business authority."""
import copy
import inspect
import json
import time
from fastapi import Request,HTTPException,Query
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse,Response
from fastapi.exceptions import RequestValidationError
from starlette.concurrency import run_in_threadpool
from starlette.routing import compile_path
from backend.mini_auth import MiniError,fail,request_key
from backend.mini_api import limited_body

PREFIX='/api/mini/account/v1'
# batch, method, original path; never forward a client-supplied destination.
ROUTES=(
 ('B','GET','/api/coverage'),('B','POST','/api/coverage/view'),('B','POST','/api/coverage/choice'),
 ('C','GET','/api/submissions/catalog'),('C','POST','/api/submissions'),('C','GET','/api/submissions'),
 ('C','GET','/api/submissions/{sid}'),('C','PUT','/api/submissions/{sid}'),('C','POST','/api/submissions/{sid}/submit'),
 ('C','POST','/api/submissions/{sid}/images'),('C','DELETE','/api/submissions/{sid}/images/{iid}'),('C','GET','/api/submissions/{sid}/images/{iid}'),
 ('C','GET','/api/contributions/leaderboard'),('C','GET','/api/contributions/me'),('C','PUT','/api/contributions/preferences'),
 ('D','GET','/api/feedback/context'),('D','POST','/api/feedback'),('D','GET','/api/feedback'),
 ('D','GET','/api/feedback/{tid}'),('D','POST','/api/feedback/{tid}/reply'),
 ('D','GET','/api/announcements'),('D','GET','/api/me/announcement-preferences'),('D','PUT','/api/me/announcement-preferences'),
 ('D','POST','/api/me/announcements/{aid}/dismiss'),('D','DELETE','/api/me/announcements/{aid}/dismiss'),
 ('D','POST','/api/usage/session'),('D','POST','/api/usage/events'),
 ('D','GET','/api/notifications'),('D','POST','/api/notifications/read'),
 ('E','POST','/api/admin/submissions/{sid}/preview'),('E','POST','/api/admin/submissions/{sid}/review'),
 ('E','POST','/api/admin/contributions/{sid}/rating'),
 ('E','GET','/api/admin/feedback'),('E','GET','/api/admin/feedback/summary'),('E','GET','/api/admin/feedback/{tid}'),('E','POST','/api/admin/feedback/{tid}/handle'),
 ('E','GET','/api/admin/accounts'),('E','POST','/api/admin/accounts/{uid}/control'),('E','GET','/api/admin/accounts/{uid}/events'),
 ('E','GET','/api/admin/invitations'),('E','POST','/api/admin/invitations'),('E','POST','/api/admin/invitations/{iid}/revoke'),
 ('E','GET','/api/admin/members'),('E','POST','/api/admin/members/{uid}/revoke'),
 ('E','GET','/api/admin/announcements'),('E','POST','/api/admin/announcements'),('E','PUT','/api/admin/announcements/{aid}'),('E','POST','/api/admin/announcements/{aid}/state'),
 ('E','GET','/api/admin/usage'),('E','GET','/api/admin/usage/accounts'),('E','GET','/api/admin/usage/accounts/{uid}'),
 ('E','GET','/api/admin/score-versions'),('E','POST','/api/admin/score-versions/reauth'),('E','POST','/api/admin/score-versions'),
 ('E','GET','/api/admin/score-versions/{bid}'),('E','POST','/api/admin/score-versions/{bid}/execute'),
 ('E','POST','/api/admin/score-versions/{bid}/rollback'),('E','POST','/api/admin/score-versions/{bid}/recover'),
)
PUBLIC={('GET','/api/coverage'),('POST','/api/coverage/view'),('GET','/api/contributions/leaderboard'),('GET','/api/announcements'),('POST','/api/usage/session'),('POST','/api/usage/events')}
READ_POST={('POST','/api/coverage/view'),('POST','/api/usage/session')}


def path_for(original):return PREFIX+original[4:]


def policy(batch,method,original):
    mutation=method not in ('GET','HEAD') and (method,original) not in READ_POST
    role='account'
    if (method,original) in PUBLIC:role='public'
    if batch=='E':role='reviewer' if original.startswith(('/api/admin/submissions/','/api/admin/contributions/')) else 'superadmin'
    return {'batch':batch,'method':method,'original':original,'path':path_for(original),'access':role,'mutation':mutation,
            'max_bytes':3000000 if original.endswith('/images') else 8192 if original.startswith('/api/usage/') else 65536}


POLICIES=[{**policy(*row),'regex':compile_path(path_for(row[2]))[0]} for row in ROUTES]
POLICIES.append({**policy('C','POST','/api/submissions/{sid}/images'),
    'path':PREFIX+'/submissions/{sid}/images/upload','regex':compile_path(PREFIX+'/submissions/{sid}/images/upload')[0],
    'multipart':True,'max_bytes':2*1024*1024+65536,'file_max_bytes':2*1024*1024})


def match(request):
    for entry in POLICIES:
        if request.method==entry['method'] and entry['regex'].fullmatch(request.url.path):return entry
    return None


def writes_enabled(config,source):
    if config.get('mirror_fixture_writes') is not True or getattr(source,'production',False):return False
    try:
        from backend.score_repository import validate_lab
        from pathlib import Path
        writer=getattr(source,'score_versions',None)
        if writer is None or getattr(writer,'production',False):return False
        lab,_=validate_lab(writer.lab,source.store.directory)
        if config.get('fixture') is True:return True
        if Path(config['mirror_lab'])!=lab:return False
        record=json.loads((lab/'mini-integration.json').read_text('utf-8'))
        return record.get('full_mirror') is True and Path(record['account_state'])==config['account_store'].root and Path(record['guest_state'])==config['store'].root
    except (KeyError,ValueError,OSError):return False


async def guard(request,entry,config,source):
    role=entry['access'];actor=getattr(request.state,'actor',None)
    if role=='reviewer' and (not actor or actor['role'] not in ('admin','superadmin')):fail(403,'REVIEWER_REQUIRED','需要实时管理员权限')
    if role=='superadmin' and (not actor or actor['role']!='superadmin'):fail(403,'SUPERADMIN_REQUIRED','需要实时超级管理员权限')
    if entry['mutation']:
        if not writes_enabled(config,source):fail(503,'MIRROR_WRITE_DISABLED','本批业务写仅在显式新建的全功能隔离环境开放')
        if entry['batch']=='E' and not entry['original'].endswith('/reauth') and time.time()-request.state.account['authenticated_at']>600:
            fail(403,'STEP_UP_REQUIRED','请先使用账号再认证接口更新认证；成绩发布另须业务专属再认证')
        request_key(request.headers.get('idempotency-key'))
    if request.method not in ('GET','HEAD'):
        expected='multipart/form-data' if entry.get('multipart') else 'application/json'
        if request.headers.get('content-type','').split(';')[0]!=expected:fail(415,'BODY_TYPE_REQUIRED','正文类型不符合此路径契约')
        request._body=await limited_body(request,entry['max_bytes'])
    pairs=list(request.query_params.multi_items())
    if len({k for k,v in pairs})!=len(pairs):fail(422,'QUERY_DUPLICATED','query字段不能重复')


def native_links(value):
    if isinstance(value,list):return [native_links(item) for item in value]
    if isinstance(value,dict):
        return {key:(path_for(item) if key=='url' and isinstance(item,str) and item.startswith('/api/submissions/') else native_links(item)) for key,item in value.items()}
    return value


def install(app,config,source):
    accounts=config['account_store'];web=source.native_accounts
    source_routes=source.native_feature_routes
    registered=[]

    def binding(server):
        if server not in ('cn','global'):fail(422,'INVALID_SERVER','服别无效')
        writer=getattr(source,'score_versions' if server=='cn' else 'global_score_versions',None)
        if writer is None:fail(503,'COMPONENT_UNAVAILABLE','活动快照组件未启用')
        info,contents=writer.current()
        from backend.mini_api import digest
        return {'server':server,'version':info['id'],'sha256':{n:digest(raw) for n,raw in contents.items()}}

    def wrap(route,entry):
        endpoint=route.endpoint;signature=inspect.signature(endpoint,eval_str=True)
        params=dict(signature.parameters)
        request_name=next((name for name,p in params.items() if p.annotation is Request),None)
        query_names={p.name for p in route.dependant.query_params}
        if entry.get('multipart'):
            body_name=route.dependant.body_params[0].name
            image_model=params[body_name].annotation
            signature=signature.replace(parameters=[p for p in signature.parameters.values() if p.name!=body_name]+[
                inspect.Parameter('revision',inspect.Parameter.KEYWORD_ONLY,annotation=int,default=Query(...,ge=1))])
            query_names={'revision'}
        # Even source functions without Request (public leaderboard) receive native policy context.
        injected='native_request' if request_name is None else request_name
        if request_name is None:
            signature=signature.replace(parameters=[*signature.parameters.values(),inspect.Parameter(injected,inspect.Parameter.KEYWORD_ONLY,annotation=Request)])
        async def invoke(**kwargs):
            request=kwargs.pop(injected)
            if set(request.query_params)-query_names:fail(422,'QUERY_UNKNOWN','存在未固定query字段')
            if entry.get('multipart'):
                import base64
                from backend.mini_api import multipart_image
                image,_=multipart_image(await request.body(),request.headers.get('content-type',''),entry['file_max_bytes'])
                kwargs[body_name]=image_model(revision=kwargs.pop('revision'),data=base64.b64encode(image).decode('ascii'))
            row=getattr(request.state,'account',None)
            internal=web.request(request,row['anchor'] if row else None,row['user_id'] if row else None)
            usage_token=request.headers.get('x-usage-token')
            if usage_token:
                if len(usage_token)>1024 or not usage_token.isascii():fail(400,'USAGE_TOKEN_INVALID','统计token无效')
                internal.scope['headers']=[*internal.scope['headers'],(b'x-usage-token',usage_token.encode('ascii'))]
            if request_name:kwargs[request_name]=internal
            selected=kwargs['body'].server if 'body' in kwargs and hasattr(kwargs['body'],'server') else kwargs.get('server','cn')
            before=binding(selected) if entry['original'] in ('/api/coverage','/api/coverage/view') else None
            transient={}
            def call():
                try:
                    value=endpoint(**kwargs)
                    if inspect.isawaitable(value):raise RuntimeError('Async source endpoints need an explicit adapter')
                    if isinstance(value,Response):
                        if not entry['mutation']:return value
                        payload=json.loads(value.body);status=value.status_code
                    else:payload=jsonable_encoder(value);status=200
                    payload=native_links(payload)
                    if entry['mutation']:
                        with accounts.connect() as audit:
                            audit.execute('INSERT INTO events(action,actor_id,at) VALUES(?,?,?)',('mirror:'+entry['method']+' '+entry['original'],row['user_id'] if row else None,int(time.time())))
                    if entry['original']=='/api/admin/invitations' and entry['method']=='POST' and status==200:
                        transient['response']=JSONResponse(payload,status_code=status)
                        return 409,{'schema_version':1,'code':'ONE_TIME_RESULT_UNRECOVERABLE','detail':'邀请码只返回一次；先查看邀请列表，必要时明确撤销并新建','id':payload['id']}
                    return status,payload
                except HTTPException as error:
                    return error.status_code,{'schema_version':1,'code':'BUSINESS_REJECTED','detail':str(error.detail)}
            if entry['mutation']:
                raw=await request.body();key=request.headers['idempotency-key']
                for value in kwargs.values():
                    if hasattr(value,'request_key') and value.request_key!=key:fail(409,'REQUEST_KEY_MISMATCH','正文request_key必须与Idempotency-Key一致')
                fingerprint={'path':request.url.path,'query':sorted(request.query_params.multi_items()),'body_hmac':accounts.digest(raw.hex())}
                if entry.get('multipart'):
                    fingerprint={'path':request.url.path,'query':sorted(request.query_params.multi_items()),'image_hmac':accounts.digest(image.hex())}
                status,value=await run_in_threadpool(accounts.operation,('feature:'+row['sid']) if row else 'public-feature:'+config['store'].hashed(request.scope['mini_ip']),key,entry['method']+' '+entry['original'],fingerprint,call)
                if 'response' in transient:return transient['response']
                return JSONResponse(value,status_code=status,headers={'Retry-After':'60'} if status==429 else None)
            result=await run_in_threadpool(call)
            if isinstance(result,Response):
                if before:
                    payload=json.loads(result.body)
                    after=binding(before['server'])
                    if after!=before:fail(409,'SNAPSHOT_CHANGED','读取期间活动快照变化，请重查')
                    payload['source_snapshot']=before
                    return JSONResponse(payload,status_code=result.status_code)
                return result
            status,value=result
            if before and status==200:
                if binding(before['server'])!=before:fail(409,'SNAPSHOT_CHANGED','读取期间活动快照变化，请重查')
                value['source_snapshot']=before
            return JSONResponse(value,status_code=status)
        invoke.__signature__=signature
        invoke.__name__='mini_'+entry['batch']+'_'+endpoint.__name__+'_'+entry['method'].lower()
        return invoke

    for entry in POLICIES:
        original=source_routes.get((entry['method'],entry['original']))
        if original is None:
            async def unavailable(request:Request):fail(503,'COMPONENT_UNAVAILABLE','本服务器未启用该业务组件')
            app.add_api_route(entry['path'],unavailable,methods=[entry['method']],tags=[entry['batch']])
            registered.append({**{k:v for k,v in entry.items() if k!='regex'},'available':False})
            continue
        app.add_api_route(entry['path'],wrap(original,entry),methods=[entry['method']],tags=[entry['batch']],name='native_'+original.name)
        registered.append({k:v for k,v in entry.items() if k!='regex'})

    @app.exception_handler(RequestValidationError)
    async def validation(request,error):
        return JSONResponse({'schema_version':1,'code':'FIELD_VALIDATION','detail':'字段或格式无效',
                             'fields':[{'loc':list(item['loc']),'type':item['type']} for item in error.errors()]},status_code=422)

    @app.get(PREFIX+'/feature-operations/{key}',tags=['recovery'])
    async def recover(key:str,request:Request):
        request_key(key)
        if request.query_params:fail(400,'QUERY_UNKNOWN','恢复路径不接受query')
        with accounts.connect() as db:row=db.execute('SELECT * FROM operations WHERE scope=? AND request_key=?',('feature:'+request.state.account['sid'],key)).fetchone()
        if row is None:fail(404,'OPERATION_NOT_FOUND','无保留结果；不要自动换key重传')
        if row['state']!='done':fail(409,'OPERATION_UNCERTAIN','写入进行中或结果不确定，请核对',2)
        return JSONResponse(json.loads(row['result']),status_code=row['status'])

    @app.get(PREFIX+'/contract',tags=['contract'])
    async def contract():return specification()

    def specification():
        spec=copy.deepcopy(app.openapi())
        spec['info']={'title':'RacePick native account and B-E mirror','version':'1.0.0'}
        spec['x-native-policy']={'schema_version':1,'routes':registered,'writes':'explicit isolated full-mirror lab only; production disabled',
            'time_unit':'unix seconds','retry_after_unit':'seconds','identity':'server account bearer; no cookie/origin authority',
            'image_content_safety':'not integrated; legacy evidence validation is not moderation'}
        spec.setdefault('components',{}).setdefault('securitySchemes',{})['NativeAccountBearer']={'type':'http','scheme':'bearer','description':'A account token, not WeChat guest or Cookie'}
        spec['components'].setdefault('schemas',{})['NativeError']={'type':'object','required':['schema_version','code','detail'],'properties':{
            'schema_version':{'const':1},'code':{'type':'string'},'detail':{'type':'string'},'fields':{'type':'array','items':{'type':'object'}}}}
        for entry in registered:
            operation=spec['paths'][entry['path']][entry['method'].lower()]
            operation['x-access']=entry['access'];operation['x-fixture-write']=entry['mutation']
            operation['x-limits']={k:entry[k] for k in ('max_bytes','file_max_bytes') if k in entry}
            operation['security']=[] if entry['access']=='public' else [{'NativeAccountBearer':[]}]
            operation['x-response-contract']='MINI_BATCH_'+entry['batch']+'_20261103.md'
            for status in (400,401,403,404,409,410,413,415,422,429,503):
                operation.setdefault('responses',{})[str(status)]={'description':'Native/unchanged business rejection; no input echo','content':{'application/json':{'schema':{'$ref':'#/components/schemas/NativeError'}}}}
            if entry.get('multipart'):
                operation['requestBody']={'required':True,'content':{'multipart/form-data':{'schema':{'type':'object','required':['image'],'additionalProperties':False,'properties':{'image':{'type':'string','format':'binary'}}}}}}
            if entry['method']=='GET' and entry['original'].endswith('/images/{iid}'):
                operation['responses']['200']={'description':'Private normalized JPEG; native download requires account bearer','content':{'image/jpeg':{'schema':{'type':'string','format':'binary'}}}}
            if entry['access']!='public':operation.setdefault('parameters',[]).append({'name':'X-Account-ID','in':'header','required':True,'schema':{'type':'string'}})
            if entry['mutation']:operation.setdefault('parameters',[]).append({'name':'Idempotency-Key','in':'header','required':True,'schema':{'type':'string','minLength':16,'maxLength':80}})
            if entry['original']=='/api/usage/events':operation.setdefault('parameters',[]).append({'name':'X-Usage-Token','in':'header','required':True,'schema':{'type':'string','maxLength':1024}})
        for schema in spec['components']['schemas'].values():
            for name,field in schema.get('properties',{}).items():
                if name in ('password','token','invite_code'):
                    field['x-sensitive']=True
                    if field.get('type')=='string':field['format']='password'
        return spec
    return {'specification':specification,'routes':registered}
