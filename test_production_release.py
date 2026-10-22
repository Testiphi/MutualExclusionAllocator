import tempfile
from pathlib import Path
import unittest
import zipfile
from production_release_tools import APP_FILES,pack,stage,verify,read_bundle
ROOT=Path(__file__).resolve().parent

class ReleaseTests(unittest.TestCase):
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

if __name__=='__main__':unittest.main()
