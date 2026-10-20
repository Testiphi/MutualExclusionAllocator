"""Explicit disposable lab provisioning; never copy or replace user workbooks/accounts."""
import argparse
import json
import secrets
from pathlib import Path
from export_xlsx import build_workbook
from backend.previews import ROOT, sha

LABS=ROOT/'.local-writeback-labs'
FILES=('gauntlet_data.json','gauntlet_data.xlsx','gauntlet_data_shared.xlsx')

def provision(source):
    source=Path(source).resolve()
    raw=(source/'gauntlet_data.json').read_bytes();cars=(source/'cars.json').read_bytes()
    data=json.loads(raw.decode('utf-8-sig'))
    lab=LABS/secrets.token_hex(12);lab.mkdir(parents=True)
    (lab/'data').mkdir();(lab/'accounts').mkdir();(lab/'batches').mkdir()
    (lab/'data/gauntlet_data.json').write_bytes(raw);(lab/'data/cars.json').write_bytes(cars)
    for name in FILES[1:]:
        book,_=build_workbook(data['tracks'])
        try:book.save(lab/'data'/name)
        finally:book.close()
    marker={'kind':'racepick-disposable-writeback-lab-v1','id':lab.name,'baseline':{n:sha((lab/'data'/n).read_bytes()) for n in FILES},'origin':str(source)}
    (lab/'lab.json').write_text(json.dumps(marker,ensure_ascii=False,indent=2),encoding='utf-8')
    return lab

def validate_lab(path,data_dir=None,source=None):
    lab=Path(path).absolute()
    # A root under a fixed ignored directory, with no junctions/symlinks/hard-linked files.
    if lab.parent!=LABS or lab.resolve()!=lab:raise ValueError('写回仅允许专用测试目录')
    for p in (LABS,lab,lab/'data',lab/'accounts',lab/'batches'):
        if p.is_symlink() or (hasattr(p,'is_junction') and p.is_junction()) or p.resolve()!=p:raise ValueError('测试目录不能包含链接')
    marker=json.loads((lab/'lab.json').read_text(encoding='utf-8'))
    if marker.get('kind')!='racepick-disposable-writeback-lab-v1' or marker.get('id')!=lab.name:raise ValueError('缺少有效测试环境标记')
    if data_dir is not None and Path(data_dir).resolve()!=lab/'accounts':raise ValueError('必须使用测试环境独立账号库')
    if source is not None and Path(source).resolve()!=lab/'data':raise ValueError('必须使用测试环境独立成绩库')
    for p in lab.rglob('*'):
        if p.is_symlink() or (hasattr(p,'is_junction') and p.is_junction()) or p.resolve()!=p or (p.is_file() and p.stat().st_nlink!=1):raise ValueError('测试环境文件不能链接到外部')
    return lab,marker

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--source',type=Path,required=True)
    print(provision(parser.parse_args().source))
