"""Start an isolated localhost RacePick screenshot-recognition demo.

Only approved public JSON and selected private example copies are staged.
No workbook, production account DB, score-state or existing demo is overwritten.
"""
from pathlib import Path
import argparse
import hashlib
import io
import json
import os
import socket
import sys
import zipfile

REPO=Path(__file__).resolve().parents[1]
WORKSPACE=REPO.parent
sys.path.insert(0,str(REPO))
RUNTIME=('cars.json','gauntlet_data.json','cars.global.json','gauntlet_data.global.json','global-data-manifest.json')
ARCHIVE_SHA='34d11ecaa1a23dc3e9225f8838b209a611ac178c551152cf23007b302eabbf35'


def sha(raw):return hashlib.sha256(raw).hexdigest()


def prepare(root):
    config_path=root/'config.json'
    if root.exists():
        if not config_path.is_file():raise ValueError('目标目录已存在且不是本demo，拒绝覆盖')
        from backend.map_recognition import RecognitionService
        service=RecognitionService(config_path)
        if service.root!=root.resolve():raise ValueError('demo目录不匹配')
        for name,digest in service.config['reference_sha256'].items():
            if sha((service.reference/name).read_bytes())!=digest:raise ValueError('已有冻结来源变化，拒绝覆盖')
        return config_path
    archive=WORKSPACE/'repo/.production-build/RacePick-Global659-Compat-20261030-3d978fd3-delivery.zip'
    raw=archive.read_bytes()
    if sha(raw)!=ARCHIVE_SHA:raise ValueError('批准数据来源归档SHA不一致')
    with zipfile.ZipFile(io.BytesIO(raw)) as outer:
        inner=outer.read('delivery-20261030-global659-compat/racepick-accounts-release.zip')
    with zipfile.ZipFile(io.BytesIO(inner)) as bundle:
        manifest=json.loads(bundle.read('manifest.json'));data={n:bundle.read(n) for n in RUNTIME}
        for name,content in data.items():
            expected=manifest['files'][name]
            if sha(content)!=expected['sha256'] or len(content)!=expected['size']:raise ValueError('冻结JSON校验失败')
    base=WORKSPACE/'offline-evaluation/maps-20261031-01'
    model_manifest=json.loads((base/'models/manifest.json').read_text(encoding='utf-8'))
    models={}
    for key,name in [('det','ma9_v5_det.onnx'),('rec','ma9_v5_rec.onnx'),('keys','ma9_v5_keys.txt')]:
        item=next(x for x in model_manifest if x['name']==name)
        if sha(Path(item['path']).read_bytes())!=item['sha256']:raise ValueError('模型来源校验失败')
        models[key]={'path':item['path'],'sha256':item['sha256']}
    old=json.loads((base/'samples/manifest.json').read_text(encoding='utf-8'))
    new=json.loads((WORKSPACE/'offline-evaluation/maps-20261031-02/samples/manifest.json').read_text(encoding='utf-8'))
    examples={}
    selections=[('gray_button','灰按钮资格赛',next(x for x in new if x['id']=='img_46df9d4aa089')),
                ('challenge','平板挑战页',next(x for x in new if x['id']=='img_302da0ae6b1c')),
                ('results','五卡结果页',next(x for x in new if x['id']=='img_c470f68eb77c')),
                ('low_resolution','低清截图（手动补充）',next(x for x in old if x['id']=='defense01__down640'))]
    for key,title,item in selections:
        p=Path(item['path']);p=p if p.is_absolute() else base/p
        content=p.read_bytes()
        if sha(content)!=item['sha256']:raise ValueError('样例来源校验失败')
        from PIL import Image
        with Image.open(io.BytesIO(content)) as image:format_name=image.format
        suffix={'PNG':'.png','JPEG':'.jpg','WEBP':'.webp'}[format_name]
        examples[key]={'title':title,'filename':key+suffix,'sha256':sha(content),'content':content}
    root.mkdir(parents=True,exist_ok=False)
    (root/'.racepick-map-demo.json').write_text(json.dumps({'kind':'racepick-local-map-recognition','schema':1}),encoding='utf-8')
    (root/'reference').mkdir();(root/'examples').mkdir()
    for name,content in data.items():(root/'reference'/name).write_bytes(content)
    for example in examples.values():(root/'examples'/example['filename']).write_bytes(example.pop('content'))
    config={'root':str(root.resolve()),'reference':str((root/'reference').resolve()),'models':models,
            'vendor':str((base/'vendor').resolve()),'reference_sha256':{n:sha(v) for n,v in data.items()},
            'examples':examples,'source_archive':str(archive),'source_archive_sha256':ARCHIVE_SHA,
            'release_id':'3d978fd30812fa8f72ba928d','local_only':True}
    config_path.write_text(json.dumps(config,ensure_ascii=False,indent=2),encoding='utf-8')
    return config_path


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--state-dir',type=Path,required=True);p.add_argument('--port',type=int,default=8031)
    args=p.parse_args()
    if not 1024<=args.port<=65535:p.error('请选择1024–65535端口')
    with socket.socket() as probe:probe.bind(('127.0.0.1',args.port))
    root=args.state_dir.resolve();config=prepare(root)
    (root/'server-receipt.json').write_text(json.dumps({'pid':os.getpid(),'origin':f'http://127.0.0.1:{args.port}',
        'source_commit_base':'4eef340f6481fcc3f08de2ca5b2900e126368ee6','data_release':'3d978fd30812fa8f72ba928d',
        'production':False,'state_directory':str(root)},indent=2),encoding='utf-8')
    from backend.app import create_app
    import uvicorn
    app=create_app(data_dir=root/'accounts',origin=f'http://127.0.0.1:{args.port}',map_recognition=config)
    print('本地截图选图demo：http://127.0.0.1:'+str(args.port)+'/',flush=True)
    print('独立状态目录：'+str(root)+'；游客可识别，无需注册或登录。',flush=True)
    uvicorn.run(app,host='127.0.0.1',port=args.port,proxy_headers=False)


if __name__=='__main__':main()
