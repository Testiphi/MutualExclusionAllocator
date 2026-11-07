"""In-process acceptance of the packaged code, fresh state and patched platform only."""
import argparse
import json
from pathlib import Path
import sys
import secrets
import tempfile
from unittest.mock import patch


def validate(candidate):
    candidate=Path(candidate).resolve()
    sys.path.insert(0,str(candidate))
    from fastapi.testclient import TestClient
    from backend.mini_account_isolation import provision,prepare_account_stopped,backup_stopped,restore_stopped,preflight
    from backend.mini_account_service import make_app,provenance,KIND
    from backend.mini_auth import WechatVerifier
    assert Path(sys.modules['backend.mini_account_service'].__file__).resolve().is_relative_to(candidate)
    delivery=provenance();assert delivery['fixed_delivery']
    origin='https://packaged-account.example.test'
    proxy={'X-Forwarded-Proto':'https','X-Real-IP':'192.0.2.80'}
    a='/api/mini/account/v1'
    def write(path,data):
        path.write_text(json.dumps(data),encoding='utf-8');path.chmod(0o600)
    with tempfile.TemporaryDirectory() as directory:
        parent=Path(directory).resolve();root=parent/'state'
        password=secrets.token_urlsafe(24)
        provision(root,candidate/'snapshot',origin,candidate/'docs/FIXED_SNAPSHOT_BINDING.json')
        prepare_account_stopped(root,'packaged@example.test',password)
        secret=parent/'fixture-secret';secret.write_text(secrets.token_urlsafe(32));secret.chmod(0o600)
        mini=parent/'mini.json';config=parent/'service.json'
        write(mini,{'kind':'racepick-mini-guests-v1','state_dir':str(root/'guests'),'appid':'wx'+'0'*16,
                    'app_secret_file':str(secret),'image_policy':'disabled','account_state_dir':str(root/'native')})
        declaration={'kind':KIND,'origin':origin,'state_root':str(root),'mini_config':str(mini),'enabled':True,'cloud_writes':True}
        write(config,declaration)
        with patch.object(WechatVerifier,'__call__',return_value='owned-packaged-fixture-subject'):
            app=make_app(config)
            with TestClient(app,base_url=origin,client=('127.0.0.1',12000)) as client:
                health=client.get('/_account-test/health',headers=proxy)
                assert health.status_code==200 and health.json()['delivery_id']==delivery['delivery_id']
                assert client.get('/').status_code==400
                for name in ('cars.json','gauntlet_data.json','cars.global.json','gauntlet_data.global.json','global-data-manifest.json'):
                    assert client.get('/'+name,headers=proxy).content==(candidate/'snapshot'/name).read_bytes()
                result=client.post('/api/mini/v1/session',headers=proxy,json={
                    'code':'packaged-fixture-code','client_schema':1,'request_key':'packaged-guest-key'})
                assert result.status_code==200
                guest={**proxy,'Authorization':'Bearer '+result.json()['token']}
                login=client.post(a+'/auth/login',headers=guest,json={'schema':1,'request_key':'packaged-login-key',
                    'email':'packaged@example.test','password':password})
                assert login.status_code==200
                auth={**proxy,'Authorization':'Bearer '+login.json()['token'],'X-Account-ID':login.json()['actor']['id']}
                for server in ('cn','global'):
                    initial=client.get(a+'/profile?server='+server,headers=auth)
                    assert initial.status_code==200 and initial.json()['profile'] is None
                # Separate browser transport; its Cookie never enters a native request.
                browser=TestClient(app,base_url=origin,client=('127.0.0.1',12001))
                try:
                    me=browser.get('/api/auth/me',headers=proxy).json()
                    logged=browser.post('/api/auth/login',headers={**proxy,'Origin':origin,'X-CSRF-Token':me['csrf']},
                        json={'email':'packaged@example.test','password':password})
                    assert logged.status_code==200
                    web={**proxy,'X-Account-ID':logged.json()['user']['id']}
                    assert browser.get('/api/me/profile?server=global',headers=web).json()['profile'] is None
                    body={'schema':1,'request_key':'packaged-profile-key','explicit_save':True,'intent':'save',
                          'revision':0,'cars':[],'stars':{},'ocMap':{}}
                    assert client.put(a+'/profile?server=global',headers=auth,json=body).status_code==200
                    assert browser.get('/api/me/profile?server=global',headers=web).json()['revision']==1
                    assert browser.get('/api/me/profile?server=cn',headers=web).json()['profile'] is None
                    conflict=client.put(a+'/profile?server=global',headers=auth,json={**body,'request_key':'packaged-conflict-key'})
                    assert conflict.status_code==409 and 'current' in conflict.json() and 'submitted' in conflict.json()
                    assert client.get(a+'/operations/packaged-profile-key?action=profile-save&server=cn',headers=auth).status_code==409
                finally:browser.close()
                for path in (a+'/auth/register','/api/auth/register','/api/auth/verify-email','/api/admin/accounts','/api/mini/v1/map-recognition/jobs'):
                    assert client.post(path,headers=guest,json={}).status_code==404
                assert client.delete(a+'/session',headers=auth).status_code==200
                assert client.get(a+'/operations/packaged-login-key?action=login',headers=guest).status_code==401
                assert client.get(a+'/session',headers=guest).status_code==200
            backup_stopped(root,parent/'backup');restore_stopped(parent/'backup',parent/'restored')
            assert preflight(parent/'restored')['schemas']==preflight(root)['schemas']
        write(config,{**declaration,'enabled':False,'cloud_writes':False,'state_root':str(parent/'absent')})
        with TestClient(make_app(config),base_url=origin) as closed:
            assert closed.get(a+'/session').status_code==404
        assert not any(name in sys.modules for name in ('backend.map_recognition','onnxruntime','rapidocr','backend.ocr_queue_bridge'))
    return {'delivery_id':delivery['delivery_id'],'packaged_code_only':True,'checks_passed':True,
        'fresh_fixture_state':True,'shared_website_native_database':True,'independent_restore':True,
        'real_platform':False,'smtp':False,'real_account_or_cloud':False,'ocr_model_loaded':False}


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--candidate',type=Path,required=True)
    print(json.dumps(validate(p.parse_args().candidate)))
