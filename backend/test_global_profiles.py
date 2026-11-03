"""International cloud garages: only fresh, disposable website/native/restore fixtures."""
from pathlib import Path
import json
import tempfile
import unittest
from fastapi.testclient import TestClient
from backend import test_mini_accounts as native_fixture
from backend.app import ROOT,Store,create_app
from backend.global_profiles import state,migrate


class GlobalCloudTests(unittest.TestCase):
    def setUp(self):
        self.f=native_fixture.NativeAccountTests();self.f.setUp();self.addCleanup(self.f.tearDown)
        self.f.register();self.value,self.auth=self.f.login()
        data=json.loads((ROOT/'gauntlet_data.global.json').read_bytes())
        self.oc=next(e['cars'][0]['name'] for t in data['tracks'] for e in t['五区']['理论'] if e['cars'][0].get('oc') is True)

    def save(self,revision=0,key='global-cloud-save-key',**extra):
        return self.f.client.put(native_fixture.P+'/profile?server=global',headers=self.auth,json={
            'schema':1,'request_key':key,'explicit_save':True,'intent':'save','revision':revision,
            'cars':[self.oc],'stars':{self.oc:6},'ocMap':{self.oc:True},**extra})

    def test_native_global_is_separate_from_national_and_preserves_oc(self):
        r=self.save();self.assertEqual(r.status_code,200,r.text)
        self.assertEqual(r.json(),{'server':'global','revision':1})
        cloud=self.f.client.get(native_fixture.P+'/profile?server=global',headers=self.auth).json()
        self.assertEqual(cloud['storage'],'account');self.assertEqual(cloud['profile']['ocMap'],{self.oc:True})
        self.assertIsNone(self.f.client.get(native_fixture.P+'/profile?server=cn',headers=self.auth).json()['profile'])
        self.assertEqual(self.f.save(self.auth).status_code,200)
        self.assertEqual(self.f.client.get(native_fixture.P+'/profile?server=global',headers=self.auth).json()['revision'],1)

    def test_global_revision_conflict_and_cross_server_key_cannot_replay(self):
        self.assertEqual(self.save().status_code,200)
        self.assertEqual(self.save().json()['revision'],1)
        conflict=self.save(key='global-conflict-new-key')
        self.assertEqual(conflict.status_code,409)
        self.assertEqual(conflict.json()['current']['profile']['ocMap'],{self.oc:True})
        self.assertEqual(conflict.json()['submitted']['revision'],0)
        replay=self.f.client.get(native_fixture.P+'/operations/global-cloud-save-key?action=profile-save&server=global',headers=self.auth)
        self.assertEqual(replay.status_code,200,replay.text)
        wrong=self.f.client.get(native_fixture.P+'/operations/global-cloud-save-key?action=profile-save&server=cn',headers=self.auth)
        self.assertEqual(wrong.status_code,409)
        self.assertEqual(self.f.save(self.auth,key='global-cloud-save-key').status_code,409)

    def test_website_and_native_read_the_same_global_record(self):
        self.assertEqual(self.save().status_code,200)
        with TestClient(self.f.app,base_url='http://127.0.0.1:8044') as browser:
            me=browser.get('/api/auth/me').json()
            r=browser.post('/api/auth/login',json={'email':'alice@example.test','password':native_fixture.PASSWORD},headers={
                'Origin':'http://127.0.0.1:8044','X-CSRF-Token':me['csrf']})
            self.assertEqual(r.status_code,200,r.text)
            headers={'Origin':'http://127.0.0.1:8044','X-CSRF-Token':r.json()['csrf'],'X-Account-ID':r.json()['user']['id'],'X-Profile-Save':'explicit'}
            cloud=browser.get('/api/me/profile?server=global',headers=headers).json()
            self.assertEqual(cloud['profile']['ocMap'],{self.oc:True})
            r=browser.put('/api/me/profile?server=global',headers=headers,json={'revision':1,'cars':[],'stars':{},'ocMap':{}})
            self.assertEqual(r.status_code,200,r.text)
            native=self.f.client.get(native_fixture.P+'/profile?server=global',headers=self.auth).json()
            self.assertEqual(native['revision'],2);self.assertEqual(native['profile'],{'cars':[],'stars':{},'ocMap':{}})
            self.assertIsNone(browser.get('/api/me/profile',headers=headers).json()['profile'])

    def test_bad_oc_foreign_car_and_other_account_rejected(self):
        self.assertEqual(self.save(ocMap={self.oc:'true'}).status_code,400)
        self.assertEqual(self.save(key='global-invalid-car-key',cars=['not-a-real-car']).status_code,422)
        self.assertEqual(self.save().status_code,200)
        self.f.register('bob@example.test');_,other=self.f.login('bob@example.test')
        own=self.f.client.get(native_fixture.P+'/profile?server=global',headers=other).json()
        self.assertIsNone(own['profile'])
        self.assertEqual(self.f.client.get(native_fixture.P+'/profile?server=global',headers={**other,'X-Account-ID':self.value['actor']['id']}).status_code,401)


class ProfileSchemaTests(unittest.TestCase):
    def test_existing_database_is_not_auto_migrated_and_local_explicit_is_idempotent(self):
        with tempfile.TemporaryDirectory() as root:
            store=Store(Path(root))
            with store.connect() as db:self.assertEqual(state(db)['global_profile_schema'],0)
            app=create_app(Path(root),'http://127.0.0.1:8993')
            self.assertFalse(app.state.global_profiles)
            with store.connect() as db:self.assertEqual(state(db)['global_profile_schema'],0)
            self.assertFalse(migrate(store)['already_migrated'])
            before=store.path.read_bytes();self.assertTrue(migrate(store)['already_migrated']);self.assertEqual(before,store.path.read_bytes())
            self.assertTrue(create_app(Path(root),'http://127.0.0.1:8993').state.global_profiles)

    def test_backup_drill_keeps_global_garage_and_old_activation_is_rejected(self):
        from backend import test_global_score_production as fixtures
        from backend.global_score_production import migrate as migrate_scores
        from backend.score_production import backup,drill,verify_backup
        from production_release_tools import APP_FILES,GLOBAL_PROFILE_FILES,check_score_compatibility
        fixture=fixtures.GlobalScoreProductionTests();fixture.setUp();self.addCleanup(fixture.tearDown)
        migrate_scores(fixture.config,fixture.source,fixture.dataset,fixture.version)
        migrate(fixture.store)
        with fixture.store.connect() as db:
            db.execute('INSERT INTO profiles_global VALUES (?,?,?,?,?,?)',(fixture.uid,'["杰哥"]','{"杰哥":6}','{"杰哥":true}',3,123))
        archive=backup(fixture.config);self.assertEqual(verify_backup(archive)['global_profile_schema'],1)
        restored=drill(fixture.config,archive)
        self.assertEqual(restored['counts']['profiles_global'],1);self.assertEqual(restored['global_profile_schema'],1)
        self.assertFalse(restored['active_database_replaced'])
        target=fixture.path/'new-profile-code';(target/'production').mkdir(parents=True)
        (target/'production/score-capability.json').write_bytes((ROOT/'production/score-capability.json').read_bytes())
        info={'files':dict.fromkeys(APP_FILES)}
        check_score_compatibility(target,info,fixture.path)
        old={'files':{n:v for n,v in info['files'].items() if n not in GLOBAL_PROFILE_FILES}}
        with self.assertRaisesRegex(ValueError,'国际账号车库'):check_score_compatibility(target,old,fixture.path)
