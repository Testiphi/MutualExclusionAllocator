"""Compose existing features and OCR in a NEW, isolated localhost review sandbox."""
from pathlib import Path
import argparse
import json
import os
import socket
import sys

REPO=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(REPO))

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--demo-config',type=Path,required=True)
    parser.add_argument('--port',type=int,default=8032)
    args=parser.parse_args()
    if not 1024<=args.port<=65535:parser.error('端口不合法')
    with socket.socket() as probe:probe.bind(('127.0.0.1',args.port))
    from backend.map_recognition import RecognitionService,digest
    # Read frozen public inputs only; never copy the demo's accounts or uploaded media.
    source=RecognitionService(args.demo_config)
    source.catalog('cn');source.catalog('global')
    contents={name:(source.reference/name).read_bytes() for name in source.config['reference_sha256']}
    for name,raw in contents.items():
        if digest(raw)!=source.config['reference_sha256'][name]:raise ValueError('冻结数据校验失败')
    from backend.score_repository import provision
    root=provision(source.reference)
    (root/'reference').mkdir()
    for name,raw in contents.items():(root/'reference'/name).write_bytes(raw)
    (root/'.racepick-map-demo.json').write_text(json.dumps({'kind':'racepick-local-map-recognition','schema':1}),encoding='utf-8')
    config={**source.config,'root':str(root),'reference':str(root/'reference'),'examples':{}}
    config_path=root/'config.json'
    config_path.write_text(json.dumps(config,ensure_ascii=False,indent=2),encoding='utf-8')
    from backend.app import create_app
    from backend.mailing import MailConfig
    app=create_app(data_dir=root/'accounts',origin=f'http://127.0.0.1:{args.port}',
                   score_version_lab=root,map_recognition=config_path,contributions=True,
                   coverage=True,feedback=True,notifications=True,usage=True,mail_config=MailConfig())
    receipt={'pid':os.getpid(),'origin':f'http://127.0.0.1:{args.port}',
             'state_directory':str(root),'production':False,'public_data_archive_sha256':config['source_archive_sha256'],
             'features':['coverage','contributions','feedback','notifications','usage','map_recognition'],
             'accounts_imported':False,'examples_exposed':False}
    (root/'review-receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(receipt,ensure_ascii=False),flush=True)
    import uvicorn
    uvicorn.run(app,host='127.0.0.1',port=args.port,proxy_headers=False)

if __name__=='__main__':main()
