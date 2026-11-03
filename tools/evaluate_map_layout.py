"""Offline fresh-image evaluation. Requires explicit local models and vendor.

No web API, MaaFramework, game controller, database or model auto-download.
"""
from pathlib import Path
import argparse
import hashlib
import json
import socket
import sys
import time

REPO=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(REPO))
sys.dont_write_bytecode=True
from backend.map_layout import parse_map_layout


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def deny(*args,**kwargs):raise RuntimeError('Network disabled during offline evaluation')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest',type=Path,required=True)
    parser.add_argument('--catalog',type=Path,required=True)
    parser.add_argument('--models',type=Path,required=True)
    parser.add_argument('--vendor',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--server',choices=['cn','global'],default='cn')
    args=parser.parse_args()
    if args.output.exists():raise ValueError('Refusing to overwrite previous results')
    samples=json.loads(args.manifest.read_text(encoding='utf-8'))
    for row in samples:
        if sha(row['path'])!=row['sha256']:raise ValueError('Input screenshot changed: '+row['id'])
    models=json.loads(args.models.read_text(encoding='utf-8'))
    chosen={}
    for item in models:
        if item['name'] in ('ma9_v5_det.onnx','ma9_v5_rec.onnx','ma9_v5_keys.txt'):
            if sha(item['path'])!=item['sha256']:raise ValueError('Model changed: '+item['name'])
            chosen[item['name']]=str(Path(item['path']).resolve())
    if len(chosen)!=3:raise ValueError('Explicit local v5 detector/recognizer/dictionary required')
    socket.socket.connect=deny;socket.socket.connect_ex=deny;socket.create_connection=deny
    sys.path.insert(0,str(args.vendor.resolve()))
    import cv2
    import numpy as np
    import onnxruntime
    import psutil
    from rapidocr import RapidOCR
    from rapidocr.utils.typings import OCRVersion,ModelType
    engine=RapidOCR(params={
        'Global.use_cls':False,'Global.log_level':'error',
        'Global.model_root_dir':str(Path(chosen['ma9_v5_det.onnx']).parent),
        'Det.model_path':chosen['ma9_v5_det.onnx'],'Rec.model_path':chosen['ma9_v5_rec.onnx'],
        'Rec.rec_keys_path':chosen['ma9_v5_keys.txt'],
        'Det.ocr_version':OCRVersion.PPOCRV5,'Rec.ocr_version':OCRVersion.PPOCRV5,
        'Det.model_type':ModelType.MOBILE,'Rec.model_type':ModelType.MOBILE,
        'Det.limit_side_len':1280,'Det.limit_type':'max',
        'EngineConfig.onnxruntime.intra_op_num_threads':2,'EngineConfig.onnxruntime.inter_op_num_threads':1})
    catalog=json.loads(args.catalog.read_text(encoding='utf-8'));version=sha(args.catalog)
    with args.output.open('x',encoding='utf-8') as stream:
        env=dict(type='environment',manifest_sha256=sha(args.manifest),catalog_sha256=version,
            parser_sha256=sha(REPO/'backend/map_layout.py'),runner_sha256=sha(__file__),
            models={k:sha(p) for k,p in chosen.items()},ort=onnxruntime.__version__,
            cpu_threads=2,detector_limit='max1280',ocr_scope='whole_image',minimum_ocr_width=1280,
            network_disabled=True,maa_imported=any(n=='maa' or n.startswith('maa.') for n in sys.modules),
            user_confirmation_required=True)
        stream.write(json.dumps(env)+'\n');stream.flush()
        for sample in samples:
            started=time.perf_counter()
            image=cv2.imdecode(np.fromfile(sample['path'],dtype=np.uint8),cv2.IMREAD_COLOR)
            if image is None:raise ValueError('Invalid frozen image: '+sample['id'])
            h,w=image.shape[:2]
            # Uniform upscaling helps screenshot small text; never stretch a
            # tablet to 16:9. Return boxes in ORIGINAL image coordinates.
            working=image if w>=1280 else cv2.resize(image,(1280,round(h*1280/w)),interpolation=cv2.INTER_CUBIC)
            wh,ww=working.shape[:2];sx,sy=w/ww,h/wh
            raw=engine(working,use_det=True,use_cls=False,use_rec=True)
            ocr=[]
            for box,text,score in zip(raw.boxes if raw.boxes is not None else [],raw.txts or [],raw.scores or []):
                points=np.asarray(box)*np.array([sx,sy]);lo,hi=points.min(axis=0),points.max(axis=0)
                ocr.append(dict(text=text,confidence=float(score),box=[float(lo[0]),float(lo[1]),float(hi[0]-lo[0]),float(hi[1]-lo[1])]))
            ocr_done=time.perf_counter()
            # Truth is deliberately not an argument to the parser.
            result=parse_map_layout((w,h),ocr,catalog,server=args.server,catalog_version=version)
            finished=time.perf_counter()
            truth=sample['expected_maps']
            pred=[(s['big'],s['small']) for s in result['slots']]
            exact=bool(truth and result['status']=='complete' and pred==[tuple(p) for p in truth])
            record=dict(id=sample['id'],batch=sample['batch'],kind=sample['kind'],group=sample['group'],
                scope=sample.get('scope'),positive=bool(truth),exact_five=exact,
                original_size=[w,h],ocr_working_size=[ww,wh],
                false_complete=bool(result['status']=='complete' and not exact),
                ocr_seconds=ocr_done-started,parser_seconds=finished-ocr_done,
                elapsed_seconds=finished-started,rss_mib=psutil.Process().memory_info().rss/1024**2,
                result=result,ocr=ocr)
            stream.write(json.dumps(record,ensure_ascii=False)+'\n');stream.flush()
            print(json.dumps(dict(id=sample['id'],status=result['status'],exact=exact,
                                 reason=result['reason']),ensure_ascii=False),flush=True)


if __name__=='__main__':main()
