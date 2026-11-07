"""Explicit fresh account-test state, read-only startup preflight and offline restore.

No deployment, production migration, credentials, account creation or SMTP here.
"""
from contextlib import closing
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import stat
from urllib.parse import parse_qs,urlsplit

from backend.mini_snapshot import FILES, load_snapshot, safe_path, validate_origin

KIND = 'racepick-isolated-account-test-v1'
DATABASES = ('accounts/accounts.sqlite3', 'guests/guests.sqlite3', 'native/native-accounts.sqlite3')


def private(path):
    path = safe_path(path)
    info = path.stat()
    if path.is_file() and info.st_nlink != 1:
        raise ValueError('Isolation state cannot contain hardlinks')
    if os.name == 'posix' and (info.st_uid != os.geteuid() or stat.S_IMODE(info.st_mode) & 0o077):
        raise ValueError('Isolation state must be private to the service owner')
    return path


def readonly(path):
    if not private(path).is_file():
        raise ValueError('Explicitly provisioned database is required')
    db = sqlite3.connect(Path(path).absolute().as_uri()+'?mode=ro', uri=True, timeout=5)
    db.execute('PRAGMA query_only=ON')
    return db


def schema(path):
    with closing(readonly(path)) as db:
        if db.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
            raise ValueError('Isolation database integrity check failed')
        rows = db.execute("SELECT type,name,tbl_name,sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%' ORDER BY type,name").fetchall()
        return hashlib.sha256(json.dumps(rows, ensure_ascii=False, separators=(',', ':')).encode()).hexdigest()


def root_path(root):
    root = safe_path(root)
    code = Path(__file__).resolve().parents[1]
    if root.is_relative_to(code) or code.is_relative_to(root):
        raise ValueError('Isolation state must be independent of release code')
    return root


def preflight(root, origin=None):
    """Read only. Never instantiate Store, load platform credentials or migrate."""
    root = private(root_path(root))
    marker = json.loads(private(root/'isolation.json').read_bytes())
    if set(marker) != {'kind','schema','origin','snapshot_files','database_schemas'} or marker['kind'] != KIND or marker['schema'] != 1:
        raise ValueError('Unknown account isolation marker')
    validate_origin(marker['origin'])
    if origin is not None and origin != marker['origin']:
        raise ValueError('Exact isolation origin mismatch')
    expected = {'accounts','guests','native','snapshot','isolation.json'}
    if {p.name for p in root.iterdir()} != expected:
        raise ValueError('Unexpected files in isolation root; do not mix old or production state')
    for path in root.rglob('*'):
        private(path)
        if path.name in ('production.json','production-scores.json','recognition.sqlite3','usage.sqlite3'):
            raise ValueError('Production, OCR and usage state forbidden')
    _, snapshot = load_snapshot(root/'snapshot')
    if snapshot['files'] != marker['snapshot_files']:
        raise ValueError('Fixed isolation snapshot changed')
    if set(marker['database_schemas']) != set(DATABASES):
        raise ValueError('Incomplete isolation database declaration')
    actual = {name: schema(root/name) for name in DATABASES}
    if actual != marker['database_schemas']:
        raise ValueError('Schema changed or an old database was supplied; startup never migrates')
    with closing(readonly(root/DATABASES[0])) as db:
        from backend.global_profiles import state
        if db.execute('SELECT max(version) FROM schema_version').fetchone()[0] != 6 or state(db)['global_profile_schema'] != 1:
            raise ValueError('Account schema6 and global profile schema1 required')
        if db.execute('SELECT max(version) FROM community_schema').fetchone()[0] != 1:
            raise ValueError('Account controls schema1 required')
    for name in DATABASES[1:]:
        with closing(readonly(root/name)) as db:
            if db.execute('SELECT version FROM meta').fetchall() != [(1,)]:
                raise ValueError('Guest/native schema1 required')
    return {'kind':KIND,'origin':marker['origin'],'schemas':{'business':6,'community':1,'global_profile':1,'guest':1,'native_account':1},
            'snapshot_files':snapshot['files'],'database_schemas':actual,
            'mail_mode':'file','production_business':False,'schema_migrations_run':False}


