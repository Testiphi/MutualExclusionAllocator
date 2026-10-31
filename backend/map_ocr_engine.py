"""CPU-only OCR adapter. Imported/instantiated only by an isolated worker."""
from pathlib import Path
import hashlib
import socket
import sys


class MapOcrEngine:
    def __init__(self,config):
        def deny(*args,**kwargs):raise RuntimeError('Offline OCR cannot connect to a network')
        socket.socket.connect=deny;socket.socket.connect_ex=deny;socket.create_connection=deny
        if config.get('vendor'):sys.path.insert(0,str(Path(config['vendor']).resolve()))
        from rapidocr import RapidOCR
        from rapidocr.utils.typings import OCRVersion,ModelType
        paths={}
        for key,item in config['models'].items():
            path=Path(item['path']).resolve()
            if hashlib.sha256(path.read_bytes()).hexdigest()!=item['sha256']:raise ValueError('模型校验失败: '+key)
            paths[key]=str(path)
        self.engine=RapidOCR(params={'Global.use_cls':False,'Global.log_level':'error',
            'Global.model_root_dir':str(Path(paths['det']).parent),
            'Det.model_path':paths['det'],'Rec.model_path':paths['rec'],'Rec.rec_keys_path':paths['keys'],
            'Det.ocr_version':OCRVersion.PPOCRV5,'Rec.ocr_version':OCRVersion.PPOCRV5,
            'Det.model_type':ModelType.MOBILE,'Rec.model_type':ModelType.MOBILE,
            'Det.limit_side_len':1280,'Det.limit_type':'max',
            'EngineConfig.onnxruntime.use_cuda':False,'EngineConfig.onnxruntime.use_dml':False,
            'EngineConfig.onnxruntime.intra_op_num_threads':2,'EngineConfig.onnxruntime.inter_op_num_threads':1})
        self.engine._load_det_model();self.engine._load_rec_model()

    def recognize(self,raw):
        import cv2
        import numpy as np
        image=cv2.imdecode(np.frombuffer(raw,dtype=np.uint8),cv2.IMREAD_COLOR)
        if image is None:raise ValueError('图片解码失败')
        h,w=image.shape[:2]
        working=image if w>=1280 else cv2.resize(image,(1280,round(h*1280/w)),interpolation=cv2.INTER_CUBIC)
        wh,ww=working.shape[:2];sx,sy=w/ww,h/wh
        output=self.engine(working,use_det=True,use_cls=False,use_rec=True);rows=[]
        for box,text,score in zip(output.boxes if output.boxes is not None else [],output.txts or [],output.scores or []):
            points=np.asarray(box)*np.array([sx,sy]);lo,hi=points.min(axis=0),points.max(axis=0)
            rows.append({'text':text,'confidence':float(score),
                         'box':[float(lo[0]),float(lo[1]),float(hi[0]-lo[0]),float(hi[1]-lo[1])]})
        return (w,h),rows
