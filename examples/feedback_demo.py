"""Provision a NEW isolated feedback demo; never use an existing account directory."""
import json
import sys
from pathlib import Path as _RepoPath
sys.path.insert(0, str(_RepoPath(__file__).resolve().parents[1]))
import secrets
from fastapi.testclient import TestClient
from examples.contribution_demo import prepare
from backend.app import create_app


def main():
    lab = prepare(feedback=True, port=8010)
    password = (lab/'LOGIN.txt').read_text(encoding='utf-8').split('共同测试密码：',1)[1].strip()
    app = create_app(lab/'accounts', score_version_lab=lab, contributions=True, feedback=True)
    def client(email):
        c = TestClient(app, base_url='http://127.0.0.1:8000')
        session = c.get('/api/auth/me').json()
        c.headers.update({'Origin':'http://127.0.0.1:8000','X-CSRF-Token':session['csrf']})
        response = c.post('/api/auth/login',json={'email':email,'password':password})
        assert response.status_code == 200, response.text
        data=response.json();c.headers.update({'X-CSRF-Token':data['csrf'],'X-Account-ID':data['user']['id']})
        return c
    with client('player@example.test') as player, client('owner@example.test') as owner:
        ids=[]
        for title in ('手机上返回按钮显示异常（演示）','反馈界面体验建议（演示）'):
            response=player.post('/api/feedback',json={'request_key':secrets.token_hex(16),'category':'bug' if not ids else 'suggestion',
                'title':title,'description':'这是独立本地验收的模拟反馈，不代表线上真实问题。',
                'steps':'打开页面，查看顶部返回入口。','expected':'入口清晰且可点击','actual':'请按本轮设计验证','source_page':'/leaderboard'})
            assert response.status_code==200,response.text
            ids.append(response.json()['id'])
        response=owner.post('/api/admin/feedback/'+ids[1]+'/handle',json={'request_key':secrets.token_hex(16),'revision':1,'status':'needs_info','message':'演示回复：请补充希望优化的具体位置。'})
        assert response.status_code==200,response.text
    (lab/'feedback-acceptance.json').write_text(json.dumps({'pending':ids[0],'needs_info':ids[1]},indent=2),encoding='utf-8')
    print('Feedback demo seeded; two private examples; existing environments untouched.')


if __name__ == '__main__': main()