def provision(root, snapshot_dir, origin, binding_file):
    """Only create a NEW target; accept exactly the explicitly supplied fixed binding."""
    root = root_path(root)
    validate_origin(origin)
    if root.exists():
        raise ValueError('Provision requires a new target; no old-state initialization or migration')
    source, snapshot = load_snapshot(snapshot_dir)
    binding = json.loads(Path(binding_file).read_bytes())
    if snapshot['files'] != binding['files']:
        raise ValueError('Snapshot does not match the explicit delivery binding')
    versions = {s:getattr(source, 'score_versions' if s=='cn' else 'global_score_versions').version for s in ('cn','global')}
    if versions != binding['snapshot_versions']:
        raise ValueError('Fixed snapshot versions do not match binding')
    root.mkdir(mode=0o700)  # Never mkdir parents or overwrite a previous attempt.
    (root/'snapshot').mkdir(mode=0o700)
    for name in (*FILES,'snapshot.json'):
        target=root/'snapshot'/name
        target.write_bytes((Path(snapshot_dir)/name).read_bytes());target.chmod(0o600)
    from backend.app import Store
    from backend.global_profiles import migrate
    (root/'accounts').mkdir(mode=0o700)
    store = Store(root/'accounts')
    migrate(store)  # Explicit provisioning of an empty new business DB only.
    store.path.chmod(0o600)
    (root/'accounts/service.lock').write_bytes(b'0')
    (root/'accounts/service.lock').chmod(0o600)
    from backend.mini_auth import provision as provision_guests
    from backend.mini_accounts import provision as provision_native
    provision_guests(root/'guests');provision_native(root/'native')
    marker={'kind':KIND,'schema':1,'origin':origin,'snapshot_files':snapshot['files'],
            'database_schemas':{name:schema(root/name) for name in DATABASES}}
    (root/'isolation.json').write_text(json.dumps(marker,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (root/'isolation.json').chmod(0o600)
    return preflight(root,origin)


@contextmanager
def service_lock(root):
    """One isolated owner for service, offline account prep, backup and restore."""
    path=private(root_path(root)/'accounts/service.lock')
    with path.open('r+b') as handle:
        try:
            if os.name=='nt':
                import msvcrt
                msvcrt.locking(handle.fileno(),msvcrt.LK_NBLCK,1)
            else:
                import fcntl
                fcntl.flock(handle.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
        except OSError:
            raise ValueError('Isolated state is in use; no concurrent preparation, backup or restore') from None
        try:
            yield
        finally:
            handle.seek(0)
            if os.name=='nt':msvcrt.locking(handle.fileno(),msvcrt.LK_UNLCK,1)
            else:fcntl.flock(handle.fileno(),fcntl.LOCK_UN)


def backup_stopped(root, destination):
    with service_lock(root):
        return _backup_stopped(root,destination)


def _backup_stopped(root, destination):
    """Offline whole-root preservation. Caller must stop this isolated service first.

    Copies all three databases, signing keys and private file outbox together.
    Not a live backup API. Never overwrites a target or touches production state.
    """
    root=root_path(root);destination=root_path(destination)
    if destination.exists() or destination.is_relative_to(root) or root.is_relative_to(destination):
        raise ValueError('Backup requires a separate new private destination')
    preflight(root)
    # Reject journals/WAL: concurrent/live snapshots require a coordinated mechanism.
    if any(p.name.endswith(('-wal','-shm','-journal')) for p in root.rglob('*')):
        raise ValueError('Stop writers and preserve journal evidence; offline backup refused')
    def hashes(directory):
        return {str(p.relative_to(directory)):hashlib.sha256(p.read_bytes()).hexdigest()
                for p in directory.rglob('*') if p.is_file() and p.relative_to(directory)!=Path('accounts/service.lock')}
    before=hashes(root)
    shutil.copytree(root,destination,ignore=lambda directory,names: ['service.lock'] if Path(directory)==root/'accounts' else [])
    (destination/'accounts/service.lock').write_bytes(b'0');(destination/'accounts/service.lock').chmod(0o600)
    after=hashes(root);copied=hashes(destination)
    if before != after or before != copied:
        raise ValueError('State changed during offline backup; retain both targets and do not activate')
    preflight(destination)
    return {'files_verified':len(copied),'independent_target':True,'secrets_included':True,'publishable':False}


def restore_stopped(backup, destination):
    """Independent new target only; no replacement of an active root or old DB rollback."""
    return backup_stopped(backup,destination)


def prepare_account_stopped(root, email, password):
    """Explicit new isolated account only, original register/verify handlers, file outbox.

    This is an offline operator action, never a public route or automatic startup task.
    A failed/unknown result must be inspected locally; existing email is never retried.
    """
    with service_lock(root):
        report=preflight(root)
        root=root_path(root)
        from backend.app import create_app,Credentials
        from backend.mailing import MailConfig
        from starlette.requests import Request
        email=Credentials.email_valid(email)
        with closing(readonly(root/'accounts/accounts.sqlite3')) as db:
            if db.execute('SELECT 1 FROM users WHERE email=?',(email,)).fetchone():
                raise ValueError('Isolated account already exists; do not replay registration or mail')
        app=create_app(root/'accounts',report['origin'],production=True,mail_config=MailConfig(),isolated_account_root=root)
        web=app.state.native_accounts
        request=web.request(Request({'type':'http','method':'POST','path':'/','headers':[],
            'client':('127.0.0.1',0),'mini_ip':'127.0.0.1'}))
        before=set((root/'accounts/outbox').glob('*.json'))
        web.handlers['register'](web.models['register'].model_validate({'email':email,'password':password}),request)
        after=set((root/'accounts/outbox').glob('*.json'))
        if len(after-before)!=1:
            raise ValueError('Registration delivery uncertain; inspect private state, do not retry')
        payload=json.loads(next(iter(after-before)).read_bytes())
        if payload['to']!=email or payload['purpose']!='verify':
            raise ValueError('Private verification delivery mismatch; do not retry')
        token=parse_qs(urlsplit(payload['url']).fragment)['token'][0]
        web.handlers['verify-email'](web.models['verify-email'].model_validate({'token':token}),request)
        return {'created':True,'verified':True,'mail_mode':'file','external_mail_sent':False,'production_account':False}
