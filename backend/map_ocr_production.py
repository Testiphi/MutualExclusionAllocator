"""Explicit, private OCR queue provisioning. Never initializes business databases."""
from pathlib import Path
import argparse
import json
import os
import stat
import time
from backend.map_recognition import JobStore,RecognitionError,digest

ROOT=Path(__file__).resolve().parents[1]
KIND='racepick-map-recognition-production-v1'

def settings(path):
    path=Path(path).absolute()
    if path.is_symlink() or path.resolve()!=path:raise ValueError('识图配置不能为链接')
    data=json.loads(path.read_text(encoding='utf-8'))
    if set(data)!={'kind','root'} or data['kind']!=KIND:raise ValueError('识图配置字段不正确')
    root=Path(data['root'])
    if not root.is_absolute() or root.resolve()!=root or root.is_relative_to(ROOT) or path!=root/'config.json':
        raise ValueError('识图必须使用发布目录之外的独立状态目录')
    if any((root/name).exists() for name in ('accounts.sqlite3','production.json','score-state','global-score-state')):
        raise ValueError('识图状态禁止包含正式业务库')
    if os.name=='posix' and (stat.S_IMODE(root.stat().st_mode)&0o077 or stat.S_IMODE(path.stat().st_mode)&0o077):
        raise ValueError('识图目录及配置必须为私有权限')
    if os.name=='posix' and (root.stat().st_uid!=os.geteuid() or path.stat().st_uid!=os.geteuid()):
        raise ValueError('识图目录及配置必须属于运行服务用户')
    return root

def provision(root):
    root=Path(root).absolute()
    if root.resolve()!=root or root.is_relative_to(ROOT) or root.exists():raise ValueError('仅接受发布目录之外的新建空目标')
    if not root.parent.is_dir():raise ValueError('请先核验并建立父目录')
    root.mkdir(mode=0o700)
    for name,value in [('queue.json',{'kind':'racepick-map-queue-v1'}),('config.json',{'kind':KIND,'root':str(root)})]:
        path=root/name
        with path.open('x',encoding='utf-8') as stream:json.dump(value,stream)
        if os.name=='posix':path.chmod(0o600)
    JobStore(root,production=True)
    if os.name=='posix':
        (root/'media').chmod(0o700)
        for path in root.glob('*.sqlite3*'):path.chmod(0o600)
    return root/'config.json'

class ProductionRecognitionService:
    production=True
    def __init__(self,path,catalog_provider=None):
        self.config_path=Path(path).absolute();self.root=settings(path)
        self.config=json.loads(self.config_path.read_text(encoding='utf-8'));self.provider=catalog_provider
        self.store=JobStore(self.root,production=True)
        manifest=json.loads((ROOT/'production/ocr-models.json').read_text(encoding='utf-8'))
        self.config['models']={key:{**item,'path':str(ROOT/item['path'])} for key,item in manifest['models'].items()}
        self.config['vendor']=None

    def catalog(self,server):
        if server not in ('cn','global'):raise RecognitionError(422,'请选择国服或国际服')
        if self.provider is None:raise RecognitionError(503,'识图目录尚未绑定活动成绩')
        return self.provider(server)

    def start(self):pass # Exactly one external systemd supervisor owns the worker.
    def stop(self):pass

    def health(self):
        try:
            state=json.loads((self.root/'supervisor-state.json').read_text())
            worker=json.loads((self.root/'worker-state.json').read_text())
            fresh=0<=time.time()-state['updated']<5
            return 'ready' if fresh and state['state']=='running' and worker['state'] in ('ready','working') and state['run_id']==worker['run_id'] else 'unavailable'
        except (OSError,ValueError,KeyError,TypeError):return 'unavailable'

def worker_service(path):
    data=json.loads(Path(path).read_text(encoding='utf-8'))
    if data.get('kind')==KIND:return ProductionRecognitionService(path)
    from backend.map_recognition import RecognitionService
    return RecognitionService(path)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=['provision','check'])
    parser.add_argument('--state-dir',type=Path,required=True)
    args=parser.parse_args()
    path=provision(args.state_dir) if args.command=='provision' else args.state_dir/'config.json'
    service=ProductionRecognitionService(path)
    print(json.dumps({'root':str(service.root),'worker':service.health(),'business_database_initialized':False}))

if __name__=='__main__':main()
