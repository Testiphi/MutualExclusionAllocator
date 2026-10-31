"""Single external OCR supervisor. Hard deadlines kill/restart only its own child."""
import argparse
from collections import deque
import json
import os
from pathlib import Path
import secrets
import signal
import subprocess
import sys
import time
from backend.map_ocr_production import ProductionRecognitionService,ROOT

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--config',type=Path,required=True)
    args=parser.parse_args();service=ProductionRecognitionService(args.config);root=service.root
    import fcntl
    lock=(root/'supervisor.lock').open('a+b');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    stopping=False;child=None;recent=deque()
    def stop(*_):
        nonlocal stopping
        stopping=True
    signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop)
    def state(value,run_id):
        path=root/'supervisor-state.tmp'
        path.write_text(json.dumps({'state':value,'updated':time.time(),'run_id':run_id,'pid':os.getpid()}))
        os.replace(path,root/'supervisor-state.json')
    def kill():
        if child and child.poll() is None:
            child.terminate()
            try:child.wait(timeout=2)
            except subprocess.TimeoutExpired:child.kill();child.wait(timeout=2)
    service.store.fail_pending('识别服务已重新启动，请重试')
    run_id='';started=0
    try:
        while not stopping:
            now=time.time();service.store.cleanup();service.store.expire_pending()
            if child and child.poll() is None:
                with service.store.connect() as db:
                    overdue=db.execute("SELECT 1 FROM jobs WHERE state='running' AND started<?",(now-45,)).fetchone()
                try:
                    worker=json.loads((root/'worker-state.json').read_text())
                    ready=worker.get('run_id')==run_id and worker.get('state') in ('ready','working')
                    overdue=overdue or (ready and worker.get('state')=='working' and now-worker['started']>45)
                except (OSError,ValueError,KeyError,TypeError):ready=False
                if overdue or (not ready and now-started>120):
                    kill();service.store.fail_running('识别超时，请重新上传');state('restarting',run_id)
            if child is None or child.poll() is not None:
                if child is not None:service.store.fail_running('识别进程已退出，请重试')
                while recent and recent[0]<now-300:recent.popleft()
                if len(recent)>=3:
                    state('unavailable',run_id);time.sleep(.5);continue
                recent.append(now);run_id=secrets.token_hex(8);started=now
                child=subprocess.Popen([sys.executable,'-B','-m','backend.map_ocr_worker','--config',str(args.config),'--run-id',run_id],
                                       cwd=ROOT,stdin=subprocess.DEVNULL)
            state('running',run_id);time.sleep(.5)
    finally:
        kill();service.store.fail_pending('识别服务已停止，请重试');state('stopped',run_id);lock.close()

if __name__=='__main__':main()
