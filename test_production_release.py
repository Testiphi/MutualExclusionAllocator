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
if __name__=='__main__':unittest.main()
