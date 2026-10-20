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
   for path,code in [('/api/health',200),('/api/auth/me',200),('/data-previews',404),('/api/admin/writeback',404),('/production.json',404)]:
    conn=http.client.HTTPConnection('127.0.0.1',port,timeout=5)
    try:
     conn.request('GET',path,headers={'Host':'racepick.cn','X-Forwarded-Proto':'https','X-Real-IP':'192.0.2.1'})
     r=conn.getresponse();body=r.read();assert r.status==code,(path,r.status,body)
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
 print('production runtime smoke: PASS (temporary database; no email sent)')
if __name__=='__main__':main()
