import tempfile
from pathlib import Path
import unittest
import zipfile
from production_release_tools import APP_FILES,pack,stage,verify,read_bundle
ROOT=Path(__file__).resolve().parents[1]

class ReleaseTests(unittest.TestCase):
 def test_native_account_component_required_by_new_gateway(self):
  from production_release_tools import MINI_ACCOUNT_FILES,manifest
  import json
  contents,_=read_bundle(self.bundle)
  self.assertTrue(set(MINI_ACCOUNT_FILES)<=set(contents))
  contents={n:raw for n,raw in contents.items() if n not in MINI_ACCOUNT_FILES}
  target=self.path/'missing-account.zip'
  with zipfile.ZipFile(target,'w') as z:
   for n,raw in contents.items():z.writestr(n,raw)
   z.writestr('manifest.json',json.dumps(manifest(contents,{'fixture':True})))
  with self.assertRaisesRegex(ValueError,'原生账号适配组件'):read_bundle(target)

 def test_account_only_native_fixture_boots_without_optional_ocr(self):
  import subprocess,sys
  target=stage(self.bundle,self.path/'account-only-release')
  code='''from pathlib import Path
import sys
from backend.app import create_app
from backend.mini_auth import GuestStore,provision as provision_guest
from backend.mini_accounts import AccountStore,provision as provision_account
from fastapi.testclient import TestClient
base=Path(sys.argv[1])
mini={'store':GuestStore(provision_guest(base/'guest')),'account_store':AccountStore(provision_account(base/'account')),
      'fixture':True,'verifier':lambda code:'fixture','image_policy':'disabled'}
app=create_app(base/'web','http://127.0.0.1:8989',mini_config=mini)
with TestClient(app,base_url='http://127.0.0.1:8989') as client:
 r=client.post('/api/mini/v1/session',json={'code':'fixture','client_schema':1,'request_key':'fixture-session-key'})
 assert r.status_code==200,r.text
 r=client.get('/api/mini/account/v1/session',headers={'Authorization':'Bearer '+r.json()['token']})
 assert r.status_code==200 and r.json()['actor'] is None,r.text
print('ACCOUNT_BOOT_OK')'''
  root=self.path/'account-only-state';root.mkdir()
  result=subprocess.run([sys.executable,'-B','-c',code,str(root)],cwd=target,capture_output=True,text=True,encoding='utf-8')
  self.assertEqual(result.returncode,0,result.stderr);self.assertIn('ACCOUNT_BOOT_OK',result.stdout)
 def test_default_bundle_without_optional_ocr_still_boots(self):
  import subprocess,sys
  target=stage(self.bundle,self.path/'no-ocr-release')
  self.assertFalse((target/'backend/map_recognition.py').exists())
  result=subprocess.run([sys.executable,'-B','-c',
      'from backend.app import create_app; import sys; app=create_app(sys.argv[1],"http://127.0.0.1:8989"); print("BOOT_OK")',
      str(self.path/'fresh-accounts')],cwd=target,capture_output=True,text=True,encoding='utf-8')
  self.assertEqual(result.returncode,0,result.stderr)
  self.assertIn('BOOT_OK',result.stdout)
 def test_native_components_are_complete_but_historical_packages_still_verify(self):
  from production_release_tools import MINI_FILES,manifest
  import json
  contents,_=read_bundle(self.bundle)
  self.assertTrue(set(MINI_FILES)<=set(contents))
  old={n:raw for n,raw in contents.items() if n not in MINI_FILES}
  def archive(name,items):
   path=self.path/name
   with zipfile.ZipFile(path,'w') as z:
    for n,raw in items.items():z.writestr(n,raw)
    z.writestr('manifest.json',json.dumps(manifest(items,{'fixture':True})))
   return path
  with self.assertRaisesRegex(ValueError,'原生适配组件'):
   read_bundle(archive('new-app-missing-native.zip',old))
  old['backend/app.py']=b'# historical fixture app with no native imports\n'
  read_bundle(archive('historical-without-native.zip',old))
  partial=dict(contents);partial.pop(MINI_FILES[0])
  with self.assertRaises(ValueError):read_bundle(archive('partial-native.zip',partial))
 def test_selection_core_required_by_new_pages_and_old_bundles_still_verify(self):
  from production_release_tools import manifest
  import json
  contents,_=read_bundle(self.bundle)
  self.assertIn('selection_core.js',contents)
  contents.pop('selection_core.js')
  def archive(name,items):
   bundle=self.path/name
   with zipfile.ZipFile(bundle,'w') as z:
    for n,v in items.items():z.writestr(n,v)
    z.writestr('manifest.json',json.dumps(manifest(items,{'fixture':True})))
   return bundle
  with self.assertRaisesRegex(ValueError,'共享选择核心'):
   read_bundle(archive('missing-core.zip',contents))
  contents['index.html']=b'<html><script src="race_scores.js"></script></html>'
  legacy=archive('legacy-page.zip',contents)
  read_bundle(legacy)
  target=stage(legacy,self.path/'legacy-releases')
  verify(target)
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.path=Path(self.temp.name)
  self.wheels=self.path/'wheels';self.wheels.mkdir();(self.wheels/'dummy-1-py3-none-any.whl').write_bytes(b'fixture')
  self.bundle=self.path/'release.zip';self.info=pack(ROOT,ROOT,self.wheels,self.bundle,{'fixture':True})
 def tearDown(self):self.temp.cleanup()
 def test_stage_verify_idempotence_and_no_private_files(self):
  target=stage(self.bundle,self.path/'releases');self.assertEqual(verify(target),self.info)
  self.assertEqual(stage(self.bundle,self.path/'releases'),target)
  names=read_bundle(self.bundle)[0]
  self.assertFalse(any(n.endswith(('.sqlite3','.xlsx')) or 'writeback' in n for n in names))
  (target/'index.html').write_text('tampered')
  with self.assertRaises(ValueError):verify(target)
 def test_unknown_duplicate_traversal_and_tampering_rejected(self):
  with zipfile.ZipFile(self.bundle,'a') as z:z.writestr('../outside','bad')
  with self.assertRaises(ValueError):stage(self.bundle,self.path/'bad')
  self.assertFalse((self.path/'outside').exists())
 def test_content_hash_mismatch_rejected(self):
  contents,info=read_bundle(self.bundle);bad=self.path/'bad.zip'
  with zipfile.ZipFile(bad,'w') as z:
   for n,v in contents.items():z.writestr(n,b'tamper' if n=='index.html' else v)
   import json
   z.writestr('manifest.json',json.dumps(info))
  with self.assertRaises(ValueError):read_bundle(bad)

 def test_complete_frozen_dual_server_snapshot_overrides_checkout_data(self):
  import shutil
  names=('cars.json','gauntlet_data.json','cars.global.json','gauntlet_data.global.json','global-data-manifest.json')
  snapshot={n:(ROOT/n).read_bytes() for n in names}
  code=self.path/'code'
  for name in APP_FILES:
   relative=Path('docs')/name if name.endswith('.md') else Path(name)
   target=code/relative;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/relative,target)
  (code/'cars.global.json').write_bytes(b'checkout data must not be used')
  bundle=self.path/'frozen.zip'
  pack(code,ROOT,self.wheels,bundle,{'data_commit':'frozen-fixture'},data_contents=snapshot)
  contents,_=read_bundle(bundle)
  for name in names:self.assertEqual(contents[name],snapshot[name],name)
  with self.assertRaises(ValueError):
   pack(ROOT,ROOT,self.wheels,self.path/'partial.zip',{},data_contents={**snapshot,'auth.js':b'forbidden'})

 def test_global_components_and_independent_data_binding(self):
  import json
  from production_release_tools import GLOBAL_FILES,manifest
  original,_=read_bundle(self.bundle)
  for case in ('missing','mixed','legacy'):
   contents=dict(original)
   if case=='missing':contents.pop('cars.global.json')
   elif case=='mixed':
    scores=json.loads(contents['gauntlet_data.global.json']);scores['_meta']['dataset_version']='0'*64
    contents['gauntlet_data.global.json']=json.dumps(scores).encode()
   else:
    for n in GLOBAL_FILES:contents.pop(n)
   bundle=self.path/(case+'.zip')
   with zipfile.ZipFile(bundle,'w') as z:
    for n,v in contents.items():z.writestr(n,v)
    z.writestr('manifest.json',json.dumps(manifest(contents,{'case':case})))
   if case=='legacy':self.assertEqual(read_bundle(bundle)[0],contents)
   else:
    with self.assertRaises(ValueError):read_bundle(bundle)
 def test_versioned_data_blocks_legacy_application_activation(self):
  import sqlite3,json
  from contextlib import closing
  from production_release_tools import check_score_compatibility
  target=stage(self.bundle,self.path/'releases');data=self.path/'data';version='a'*32
  version_dir=data/'score-state/scores/versions'/version;version_dir.mkdir(parents=True)
  with closing(sqlite3.connect(data/'accounts.sqlite3')) as db, db:
   db.execute('CREATE TABLE score_current(slot INTEGER,version TEXT)');db.execute('INSERT INTO score_current VALUES(1,?)',(version,))
  (version_dir/'manifest.json').write_text(json.dumps({'schema':1}))
  check_score_compatibility(target,self.info,data)
  legacy={**self.info,'files':{n:v for n,v in self.info['files'].items() if n!='production/score-capability.json'}}
  with self.assertRaises(ValueError):check_score_compatibility(target,legacy,data)
  (version_dir/'manifest.json').write_text(json.dumps({'schema':2}))
  with self.assertRaises(ValueError):check_score_compatibility(target,self.info,data)

 def test_account_controls_block_old_release_without_score_state(self):
  import sqlite3
  from production_release_tools import check_score_compatibility
  target=stage(self.bundle,self.path/'releases');data=self.path/'accounts-only';data.mkdir()
  from contextlib import closing
  with closing(sqlite3.connect(data/'accounts.sqlite3')) as db,db:
   db.execute('CREATE TABLE community_schema(version INTEGER)');db.execute('INSERT INTO community_schema VALUES(1)')
  check_score_compatibility(target,self.info,data)
  legacy={**self.info,'files':{n:v for n,v in self.info['files'].items() if n!='backend/community.py'}}
  with self.assertRaises(ValueError):check_score_compatibility(target,legacy,data)

 def test_explicit_committed_data_snapshot_overrides_checkout_newlines(self):
  snapshot={n:(ROOT/n).read_bytes().replace(b'\r\n',b'\n') for n in ('cars.json','gauntlet_data.json')}
  output=self.path/'canonical.zip';pack(ROOT,ROOT,self.wheels,output,{'snapshot':True},data_contents=snapshot)
  contents,_=read_bundle(output)
  for n,raw in snapshot.items():self.assertEqual(contents[n],raw)

 def test_contribution_ledger_blocks_legacy_activation(self):
  import sqlite3,json
  from contextlib import closing
  from production_release_tools import check_score_compatibility,CONTRIBUTION_FILES
  target=stage(self.bundle,self.path/'releases');data=self.path/'contribution-state';data.mkdir()
  with closing(sqlite3.connect(data/'accounts.sqlite3')) as db,db:
   db.execute('CREATE TABLE contribution_rules(version INTEGER,enabled_at INTEGER)');db.execute('INSERT INTO contribution_rules VALUES(1,1)')
  check_score_compatibility(target,self.info,data)
  legacy={**self.info,'files':{n:v for n,v in self.info['files'].items() if n not in CONTRIBUTION_FILES}}
  with self.assertRaises(ValueError):check_score_compatibility(target,legacy,data)
  cap=target/'production/score-capability.json';old=json.loads(cap.read_text());old.pop('contribution_schema');cap.write_text(json.dumps(old))
  with self.assertRaises(ValueError):check_score_compatibility(target,self.info,data)

 def test_feedback_schema_blocks_old_packages_and_partial_components(self):
  import sqlite3,json
  from contextlib import closing
  from production_release_tools import check_score_compatibility,FEEDBACK_FILES,manifest
  target=stage(self.bundle,self.path/'releases');data=self.path/'feedback-state';data.mkdir()
  with closing(sqlite3.connect(data/'accounts.sqlite3')) as db,db:
   db.execute('CREATE TABLE feedback_schema(version INTEGER)');db.execute('INSERT INTO feedback_schema VALUES(1)')
  check_score_compatibility(target,self.info,data)
  legacy={**self.info,'files':{n:v for n,v in self.info['files'].items() if n not in FEEDBACK_FILES}}
  with self.assertRaises(ValueError):check_score_compatibility(target,legacy,data)
  cap=target/'production/score-capability.json';content=json.loads(cap.read_text());content.pop('feedback_schema');cap.write_text(json.dumps(content))
  with self.assertRaises(ValueError):check_score_compatibility(target,self.info,data)
  contents,_=read_bundle(self.bundle);contents.pop('feedback.js');bad=self.path/'partial-feedback.zip'
  with zipfile.ZipFile(bad,'w') as z:
   for n,v in contents.items():z.writestr(n,v)
   z.writestr('manifest.json',json.dumps(manifest(contents,{'partial':True})))
  with self.assertRaises(ValueError):read_bundle(bad)

if __name__=='__main__':unittest.main()
