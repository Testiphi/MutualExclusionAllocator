"""Create a new unread-demo lab with fictional data, never touch an existing lab."""
import json
import io
from contextlib import redirect_stdout
import secrets
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fastapi.testclient import TestClient
from examples.contribution_demo import prepare
from backend.app import create_app


def main():
    with redirect_stdout(io.StringIO()):
        lab = prepare(feedback=True, port=8016)
    password = (lab/'LOGIN.txt').read_text(encoding='utf-8').split('共同测试密码：',1)[1].strip()
    app = create_app(lab/'accounts',score_version_lab=lab,contributions=True,feedback=True,notifications=True)
    def checked(r):
        if r.status_code != 200: raise RuntimeError(r.text)
        return r.json()
    def login(email):
        c=TestClient(app,base_url='http://127.0.0.1:8000')
        c.headers.update({'Origin':'http://127.0.0.1:8000','X-CSRF-Token':checked(c.get('/api/auth/me'))['csrf']})
        session=checked(c.post('/api/auth/login',json={'email':email,'password':password}))
        c.headers.update({'X-CSRF-Token':session['csrf'],'X-Account-ID':session['user']['id']})
        return c
    with login('player@example.test') as player, login('owner@example.test') as owner:
        entry={'big':'排行榜验收','small':'独立测试赛道','zone':'五区','tier':'高手','car':'恶魔','stars':2,'time':'29',
               'notes':'新投稿未读演示，非真实成绩'}
        sid=checked(player.post('/api/submissions',json={'request_key':secrets.token_hex(16),'entries':[entry]}))['ids'][0]
        checked(player.post('/api/submissions/'+sid+'/submit',json={'revision':1}))
        # Produce an owner-visible review result on an older fictional record.
        old=json.loads((lab/'acceptance.json').read_text(encoding='utf-8'))[2]['id']
        checked(owner.post('/api/admin/submissions/'+old+'/review',json={'revision':2,'action':'needs_info','reason':'未读演示：请补充来源'}))
        tickets=[]
        for title in ('未读演示：待处理问题一','未读演示：待处理问题二','未读演示：已有站长回复'):
            tid=checked(player.post('/api/feedback',json={'request_key':secrets.token_hex(16),'category':'bug','title':title,
                'description':'独立本地虚构反馈，用于检查导航小圆点','source_page':'/'}))['id'];tickets.append(tid)
        checked(owner.post('/api/admin/feedback/'+tickets[2]+'/handle',json={'request_key':secrets.token_hex(16),
            'revision':1,'status':'needs_info','message':'演示回复：请补充截图或步骤。'}))
    (lab/'unread-acceptance.json').write_text(json.dumps({'new_submission':sid,'reviewed_submission':old,'feedback':tickets},indent=2),encoding='utf-8')
    print('NEW unread lab: '+str(lab))
    print('Login details: '+str(lab/'LOGIN.txt'))
    print(f'python -B -X utf8 -m backend.app --port 8016 --data-dir "{lab / "accounts"}" --score-version-lab "{lab}" --contributions --feedback --notifications')
    return lab


if __name__=='__main__': main()
