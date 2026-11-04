"""Read-only compatibility guard for the shared OCR queue schema."""
import hashlib
import json
from pathlib import Path
import sqlite3
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import closing
from production_release_tools import check_score_compatibility


class BridgeDeliveryImportsTests(unittest.TestCase):
    def test_packaged_bridge_contains_its_production_startup_dependency(self):
        # Import from the exact shipped module set, outside the source checkout.
        from tools.build_mini_ocr_delivery import BRIDGE, ROOT
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);(root/'backend').mkdir()
            for module in BRIDGE:
                shutil.copyfile(ROOT/'backend'/(module+'.py'),root/'backend'/(module+'.py'))
            code=('import sys;sys.path.insert(0,'+repr(str(root))+');'
                  'from backend.ocr_queue_bridge import load_bridge_config;'
                  'from backend.map_ocr_production import settings')
            result=subprocess.run([sys.executable,'-I','-B','-c',code],
                                  cwd=root,capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)


class SafetyCompatibilityTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.data=self.root/'data';self.data.mkdir()
        self.queue=self.data/'map-recognition';self.queue.mkdir()
        self.db=self.queue/'recognition.sqlite3'
        self.target=self.root/'release';(self.target/'production').mkdir(parents=True)
        self.cap=self.target/'production/score-capability.json'
        self.info={'files':{'production/score-capability.json':{}}}

    def prepare(self,complete=True):
        with closing(sqlite3.connect(self.db,isolation_level=None)) as db:
            db.execute('CREATE TABLE safety_checks(job_id TEXT PRIMARY KEY)')
            if complete:
                db.execute('CREATE TABLE safety_schema(version INTEGER)');db.execute('INSERT INTO safety_schema VALUES(1)')

    def test_old_release_cannot_activate_after_safety_schema(self):
        self.prepare();self.cap.write_text('{}')
        before=hashlib.sha256(self.db.read_bytes()).hexdigest()
        with self.assertRaisesRegex(ValueError,'checking'):
            check_score_compatibility(self.target,self.info,self.data)
        self.assertEqual(hashlib.sha256(self.db.read_bytes()).hexdigest(),before)

    def test_compatible_release_keeps_schema_and_rows(self):
        self.prepare();self.cap.write_text(json.dumps({'ocr_queue_safety_schema':1}))
        before=self.db.read_bytes();check_score_compatibility(self.target,self.info,self.data)
        self.assertEqual(self.db.read_bytes(),before)

    def test_partial_schema_is_rejected_even_with_capability(self):
        self.prepare(False);self.cap.write_text(json.dumps({'ocr_queue_safety_schema':1}))
        with self.assertRaises(ValueError):check_score_compatibility(self.target,self.info,self.data)

    def test_existing_unmigrated_queue_does_not_require_new_schema(self):
        with closing(sqlite3.connect(self.db,isolation_level=None)) as db:db.execute('CREATE TABLE jobs(id TEXT)')
        self.cap.write_text('{}')
        check_score_compatibility(self.target,self.info,self.data)
        with closing(sqlite3.connect(self.db,isolation_level=None)) as db:
            self.assertIsNone(db.execute("SELECT name FROM sqlite_master WHERE name='safety_schema'").fetchone())
