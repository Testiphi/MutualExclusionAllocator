"""One local OCR worker; only its own private queue/files, no device/API calls."""
from pathlib import Path
import argparse
import json
import os
import time
import traceback
from backend.map_recognition import validate_image,digest
from backend.map_ocr_production import worker_service
from backend.map_layout import parse_map_layout


def main():
    p=argparse.ArgumentParser();p.add_argument('--config',type=Path,required=True);p.add_argument('--run-id',required=True)
    args=p.parse_args();service=worker_service(args.config);root=service.root
    lock=(root/'worker.lock').open('a+b')
    if os.name=='nt':
        import msvcrt
        lock.seek(0);lock.write(b'0');lock.flush();lock.seek(0);msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
    else:
        import fcntl
        fcntl.flock(lock.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)

    def state(value,**extra):
        temp=root/('worker-state-'+args.run_id+'.tmp')
        temp.write_text(json.dumps({'state':value,'run_id':args.run_id,'pid':os.getpid(),**extra}),encoding='utf-8')
        os.replace(temp,root/'worker-state.json')

    state('starting')
    try:
        from backend.map_ocr_engine import MapOcrEngine
        engine=MapOcrEngine(service.config);state('ready')
        while not (root/('stop-'+args.run_id)).exists():
            job=service.store.claim()
            if job is None:time.sleep(.20);continue
            started=time.monotonic()
            state('working',started=time.time(),job_id=job['id'])
            try:
                catalog=json.loads(job['catalog']) if job.get('catalog') else service.catalog(job['server'])
                if catalog['version']!=job['version']:raise ValueError('任务目录版本已变化')
                raw=service.store.image_path(job['id']).read_bytes()
                if digest(raw)!=job['image_sha']:raise ValueError('图片校验不一致')
                validate_image(raw,job['mime'])
                size,rows=engine.recognize(raw)
                result=parse_map_layout(size,rows,catalog['maps'],server=job['server'],catalog_version=job['version'])
                service.store.finish(job['id'],result=result)
                print(json.dumps({'job':job['id'],'state':'succeeded','seconds':round(time.monotonic()-started,3)}),flush=True)
            except Exception:
                traceback.print_exc()
                service.store.finish(job['id'],error='图片识别失败，请重新上传原图；也可继续手动选图')
            finally:state('ready')
        state('stopped')
    except Exception:
        state('unavailable');service.store.fail_pending('识别模型未能启动，请重新启动本地demo')
        raise
    finally:lock.close()


if __name__=='__main__':main()
