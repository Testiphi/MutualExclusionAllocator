"""New isolated real-workflow acceptance lab; all accounts, scores and reviews fictional."""
import json
from pathlib import Path
import secrets
import sys
import tempfile
from urllib.parse import urlsplit,parse_qs
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from fastapi.testclient import TestClient
from backend.app import create_app
from backend.roles import set_role
from backend.score_repository import provision

ROOT=Path(__file__).resolve().parents[1]

def main():
    tracks=[]
    for i in range(3):
        tracks.append({'大地图':'覆盖表验收'+str(i+1),'小地图':'示例赛道','has_special_route':True,'special_route_note':'跳图',
          '五区':{'理论':[{'cars':[{'name':'恶魔'}],'time':25+i},{'cars':[{'name':'杰哥'}],'time':26+i},{'cars':[{'name':'杰哥'}],'time':22+i,'sc':True,'sc_type':'跳图'}],
                 '高手':[{'cars':[{'name':'恶魔','stars':6}],'time':25.5+i}],'普通':[{'cars':[{'name':'恶魔','stars':6}]}],'自动':[]},
          '四区':{'理论':[{'cars':[{'name':'恶魔'}],'time':29+i}],'高手':[],'普通':[],'自动':[]}})
    for track in tracks:track['五区']['理论'].sort(key=lambda e:e['time'])
    with tempfile.TemporaryDirectory() as temporary:
        seed=Path(temporary);(seed/'cars.json').write_bytes((ROOT/'cars.json').read_bytes());(seed/'gauntlet_data.json').write_text(json.dumps({'_version':2,'tracks':tracks},ensure_ascii=False),encoding='utf-8');lab=provision(seed)
    app=create_app(lab/'accounts',score_version_lab=lab,contributions=True,feedback=True,notifications=True,coverage=True)
    password='Demo-'+secrets.token_urlsafe(16)
    def checked(r):
        if r.status_code!=200:raise RuntimeError(str(r.status_code)+':'+r.text)
        return r.json()
    def client():
        c=TestClient(app,base_url='http://127.0.0.1:8000');c.headers.update({'Origin':'http://127.0.0.1:8000','X-CSRF-Token':checked(c.get('/api/auth/me'))['csrf']});return c
    def login(c,email):
        c.cookies.clear();c.headers['X-CSRF-Token']=checked(c.get('/api/auth/me'))['csrf'];r=checked(c.post('/api/auth/login',json={'email':email,'password':password}));c.headers.update({'X-CSRF-Token':r['csrf'],'X-Account-ID':r['user']['id']})
    def signup(email):
        c=client();checked(c.post('/api/auth/register',json={'email':email,'password':password}));messages=[json.loads(p.read_text(encoding='utf-8')) for p in (lab/'accounts/outbox').glob('*.json')];mail=next(m for m in messages if m['to']==email and m['purpose']=='verify');token=parse_qs(urlsplit(mail['url']).fragment)['token'][0];checked(c.post('/api/auth/verify-email',json={'token':token}));login(c,email);return c
    owner=signup('owner@example.test');set_role(lab/'accounts','owner@example.test','superadmin');login(owner,'owner@example.test')
    players=[]
    for email,count in [('player@example.test',0),('first@example.test',5),('full@example.test',15)]:
        c=signup(email);players.append(c)
        targets=[(t,car,star) for t in tracks for car in ['恶魔','杰哥','r兔'] for star in [5,6]]
        for t,car,star in targets[:count]:
            entry={'big':t['大地图'],'small':t['小地图'],'zone':'五区','tier':'高手','car':car,'stars':star,'time':'30','route':'','notes':'虚构验收投稿，不代表真实成绩'}
            sid=checked(c.post('/api/submissions',json={'request_key':secrets.token_hex(16),'entries':[entry]}))['ids'][0];checked(c.post('/api/submissions/'+sid+'/submit',json={'revision':1}))
            checked(owner.post('/api/admin/submissions/'+sid+'/review',json={'revision':2,'action':'ignore','reason':'本地虚构评分，仅验收解锁，不写正式成绩','quality':{'completeness':3,'evidence':4,'value':3,'reason':'本地虚构评分，仅验收解锁，不写正式成绩'}}))
    for c in [owner,*players]:c.close()
    (lab/'LOGIN.txt').write_text('仅新建本地验收环境，全部为虚构账号。\n主号：owner@example.test\n未解锁：player@example.test\n一级待选：first@example.test\n二级：full@example.test\n共同测试密码：'+password+'\n',encoding='utf-8')
    print('NEW coverage workflow lab: '+str(lab));print('Login details: '+str(lab/'LOGIN.txt'))
    print(f'python -B -X utf8 -m backend.app --port 8023 --data-dir "{lab / "accounts"}" --score-version-lab "{lab}" --contributions --feedback --notifications --coverage')
    return lab

if __name__=='__main__':main()
