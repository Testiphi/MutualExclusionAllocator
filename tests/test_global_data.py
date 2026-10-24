"""Pure-fixture checks for the independently generated international bundle."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

from tools.build_global_data import (
    CATALOG_FILE, SCORES_FILE, MANIFEST_FILE, CAPABILITIES,
    build_bundle, file_bytes, load_source, validate_global_bundle, write_bundle,
)


def source_fixture():
    def tiers(entries=None):
        return {zone: {tier: (deepcopy(entries or []) if (zone, tier) == ('五区', '理论') else [])
                       for tier in ('理论', '高手', '普通', '自动')}
                for zone in ('五区', '四区')}

    active = {'tracks': [
        {'大地图': 'Region', '小地图': 'First', 'international_track_id': 'region::first',
         'international_region': 'Region', 'international_track': 'First',
         'has_special_route': True, 'special_route_note': '跳图',
         'private_source_note': 'must not be published',
         **tiers([{'cars': [{'name': 'Regular'}], 'time': 22.84},
                  {'cars': [{'name': 'Regular'}], 'time': 21.9, 'sc': True, 'sc_type': '跳图'},
                  {'cars': [{'name': 'evoExample'}], 'time': 20.11}])},
        {'大地图': 'Fuji', '小地图': 'Empty', 'international_track_id': 'fuji::empty',
         **tiers()},
    ]}
    ledger = {'records': [
        {'target_id': 'region::first', 'car': 'Regular', 'asec_id': 1,
         'time': 22.84, 'sc': False},
        {'target_id': 'region::first', 'car': 'Regular', 'asec_id': 1,
         'time': 21.9, 'sc': True, 'sc_type': '跳图'},
        {'target_id': 'region::first', 'car': 'evoExample', 'asec_id': 2,
         'time': 20.11},
    ]}
    oc = {'count': 1, 'records': [
        {'international_track_id': 'region::first', 'zone': '五区', 'tier': '理论',
         'cars': [{'name': 'Regular', 'oc': True}], 'base_car_id': 1,
         'time': 19.55, 'source_value_text': '19.55', 'sc': False,
         'source_kind': 'user_direct_final_theory', 'status': 'accepted_saved'},
    ]}
    asec = {'cars': [
        {'id': 1, 'brand': 'Brand', 'model': 'Regular', 'car_class': 'A', 'max_stars': 5,
         'detail': {'stars': {'star_5': {'rank': 4001, 'stats': [300, 80, 60, 70]}}}},
        {'id': 2, 'brand': 'Brand', 'model': 'Example', 'car_class': 'S', 'max_stars': 6,
         'evo': True,
         'detail': {'stars': {'star_6': {'rank': 5000, 'stats': [500, 90, 80, 70]}}}},
        {'id': 3, 'brand': 'Unused', 'model': 'Catalog Only', 'car_class': 'D', 'max_stars': 3},
    ]}
    identities = {'cars': [
        {'title': 'Brand Regular', 'nickname': 'Regular', 'asec_id': 1},
        {'title': 'Brand Example', 'nickname': 'evoExample', 'asec_id': 2},
    ]}
    return active, ledger, oc, asec, identities


class GlobalDataTests(unittest.TestCase):
    def build(self, documents=None):
        return build_bundle(*(documents or source_fixture()), expected_non_oc=3)

    def test_exact_physical_pool_maximum_stars_and_unknown_evo_metrics(self):
        bundle = self.build()
        cars = bundle[CATALOG_FILE]['cars']
        self.assertEqual(len(cars), 2)
        regular = next(car for car in cars if car['nickname'] == 'Regular')
        evo = next(car for car in cars if car['nickname'] == 'evoExample')
        self.assertEqual(regular['star_rule'], {'min': 5, 'max': 5, 'default': 5})
        self.assertEqual(regular['score'], 4001)
        self.assertEqual([regular[key] for key in ('max_speed', 'acceleration', 'handling', 'nitro')],
                         [300, 80, 60, 70])
        self.assertEqual(evo['stats_status'], 'evo_configuration_unknown')
        self.assertTrue(all(evo[key] is None for key in
                            ('score', 'max_speed', 'acceleration', 'handling', 'nitro')))
        self.assertEqual(evo['base_class'], 'S')
        self.assertEqual(bundle[CATALOG_FILE]['_nickname_map'],
                         {'Regular': 'Brand Regular', 'evoExample': 'Brand Example'})
        self.assertEqual(bundle[CATALOG_FILE]['capabilities'], CAPABILITIES)

    def test_oc_is_independent_score_state_of_the_same_car_and_value_is_unchanged(self):
        bundle = self.build()
        entries = bundle[SCORES_FILE]['tracks'][0]['五区']['理论']
        regular = [entry for entry in entries if entry['cars'][0]['name'] == 'Regular']
        self.assertEqual(len(regular), 3)
        self.assertEqual(next(entry['time'] for entry in regular if entry['cars'][0].get('oc')), 19.55)
        self.assertEqual(bundle[MANIFEST_FILE]['counts'],
                         {'physical_cars': 2, 'tracks': 2, 'covered_tracks': 1,
                          'score_entries': 4, 'non_oc_entries': 3, 'oc_entries': 1,
                          'special_entries': 1, 'normal_entries': 3})
        self.assertEqual(bundle[SCORES_FILE]['tracks'][-1]['international_track_id'], 'fuji::empty')

    def test_already_integrated_oc_is_deduplicated_but_conflicting_value_is_rejected(self):
        documents = source_fixture()
        original = self.build(documents)
        integrated = deepcopy(documents)
        integrated[0]['tracks'][0]['五区']['理论'].append(
            {'cars': [{'name': 'Regular', 'oc': True}], 'time': 19.55})
        integrated[1]['records'].append({'target_id': 'region::first', 'car': 'Regular',
                                        'oc': True, 'asec_id': 1, 'time': 19.55})
        self.assertEqual(self.build(integrated), original)
        integrated[2]['records'][0]['time'] = 19.45
        with self.assertRaisesRegex(ValueError, 'conflict'):
            self.build(integrated)

    def test_duplicate_supplement_is_not_a_new_vehicle_or_score(self):
        documents = source_fixture()
        documents[2]['records'].append(deepcopy(documents[2]['records'][0]))
        documents[2]['count'] = 2
        self.assertEqual(self.build(documents)[MANIFEST_FILE]['counts']['score_entries'], 4)

    def test_authorized_oc_estimate_is_bound_to_same_car_ordinary_source_and_delta(self):
        documents = source_fixture()
        record = documents[2]['records'][0]
        record.update(source_kind='user_authorized_oc_delta_estimate',
                      source_time=22.84, adjustment=-0.1, time=22.74)
        bundle = self.build(documents)
        entries = bundle[SCORES_FILE]['tracks'][0]['五区']['理论']
        self.assertEqual(next(e['time'] for e in entries if e['cars'][0].get('oc')), 22.74)
        for field, value in [('source_time', 22.8), ('adjustment', -0.2), ('time', 22.73)]:
            changed = deepcopy(documents)
            changed[2]['records'][0][field] = value
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, 'OC delta estimate'):
                self.build(changed)

    def test_unknown_oc_vehicle_unaccepted_reference_or_wrong_identity_is_rejected(self):
        for modification in ('unknown_name', 'unaccepted', 'wrong_id', 'no_oc', 'sc'):
            documents = source_fixture()
            record = documents[2]['records'][0]
            if modification == 'unknown_name':
                record['cars'][0]['name'] = 'NotOwnedInCatalog'
            elif modification == 'unaccepted':
                record['status'] = 'candidate'
            elif modification == 'wrong_id':
                record['base_car_id'] = 2
            elif modification == 'no_oc':
                record['cars'][0].pop('oc')
            else:
                record.update(sc=True, sc_type='跳图')
            with self.subTest(modification=modification), self.assertRaises(ValueError):
                self.build(documents)

    def test_no_other_zone_tier_or_explicit_stars_can_be_published(self):
        for zone, tier in [('四区', '理论'), ('五区', '高手'), ('五区', '普通')]:
            documents = source_fixture()
            documents[0]['tracks'][0][zone][tier] = [{'cars': [{'name': 'Regular'}], 'time': 20}]
            with self.subTest(zone=zone, tier=tier), self.assertRaises(ValueError):
                self.build(documents)
        documents = source_fixture()
        documents[0]['tracks'][0]['五区']['理论'][0]['cars'][0]['stars'] = 5
        with self.assertRaisesRegex(ValueError, 'without star columns'):
            self.build(documents)

    def test_active_ledger_mismatch_and_duplicate_base_evo_id_are_rejected(self):
        documents = source_fixture()
        documents[1]['records'][0]['time'] = 22.74
        with self.assertRaisesRegex(ValueError, 'ledger differ'):
            self.build(documents)
        documents = source_fixture()
        documents[4]['cars'][1]['asec_id'] = 1
        with self.assertRaises(ValueError):
            self.build(documents)

    def test_global_metadata_and_manifest_fail_closed_on_cn_or_mixed_versions(self):
        original = self.build()
        for target in (CATALOG_FILE, SCORES_FILE, MANIFEST_FILE):
            bundle = deepcopy(original)
            bundle[target]['_meta']['server_id'] = 'cn'
            with self.subTest(target=target), self.assertRaises(ValueError):
                validate_global_bundle(bundle[CATALOG_FILE], bundle[SCORES_FILE], bundle[MANIFEST_FILE])
        changed_documents = source_fixture()
        changed_documents[0]['tracks'][0]['五区']['理论'][0]['time'] = 22.5
        changed_documents[1]['records'][0]['time'] = 22.5
        changed = self.build(changed_documents)
        with self.assertRaisesRegex(ValueError, 'Mixed'):
            validate_global_bundle(original[CATALOG_FILE], changed[SCORES_FILE], original[MANIFEST_FILE])

    def test_payload_or_raw_bytes_tampering_is_rejected(self):
        bundle = self.build()
        changed = deepcopy(bundle)
        changed[SCORES_FILE]['tracks'][0]['五区']['理论'][0]['time'] += 0.01
        with self.assertRaisesRegex(ValueError, 'Payload hash'):
            validate_global_bundle(changed[CATALOG_FILE], changed[SCORES_FILE], changed[MANIFEST_FILE])
        raw = {name: file_bytes(bundle[name]) for name in (CATALOG_FILE, SCORES_FILE)}
        raw[CATALOG_FILE] += b' '
        with self.assertRaisesRegex(ValueError, 'Manifest bytes'):
            validate_global_bundle(bundle[CATALOG_FILE], bundle[SCORES_FILE], bundle[MANIFEST_FILE], raw)

    def test_build_is_deterministic_nonmutating_and_does_not_copy_private_source_fields(self):
        documents = source_fixture()
        before = deepcopy(documents)
        first = self.build(documents)
        self.assertEqual(documents, before)
        self.assertEqual(first, self.build(documents))
        serialized = b''.join(file_bytes(value) for value in first.values())
        self.assertNotIn(b'private_source_note', serialized)
        self.assertNotIn(b'must not be published', serialized)

    def test_explicit_source_directory_relocates_old_absolute_pointers(self):
        documents = source_fixture()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            maintenance = root / 'maintenance'
            maintenance.mkdir()
            names = ('gauntlet_data_international.json', 'score-ledger.json',
                     'oc-score-ledger.json', 'cars-full.json', 'maintenance-car-identities.json')
            for name, document in zip(names, documents):
                path = root / name if name == 'cars-full.json' else maintenance / name
                path.write_bytes(file_bytes(document))
            pointer = {'active_json': 'Q:/old/personal/path/gauntlet_data_international.json',
                       'active_ledger': 'Q:/old/personal/path/score-ledger.json',
                       'oc_reference_file': 'oc-score-ledger.json',
                       'maintenance_identity_catalog': 'maintenance-car-identities.json',
                       'active_non_oc_records': 3}
            (maintenance / 'current-maintenance.json').write_bytes(file_bytes(pointer))
            bundle, sources = load_source(root)
            output = root / 'runtime'
            write_bundle(bundle, output, sources)
            for name, document in bundle.items():
                self.assertEqual((output / name).read_bytes(), file_bytes(document))
            self.assertNotIn(b'Q:/old/personal/path', (output / MANIFEST_FILE).read_bytes())
            pointer['active_json'] = '../outside.json'
            (maintenance / 'current-maintenance.json').write_bytes(file_bytes(pointer))
            with self.assertRaisesRegex(ValueError, 'escapes'):
                load_source(root)


if __name__ == '__main__':
    unittest.main()
