"""Server-bound read sources and capability gates; maintenance files are never written."""
import hashlib
import json
from fastapi import HTTPException

SERVERS=('cn','global')
CN_CAPABILITIES={'zones':['五区','四区'],'tiers':['理论','高手','普通','自动'],'max_stars_only':False,'oc':False}

def server_id(value='cn'):
    if value not in SERVERS:raise HTTPException(422,'服别无效')
    return value

def capabilities(server,catalog=None):
    server_id(server)
    value=CN_CAPABILITIES if server=='cn' else (catalog or {}).get('capabilities')
    if not isinstance(value,dict):raise HTTPException(409,'缺少服别能力配置')
    return {**value,'zones':list(value['zones']),'tiers':list(value['tiers'])}

def require_scope(server,catalog,zone,tier):
    cap=capabilities(server,catalog)
    if zone not in cap['zones'] or tier not in cap['tiers']:
        raise HTTPException(422,'当前服别尚未开放该分区或档位')
    return cap

def global_source(root):
    from tools.build_global_data import validate_global_bundle
    names=('cars.global.json','gauntlet_data.global.json','global-data-manifest.json')
    try:
        raw={n:(root/n).read_bytes() for n in names}
        catalog,data,manifest=(json.loads(raw[n]) for n in names)
        validate_global_bundle(catalog,data,manifest,raw_files=raw)
    except (OSError,ValueError,KeyError,TypeError) as error:
        raise HTTPException(409,'国际服运行数据校验失败，未回退国服数据') from error
    basis={'data':hashlib.sha256(raw[names[1]]).hexdigest(),'cars':hashlib.sha256(raw[names[0]]).hexdigest()}
    return data,catalog,basis

def target_identity(value):
    # Keep every legacy CN key byte-compatible; new scopes cannot collide with it.
    identity=[value.get(k) for k in ('big','small','zone','tier','car','stars','route')]
    if server_id(value.get('server','cn'))=='global':identity=['global',bool(value.get('oc',False)),*identity]
    return identity
