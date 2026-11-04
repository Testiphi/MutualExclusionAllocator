"""Reproduce crcmod's upstream-supported pure Python fallback without a compiler."""
import argparse
import base64
import csv
import hashlib
import io
from pathlib import Path
import tarfile
import zipfile


def build(source,expected,output):
    raw=Path(source).read_bytes()
    if hashlib.sha256(raw).hexdigest()!=expected:raise ValueError('Upstream source SHA mismatch')
    with tarfile.open(fileobj=io.BytesIO(raw)) as archive:
        prefix='crcmod-1.7/python3/crcmod/'
        files={'crcmod/'+m.name[len(prefix):]:archive.extractfile(m).read() for m in archive.getmembers()
               if m.name.startswith(prefix) and m.isfile() and m.name.endswith('.py')}
        files['crcmod-1.7.dist-info/METADATA']=archive.extractfile('crcmod-1.7/PKG-INFO').read()
    files['crcmod-1.7.dist-info/WHEEL']=b'Wheel-Version: 1.0\nGenerator: RacePick-upstream-pure-fallback\nRoot-Is-Purelib: true\nTag: py3-none-any\n'
    text=io.StringIO(newline='');writer=csv.writer(text,lineterminator='\n')
    for name,value in sorted(files.items()):
        writer.writerow([name,'sha256='+base64.urlsafe_b64encode(hashlib.sha256(value).digest()).rstrip(b'=').decode(),len(value)])
    writer.writerow(['crcmod-1.7.dist-info/RECORD','',''])
    files['crcmod-1.7.dist-info/RECORD']=text.getvalue().encode()
    with zipfile.ZipFile(output,'x',zipfile.ZIP_DEFLATED) as z:
        for name,value in sorted(files.items()):
            info=zipfile.ZipInfo(name,(2026,1,1,0,0,0));info.create_system=0
            info.external_attr=0o600<<16;info.compress_type=zipfile.ZIP_DEFLATED
            z.writestr(info,value)
    return hashlib.sha256(Path(output).read_bytes()).hexdigest()


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',required=True,type=Path);parser.add_argument('--sha256',required=True)
    parser.add_argument('--output',required=True,type=Path);args=parser.parse_args()
    print(build(args.source,args.sha256,args.output))
