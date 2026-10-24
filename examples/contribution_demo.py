"""Create a NEW disposable contribution demo; never opens an existing account database."""
import json
import sys
from pathlib import Path as _RepoPath
sys.path.insert(0, str(_RepoPath(__file__).resolve().parents[1]))
from pathlib import Path
import secrets
import tempfile
from urllib.parse import urlsplit, parse_qs
from fastapi.testclient import TestClient
from backend.app import create_app
from backend.roles import set_role
from backend.score_repository import provision

ROOT = Path(__file__).resolve().parents[1]


def prepare(feedback=False, port=8009):
    with tempfile.TemporaryDirectory() as temporary:
        seed = Path(temporary)
        (seed/'cars.json').write_bytes((ROOT/'cars.json').read_bytes())
        data = {'_version': 1, 'tracks': [{'大地图': '排行榜验收', '小地图': '独立测试赛道',
            '五区': {'理论': [], '高手': [{'cars': [{'name': '恶魔', 'stars': 6}], 'time': 25}], '普通': [{'cars': [{'name': '恶魔', 'stars': 6}]}], '自动': []},
            '四区': {'理论': [], '高手': [], '普通': [], '自动': []}}]}
        (seed/'gauntlet_data.json').write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')
        lab = provision(seed)
    app = create_app(lab/'accounts', score_version_lab=lab, contributions=True, feedback=feedback)
    password = 'Demo-'+secrets.token_urlsafe(16)
    clients = []

    def checked(response):
        if response.status_code != 200:
            raise RuntimeError(f'{response.status_code}: {response.text}')
        return response.json()

    def new_client():
        c = TestClient(app, base_url='http://127.0.0.1:8000'); clients.append(c)
        c.headers.update({'Origin': 'http://127.0.0.1:8000', 'X-CSRF-Token': checked(c.get('/api/auth/me'))['csrf']})
        return c

    def login(c, email):
        c.cookies.clear(); c.headers['X-CSRF-Token'] = checked(c.get('/api/auth/me'))['csrf']
        result = checked(c.post('/api/auth/login', json={'email': email, 'password': password}))
        c.headers.update({'X-CSRF-Token': result['csrf'], 'X-Account-ID': result['user']['id']})

    def signup(email):
        c = new_client()
        checked(c.post('/api/auth/register', json={'email': email, 'password': password}))
        messages = [json.loads(p.read_text(encoding='utf-8')) for p in (lab/'accounts/outbox').glob('*.json')]
        mail = next(m for m in messages if m['to'] == email and m['purpose'] == 'verify')
        token = parse_qs(urlsplit(mail['url']).fragment)['token'][0]
        checked(c.post('/api/auth/verify-email', json={'token': token})); login(c, email)
        return c

    owner = signup('owner@example.test'); set_role(lab/'accounts', 'owner@example.test', 'superadmin'); login(owner, 'owner@example.test')
    reviewer = signup('reviewer@example.test'); set_role(lab/'accounts', 'reviewer@example.test', 'admin'); login(reviewer, 'reviewer@example.test')
    player = signup('player@example.test')
    checked(player.put('/api/contributions/preferences', json={'revision': 0, 'nickname': '山路补图员', 'anonymous': False}))
    records = []
    for stars, value, action, points in [(5, '26', 'accept', 9), (4, '27', 'ignore', 8), (3, '28', 'pending', None)]:
        entry = {'big': '排行榜验收', 'small': '独立测试赛道', 'zone': '五区', 'tier': '高手', 'car': '恶魔', 'stars': stars, 'time': value, 'notes': '明确标记的本地模拟成绩，仅用于验收', 'route': ''}
        sid = checked(player.post('/api/submissions', json={'request_key': secrets.token_hex(16), 'entries': [entry]}))['ids'][0]
        checked(player.post('/api/submissions/'+sid+'/submit', json={'revision': 1}))
        if action != 'pending':
            body = {'revision': 2, 'action': action, 'reason': '独立测试示例：证据可核验', 'quality': {'completeness': 3, 'evidence': points-5, 'value': 2, 'reason': '模拟证据，用于检验计分过程'}}
            if action == 'accept':
                preview = checked(owner.post('/api/admin/submissions/'+sid+'/preview', json={'revision': 2, 'entry': entry}))
                body.update(entry=preview['candidate'], basis=preview['basis'])
            checked(owner.post('/api/admin/submissions/'+sid+'/review', json=body))
        records.append({'id': sid, 'stars': stars, 'status': action})
    for c in clients: c.close()
    (lab/'LOGIN.txt').write_text('仅本地隔离验收，非原账号。\n超级管理员：owner@example.test\n审核管理员：reviewer@example.test\n投稿玩家：player@example.test\n共同测试密码：'+password+'\n', encoding='utf-8')
    (lab/'acceptance.json').write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding='utf-8')
    print(lab)
    print('Login details: '+str(lab/'LOGIN.txt'))
    print(f'python -m backend.app --port {port} --data-dir "{lab / "accounts"}" --score-version-lab "{lab}" --contributions{" --feedback" if feedback else ""}')
    return lab


if __name__ == '__main__': prepare()
