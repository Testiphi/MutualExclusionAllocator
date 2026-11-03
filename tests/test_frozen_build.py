"""Freeze provenance/byte binding, not maintenance-data generation."""
from pathlib import Path
import hashlib,json,tempfile,unittest,zipfile
from build_production import load_frozen_snapshot


class FrozenBuildTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
  self.files={n:(n+'\n').encode() for n in ('cars.json','gauntlet_data.json','cars.global.json','gauntlet_data.global.json','global-data-manifest.json')}
  self.runtime={n:{'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)} for n,raw in self.files.items()}
  self.payload={'runtime/'+n:raw for n,raw in self.files.items()};self.payload['workbooks/private.xlsx']=b'excluded fixture'
  inner={'freeze_id':'fixture-freeze','runtime':self.runtime,'members':{n:{'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)} for n,raw in self.payload.items()}}
  self.archive=self.root/'freeze.zip'
  with zipfile.ZipFile(self.archive,'w') as z:
   for n,raw in self.payload.items():z.writestr(n,raw)
   z.writestr('FREEZE_MANIFEST.json',json.dumps(inner))
  self.manifest={'schema':'racepick.local-working-tree-data-freeze.v1','frozen':True,'data_commit':None,'freeze_id':'fixture-freeze',
   'runtime':self.runtime,'national_keys':1,'international_runtime_entries':1,
   'source_archive':{'path':str(self.archive),'bytes':self.archive.stat().st_size,'sha256':hashlib.sha256(self.archive.read_bytes()).hexdigest(),'files':len(self.payload)+1}}
  self.path=self.root/'freeze.json';self.save()
 def save(self):
  self.path.write_text(json.dumps(self.manifest),encoding='utf-8');self.sha=hashlib.sha256(self.path.read_bytes()).hexdigest()
 def test_only_runtime_is_selected_and_uncommitted_source_stays_null(self):
  files,provenance=load_frozen_snapshot(self.path,self.sha)
  self.assertEqual(files,self.files);self.assertIsNone(provenance['data_commit']);self.assertEqual(provenance['data_freeze_id'],'fixture-freeze')
 def test_wrong_manifest_hash_archive_bytes_and_runtime_tampering_rejected(self):
  with self.assertRaises(ValueError):load_frozen_snapshot(self.path,'0'*64)
  self.archive.write_bytes(self.archive.read_bytes()+b'tamper')
  with self.assertRaises(ValueError):load_frozen_snapshot(self.path,self.sha)
 def test_cannot_label_a_working_tree_freeze_as_a_git_commit(self):
  self.manifest['data_commit']='a'*40;self.save()
  with self.assertRaises(ValueError):load_frozen_snapshot(self.path,self.sha)
