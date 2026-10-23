"""Native runtime smoke test with disposable DB; never sends SMTP or touches live DB."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import http.client
import json
import os
import socket
import tempfile
import threading
import time
import uvicorn
from backend.production import initialize,make_app,backup,restore,service_lock
from validate_data import validate_data


def main():
 root=Path(__file__).resolve().parents[1]
 errors,_=validate_data(json.loads((root/'gauntlet_data.json').read_text(encoding='utf-8')),json.loads((root/'cars.json').read_text(encoding='utf-8')))
 assert not errors,errors
 from tools.build_global_data import validate_global_bundle
 global_files={n:(root/n).read_bytes() for n in ('cars.global.json','gauntlet_data.global.json','global-data-manifest.json')}
 validate_global_bundle(*(json.loads(raw) for raw in global_files.values()),raw_files=global_files)
 with tempfile.TemporaryDirectory() as directory:
  config={'origin':'https://racepick.cn','owner_email':'smoke@example.com','data_dir':str(Path(directory)/'state'),'mail_daily_limit':1}
  initialize(config);app=make_app(config,'unused-selfcheck-secret')
  sock=socket.socket();sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
  server=uvicorn.Server(uvicorn.Config(app,log_level='error',proxy_headers=False,access_log=False))
  thread=threading.Thread(target=server.run,kwargs={'sockets':[sock]},daemon=True);thread.start()
  try:
   for _ in range(100):
    if server.started:break
    time.sleep(.1)
   assert server.started,'服务未启动'
   for path,code in [('/api/health',200),('/api/auth/me',200),('/?server=global',200),*((f'/{n}',200) for n in global_files),('/data-previews',404),('/api/admin/writeback',404),('/production.json',404)]:
    conn=http.client.HTTPConnection('127.0.0.1',port,timeout=5)
    try:
     conn.request('GET',path,headers={'Host':'racepick.cn','X-Forwarded-Proto':'https','X-Real-IP':'192.0.2.1'})
     r=conn.getresponse();body=r.read();assert r.status==code,(path,r.status,body)
     if path[1:] in global_files:assert body==global_files[path[1:]],path
     if path=='/api/auth/me':assert 'Secure' in r.getheader('Set-Cookie') and json.loads(body)['mail_mode']=='production'
    finally:conn.close()
  finally:server.should_exit=True;thread.join(10);sock.close()
  assert not thread.is_alive(),'服务未停止'
  if os.name=='posix':
   snapshot=backup(config)
   with service_lock(Path(config['data_dir'])):
    try:restore(config,snapshot)
    except ValueError:pass
    else:raise AssertionError('恢复锁未阻止并发服务')
   restore(config,snapshot)
   from backend.score_production import source_snapshot,migrate,backup as score_backup,drill,toggle
   _,hashes=source_snapshot(root)
   result=migrate(config,root,hashes['gauntlet_data.json'],hashes['cars.json'])
   assert result['existing_rows_preserved'] and not result['write_enabled']
   migration_app=make_app(config,'unused-selfcheck-secret')
   assert migration_app.state.score_versions.current()[0]['id']==result['version']
   bundle=score_backup(config);assert drill(config,bundle)['version']==result['version']
   assert toggle(config,True)['write_enabled']
   from backend.contribution_production import migrate as migrate_contributions,preflight
   before=preflight(config)
   assert before['contribution_schema']==0
   with service_lock(Path(config['data_dir'])):
    try:migrate_contributions(config,result['version'])
    except ValueError:pass
    else:raise AssertionError('贡献迁移未拒绝活动服务锁')
   upgraded=migrate_contributions(config,result['version'])
   assert upgraded['existing_rows_preserved'] and upgraded['historical_submissions_enrolled']==0
   assert upgraded['score_writes'] and upgraded['score_version']==result['version']
   assert not any(upgraded['contribution_counts'].values())
   assert migrate_contributions(config,result['version'])['already_migrated']
   from backend.feedback_production import migrate as migrate_feedback,preflight as feedback_preflight
   before_feedback=feedback_preflight(config)
   assert before_feedback['feedback_schema']==0
   with service_lock(Path(config['data_dir'])):
    try:migrate_feedback(config,result['version'])
    except ValueError:pass
    else:raise AssertionError('反馈迁移未拒绝活动服务锁')
   feedback=migrate_feedback(config,result['version'])
   assert feedback['existing_rows_preserved'] and feedback['test_feedback_imported']==0
   assert feedback['feedback_schema']==1 and not any(feedback['feedback_counts'].values())
   for field in ('score_version','score_writes','contribution_counts','counts','active_files'):
    assert feedback[field]==before_feedback[field],field
   assert migrate_feedback(config,result['version'])['already_migrated']
   bundle=score_backup(config);restored=drill(config,bundle)
   assert restored['contribution_schema']==1 and not restored['active_database_replaced']
   assert restored['feedback_schema']==1 and not any(restored['feedback_counts'].values())
   upgraded_app=make_app(config,'unused-selfcheck-secret')
   sock=socket.socket();sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
   server=uvicorn.Server(uvicorn.Config(upgraded_app,log_level='error',proxy_headers=False,access_log=False))
   thread=threading.Thread(target=server.run,kwargs={'sockets':[sock]},daemon=True);thread.start()
   try:
    for _ in range(100):
     if server.started:break
     time.sleep(.1)
    assert server.started
    for route in ('/api/health','/leaderboard','/leaderboard.js','/leaderboard.css','/api/contributions/leaderboard','/feedback','/admin-feedback','/feedback.js','/ui.css'):
     conn=http.client.HTTPConnection('127.0.0.1',port,timeout=5)
     try:
      conn.request('GET',route,headers={'Host':'racepick.cn','X-Forwarded-Proto':'https','X-Real-IP':'192.0.2.1'})
      response=conn.getresponse();body=response.read();assert response.status==200,(route,response.status,body)
      if route=='/api/health':assert json.loads(body)['contribution_schema']==1 and json.loads(body)['score_version']==result['version'] and json.loads(body)['feedback_schema']==1 and json.loads(body)['feedback']
      if route=='/leaderboard':assert '独立本地验收环境' not in body.decode()
     finally:conn.close()
   finally:server.should_exit=True;thread.join(10);sock.close()
   assert not thread.is_alive()
   assert not toggle(config,False)['write_enabled']
 print('production runtime smoke: PASS (temporary database; no email sent)')
if __name__=='__main__':main()
