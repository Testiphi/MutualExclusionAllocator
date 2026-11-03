"""Explicit isolated native integration lab; never uses the existing 8033 state."""
from pathlib import Path
import argparse
import hashlib
import json
import secrets
import socket
from backend.app import ROOT, create_app
from backend.mini_auth import GuestStore, MiniError, load_config, provision as provision_guests
from backend.score_repository import provision as provision_scores, validate_lab


def create(source, receipt, model_config, accounts=False):
    source = Path(source).resolve()
    expected = json.loads(Path(receipt).read_text('utf-8'))['runtime']
    names = ('cars.json', 'gauntlet_data.json', 'cars.global.json', 'gauntlet_data.global.json', 'global-data-manifest.json')
    raw = {n: (source/n).read_bytes() for n in names}
    for n, value in raw.items():
        if hashlib.sha256(value).hexdigest() != expected[n]['sha256'] or len(value) != expected[n]['bytes']:
            raise ValueError('本地数据不匹配显式接收回执：'+n)
    models = json.loads(Path(model_config).read_text('utf-8'))
    for item in models['models'].values():
        if hashlib.sha256(Path(item['path']).read_bytes()).hexdigest() != item['sha256']:
            raise ValueError('模型来源SHA不匹配')
    lab = provision_scores(source)
    (lab/'reference').mkdir()
    for n, value in raw.items():
        (lab/'reference'/n).write_bytes(value)
    (lab/'.racepick-map-demo.json').write_text(json.dumps({'kind': 'racepick-local-map-recognition'}))
    config = {'root': str(lab), 'reference': str(lab/'reference'), 'reference_sha256': {n: hashlib.sha256(v).hexdigest() for n,v in raw.items()},
              'models': models['models'], 'vendor': models['vendor'], 'examples': {}, 'local_only': True}
    (lab/'config.json').write_text(json.dumps(config), encoding='utf-8')
    parent = ROOT.parent/'.mini-session-sandboxes'
    parent.mkdir(exist_ok=True)
    guests = provision_guests(parent/secrets.token_hex(12))
    result = {'lab': str(lab), 'guest_state': str(guests), 'data_unfrozen': True, 'production': False,
              'fixture_auth_only': True, 'runtime_sha256': config['reference_sha256']}
    if accounts:
        from backend.mini_accounts import provision as provision_accounts
        parent=ROOT.parent/'.mini-account-sandboxes';parent.mkdir(exist_ok=True)
        result['account_state']=str(provision_accounts(parent/secrets.token_hex(12)))
    (lab/'mini-integration.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    return result


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('create')
    p.add_argument('--source', type=Path, required=True)
    p.add_argument('--receipt', type=Path, required=True)
    p.add_argument('--model-config', type=Path, required=True)
    p.add_argument('--accounts', action='store_true', help='显式新建A批账号原生状态；不迁移已有访客状态')
    p = sub.add_parser('serve')
    p.add_argument('--lab', type=Path, required=True)
    p.add_argument('--port', type=int, default=8043)
    auth = p.add_mutually_exclusive_group(required=True)
    auth.add_argument('--fixture-auth', action='store_true')
    auth.add_argument('--mini-config', type=Path, help='用户安全配置的真实平台验证；必须绑定本次新建guest_state')
    args = parser.parse_args()
    if args.command == 'create':
        print(json.dumps(create(args.source, args.receipt, args.model_config, args.accounts), indent=2))
        return
    if args.port == 8033:
        raise ValueError('原生集成禁止使用原预览端口8033')
    lab, _ = validate_lab(args.lab, args.lab/'accounts')
    record = json.loads((lab/'mini-integration.json').read_text('utf-8'))
    if record['lab'] != str(lab) or record['production']:
        raise ValueError('不是本命令创建的独立本地环境')
    with socket.socket() as probe:
        probe.bind(('127.0.0.1', args.port))
    def fixture_verifier(code):
        if code not in ('fixture-code-1', 'fixture-code-2'):
            raise MiniError(401, 'FIXTURE_CODE_REQUIRED', '当前仅隔离fixture验证，不是真实微信code')
        return 'explicit-local-fixture-'+code
    if args.fixture_auth:
        mini = {'store': GuestStore(record['guest_state']), 'verifier': fixture_verifier, 'fixture': True, 'image_policy': 'private_unmoderated'}
        if record.get('account_state'):
            from backend.mini_accounts import AccountStore
            mini['account_store']=AccountStore(record['account_state'])
    else:
        mini = load_config(args.mini_config)
        if mini['store'].root != Path(record['guest_state']):
            raise ValueError('本地真实平台配置必须绑定本次新建的guest_state，不接旧状态')
        if mini.get('account_store') and mini['account_store'].root!=Path(record.get('account_state','')):
            raise ValueError('A批配置必须绑定本次--accounts创建的新状态')
    app = create_app(lab/'accounts', 'http://127.0.0.1:'+str(args.port), score_version_lab=lab, contributions=True, coverage=True,
                     map_recognition=lab/'config.json', mini_config=mini)
    import uvicorn
    print(('LOCAL FIXTURE AUTH ONLY. No WeChat verification.' if args.fixture_auth else 'LOCAL REAL PLATFORM VERIFIER; no production state.')+' Separate lab: '+str(lab), flush=True)
    uvicorn.run(app, host='127.0.0.1', port=args.port, proxy_headers=False)


if __name__ == '__main__':
    main()
