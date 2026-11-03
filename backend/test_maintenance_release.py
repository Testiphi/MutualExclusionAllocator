"""Disposable production-shaped fixtures; Windows lock is explicitly mocked only here."""
from contextlib import nullcontext
from copy import deepcopy
import json
import os
from pathlib import Path
import sqlite3
import unittest
from unittest.mock import patch

from backend import maintenance_release as m
from backend import test_global_score_production as fixtures
from backend.global_score_production import migrate,preflight
from backend.global_profiles import migrate as migrate_profiles
from backend.global_scores import rebind
from backend.production import make_app
from backend.score_production import backup,drill
from backend.score_repository import digest,encode
from production_release_tools import pack,stage,check_score_compatibility,APP_FILES

ROOT=Path(__file__).resolve().parents[1]

class MaintenanceReleaseTests(unittest.TestCase):
    def setUp(self):
        self.f=fixtures.GlobalScoreProductionTests();self.f.setUp();self.addCleanup(self.f.tearDown)
        migrate(self.f.config,self.f.source,self.f.dataset,self.f.version);migrate_profiles(self.f.store)
        if os.name=='nt':
            lock=patch.object(m,'service_lock',lambda path:nullcontext());lock.start();self.addCleanup(lock.stop)
        raw={n:(ROOT/n).read_bytes() for n in m.FILES}
        data=json.loads(raw['gauntlet_data.json']);data['tracks'][0]['五区']['理论'][0]['time']-=.01
        raw['gauntlet_data.json']=encode(data).encode()
        cars=json.loads(raw['cars.json']);car=next(c for c in cars['cars'] if c.get('nickname')=='cc850')
        car['zones']=['五区','四区'];car['star_rule'].update(min=3,zone4Max=3)
        raw['cars.json']=encode(cars).encode()
        catalog,global_data,manifest=[json.loads(raw[n]) for n in m.FILES[2:]]
        catalog['cars'][0]['score']+=1
        global_data['tracks'][0]['五区']['理论'][0]['time']-=.01
        raw.update(rebind(catalog,global_data,manifest))
        self.raw=raw
        parent=Path(self.f.temp.name);wheels=parent/'wheels';wheels.mkdir();(wheels/'fixture-1-py3-none-any.whl').write_bytes(b'fixture only')
        self.freeze='b'*24
        provenance={'code_commit':'c'*40,'data_commit':None,'data_source_kind':'approved_local_freeze',
                    'maintenance_release':{'required':True},
                    'data_freeze_id':self.freeze,'data_freeze_manifest_sha256':'d'*64,'data_source_archive_sha256':'e'*64,
                    'data_runtime':{n:{'sha256':digest(v),'bytes':len(v)} for n,v in raw.items()}}
        bundle=parent/'test-only.zip';pack(ROOT,ROOT,wheels,bundle,provenance,data_contents=raw)
        self.source=stage(bundle,parent/'releases')
        with self.f.store.connect() as db:
            db.execute('INSERT INTO profiles_global VALUES(?,?,?,?,?,?)',(self.f.uid,'["杰哥"]','{"杰哥":6}','{"杰哥":true}',3,123))

    def plan(self):return m.preview(self.f.config,self.source,self.freeze)
    def apply(self,plan=None):
        plan=plan or self.plan()
        return m.apply(self.f.config,self.source,plan,plan['digest'])

    def test_readonly_preview_complete_diff_and_tampered_source_rejected(self):
        before=self.f.store.path.read_bytes();plan=self.plan()
        self.assertEqual(before,self.f.store.path.read_bytes())
        with self.f.store.connect() as db:self.assertIsNone(db.execute("SELECT 1 FROM sqlite_master WHERE name='maintenance_releases'").fetchone())
        self.assertEqual(plan['scores']['cn']['counts']['faster'],1)
        self.assertEqual(plan['scores']['global']['counts']['faster'],1)
        self.assertTrue(plan['catalogs']['cn']['cars']);self.assertTrue(plan['catalogs']['global']['cars'])
        path=self.source/'cars.json';path.write_bytes(path.read_bytes()+b' ')
        with self.assertRaises(ValueError):self.plan()

    def test_apply_both_versions_original_bytes_business_preservation_and_restore(self):
        plan=self.plan();receipt=self.apply(plan)
        self.assertTrue(receipt['existing_rows_preserved'])
        self.assertEqual(self.apply(plan)['targets'],receipt['targets'])
        self.assertTrue(self.apply(plan)['idempotent'])
        app=make_app(self.f.config,'unused')
        merged={**app.state.score_versions.current()[1],**app.state.global_score_versions.current()[1]}
        self.assertEqual(merged,self.raw)
        self.assertFalse(preflight(self.f.config)['global_writes_enabled'])
        restored=drill(self.f.config,backup(self.f.config));self.assertFalse(restored['active_database_replaced'])
        self.assertEqual(restored['counts']['profiles_global'],1)
        copy=make_app({**self.f.config,'data_dir':restored['drill_directory']},'unused')
        self.assertEqual(copy.state.global_score_versions.current()[1],self.raw_global())
        with m.ReadStore(restored['drill_directory']).connect() as db:self.assertEqual(m.audit(db,plan['digest']),receipt)
        with self.f.store.connect() as db:
            self.assertEqual(db.execute('SELECT count(*) FROM users').fetchone()[0],1)
            self.assertEqual(db.execute('SELECT revision FROM profiles_global').fetchone()[0],3)
            self.assertEqual(db.execute('SELECT count(*) FROM contributions').fetchone()[0],1)

    def raw_global(self):return {n:self.raw[n] for n in m.FILES[2:]}

    def test_failure_between_pointers_rolls_back_both_and_same_plan_resumes(self):
        plan=self.plan()
        for phase in ('registered','cn-pointer'):
            def fail(name):
                if name==phase:raise RuntimeError('isolated injected crash')
            with patch.object(m,'checkpoint',side_effect=fail):
                with self.assertRaises(RuntimeError):self.apply(plan)
            _,_,cn,gl=m.writers(self.f.config)
            self.assertEqual({'cn':cn.current()[0]['id'],'global':gl.current()[0]['id']},plan['bases'])
            restored=drill(self.f.config,backup(self.f.config));self.assertFalse(restored['active_database_replaced'])
        self.assertEqual(self.apply(plan)['bases'],plan['bases'])

    def test_website_submission_publishing_still_works_after_catalog_evolution(self):
        from backend.test_score_production import ScoreProductionTests
        from backend.score_production import toggle
        self.apply();toggle(self.f.config,True);self.f.login()
        pick=ScoreProductionTests.accepted(self.f)
        r=self.f.client.post('/api/admin/score-versions',json={'request_key':'maintenance-after-submit','items':[pick]})
        self.assertEqual(r.status_code,200,r.text);plan=r.json()
        self.f.client.post('/api/admin/score-versions/reauth',json={'password':'test-password-12345'})
        r=self.f.client.post('/api/admin/score-versions/'+plan['id']+'/execute',json={'digest':plan['digest'],'effects_confirmed':True,
            'items':[{'submission_id':pick['id'],'confirmed':True}]})
        self.assertEqual(r.status_code,200,r.text)
        self.assertEqual(self.f.app.state.score_versions.current()[1]['cars.json'],self.raw['cars.json'])

    def test_stale_plan_changed_controls_pending_batch_and_plan_tamper_rejected(self):
        plan=self.plan();bad=deepcopy(plan);bad['scores']['cn']['counts']['removed']=123
        with self.assertRaises(ValueError):self.apply(bad)
        with self.f.store.connect() as db:db.execute('UPDATE global_score_control SET enabled=1')
        with self.assertRaises(ValueError):self.apply(plan)
        with self.f.store.connect() as db:
            db.execute('UPDATE global_score_control SET enabled=0')
            db.execute("INSERT INTO score_batches VALUES('x','actor','key','hash','applying','{}')")
        with self.assertRaises(Exception):self.plan()

    def test_version_drift_rejects_apply_and_rollback_without_losing_later_data(self):
        plan=self.plan();receipt=self.apply(plan)
        _,_,cn,gl=m.writers(self.f.config)
        later=cn.versions.create(cn.current()[1],receipt['targets']['cn'],'fixture-later')
        with self.f.store.connect() as db:db.execute('UPDATE score_current SET version=?',(later,))
        with self.assertRaises(ValueError):self.apply(plan)
        with self.assertRaises(ValueError):m.rollback(self.f.config,plan['digest'],digest(encode(receipt).encode()))
        self.assertEqual(m.writers(self.f.config)[2].current()[0]['id'],later)

    def test_catalog_registration_cannot_authorize_arbitrary_hash_and_rollback_gates_old_code(self):
        from backend.score_repository import approved_catalog
        self.assertFalse(approved_catalog({'cars_sha256':'a'*64,'maintenance_catalogs':{'f'*64:{'schema':1}}},'cars_sha256','f'*64))
        plan=self.plan();receipt=self.apply(plan)
        target=self.f.path/'candidate';(target/'production').mkdir(parents=True)
        cap=json.loads((ROOT/'production/score-capability.json').read_text());cap.pop('maintenance_release')
        (target/'production/score-capability.json').write_text(json.dumps(cap))
        with self.assertRaisesRegex(ValueError,'维护版本'):check_score_compatibility(target,{'files':dict.fromkeys(APP_FILES)},self.f.path)
        restored=m.rollback(self.f.config,plan['digest'],digest(encode(receipt).encode()))
        self.assertEqual(restored['state'],'reverted')
        _,_,cn,gl=m.writers(self.f.config)
        self.assertEqual({'cn':cn.current()[0]['id'],'global':gl.current()[0]['id']},plan['bases'])
        check_score_compatibility(target,{'files':dict.fromkeys(APP_FILES)},self.f.path)
        with self.assertRaises(ValueError):self.apply(plan)
        fresh=self.plan();self.assertNotEqual(fresh['digest'],plan['digest'])
        self.assertEqual(self.apply(fresh)['state'],'applied')

    @unittest.skipUnless(os.name=='posix','actual Linux service flock required')
    def test_live_service_lock_refuses_release(self):
        plan=self.plan()
        with m.service_lock(self.f.path):
            with self.assertRaises(ValueError):self.apply(plan)
