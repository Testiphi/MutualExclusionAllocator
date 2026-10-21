"""Append-only score versions in an explicitly provisioned local sandbox."""
from contextlib import contextmanager
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import tempfile
import time
from validate_data import validate_data

ROOT=Path(__file__).resolve().parents[1]
LABS=ROOT.parent/'.score-version-sandboxes'
FILES=('gauntlet_data.json','cars.json')
def digest(raw):return hashlib.sha256(raw).hexdigest()
def encode(value):return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)
def sync_dir(path):
    if os.name=='posix':
        fd=os.open(path,os.O_RDONLY|os.O_DIRECTORY)
        try:os.fsync(fd)
        finally:os.close(fd)
def write_new(path,raw):
    with path.open('xb') as stream:stream.write(raw);stream.flush();os.fsync(stream.fileno())

def validate_lab(path,accounts=None):
    path=Path(path).absolute()
    if path.parent!=LABS or path.resolve()!=path:raise ValueError('只允许专门创建的数据版本测试目录')
    for part in (LABS,path,path/'accounts',path/'scores',path/'scores/versions',path/'backups'):
        if not part.is_dir() or part.is_symlink() or (hasattr(part,'is_junction') and part.is_junction()) or part.resolve()!=part:raise ValueError('实验室目录不存在或包含链接')
    for part in path.rglob('*'):
        if part.is_symlink() or (hasattr(part,'is_junction') and part.is_junction()) or part.resolve()!=part or (part.is_file() and part.stat().st_nlink!=1):raise ValueError('实验室不允许符号链接或硬链接')
    marker=json.loads((path/'lab.json').read_text(encoding='utf-8'))
    if marker.get('kind')!='racepick-score-versions-lab-v1' or marker.get('id')!=path.name:raise ValueError('测试环境标记无效')
    if accounts is not None and Path(accounts).resolve()!=path/'accounts':raise ValueError('必须使用独立测试账号库')
    return path,marker

def validate_production_root(path,accounts):
    accounts=Path(accounts).absolute();path=Path(path).absolute()
    if accounts.resolve()!=accounts or path!=accounts/'score-state' or path.resolve()!=path:raise ValueError('生产成绩必须使用账号数据目录下的score-state')
    account_marker=json.loads((accounts/'production.json').read_text(encoding='utf-8'))
    if account_marker.get('kind')!='racepick-production-v1':raise ValueError('缺少生产账号库标记')
    for part in (accounts,path,path/'scores',path/'scores/versions',path/'backups'):
        if not part.is_dir() or part.is_symlink() or part.resolve()!=part:raise ValueError('生产成绩目录不存在或包含链接')
    for part in path.rglob('*'):
        if part.is_symlink() or part.resolve()!=part or (part.is_file() and part.stat().st_nlink!=1):raise ValueError('生产成绩目录不能含链接')
    marker=json.loads((path/'production-scores.json').read_text(encoding='utf-8'))
    if marker.get('kind')!='racepick-score-production-v1' or marker.get('account_marker')!=account_marker:raise ValueError('生产成绩与账号库标记不匹配')
    return path,marker

class Versions:
    def __init__(self,lab,validator=None):
        self.lab=Path(lab);self.root=self.lab/'scores/versions';self.validator=validator or validate_lab
    def create(self,contents,parent,kind,batch=None):
        data=json.loads(contents['gauntlet_data.json']);cars=json.loads(contents['cars.json'])
        errors,_=validate_data(data,cars)
        if errors:raise ValueError('数据校验失败：'+'；'.join(errors[:10]))
        body={'schema':1,'parent':parent,'kind':kind,'batch':batch,'created_at':int(time.time()),'nonce':secrets.token_hex(16),
              'files':{name:digest(contents[name]) for name in FILES}}
        identity=digest(encode(body).encode())[:32];body['id']=identity
        temporary=Path(tempfile.mkdtemp(prefix='.building-',dir=self.root))
        # Incomplete directories are never referenced by the active database pointer.
        for name in FILES:write_new(temporary/name,contents[name])
        write_new(temporary/'manifest.json',encode(body).encode());sync_dir(temporary)
        os.rename(temporary,self.root/identity);sync_dir(self.root)
        return identity
    def read(self,identity):
        if not re.fullmatch('[a-f0-9]{32}',identity):raise ValueError('数据版本ID无效')
        folder=self.root/identity
        if folder.is_symlink() or folder.resolve()!=folder:raise ValueError('版本路径异常')
        info=json.loads((folder/'manifest.json').read_text(encoding='utf-8'))
        if info.get('schema')!=1:raise ValueError('当前应用不支持此数据版本格式')
        identity_body={k:v for k,v in info.items() if k!='id'}
        if info.get('id')!=identity or digest(encode(identity_body).encode())[:32]!=identity:raise ValueError('版本清单校验失败')
        contents={n:(folder/n).read_bytes() for n in FILES}
        if any(digest(contents[n])!=info['files'][n] for n in FILES):raise ValueError('不可变数据版本被修改，拒绝使用')
        return info,contents
    @contextmanager
    def lock(self):
        self.validator(self.lab)
        with (self.lab/'maintenance.lock').open('a+b') as stream:
            if stream.tell()==0:stream.write(b'0');stream.flush()
            stream.seek(0)
            try:
                if os.name=='nt':
                    import msvcrt;msvcrt.locking(stream.fileno(),msvcrt.LK_NBLCK,1)
                else:
                    import fcntl;fcntl.flock(stream,fcntl.LOCK_EX|fcntl.LOCK_NB)
            except OSError:raise ValueError('已有维护操作执行中') from None
            try:yield
            finally:
                stream.seek(0)
                if os.name=='nt':msvcrt.locking(stream.fileno(),msvcrt.LK_UNLCK,1)
                else:fcntl.flock(stream,fcntl.LOCK_UN)

def provision(source):
    source=Path(source).resolve();contents={n:(source/n).read_bytes() for n in FILES}
    lab=LABS/secrets.token_hex(12);lab.mkdir(parents=True)
    for part in ('accounts','scores/versions','backups'):(lab/part).mkdir(parents=True)
    initial=Versions(lab).create(contents,None,'initial')
    marker={'kind':'racepick-score-versions-lab-v1','id':lab.name,'initial':initial,'cars_sha256':digest(contents['cars.json'])}
    write_new(lab/'lab.json',encode(marker).encode());return lab

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--source',type=Path,required=True)
    print(provision(parser.parse_args().source))
