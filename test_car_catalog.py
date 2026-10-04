from copy import deepcopy
import unittest
from data_tools import read_json, ROOT, validate_car_catalog


class CatalogTests(unittest.TestCase):
    def test_current_catalog_is_valid(self):
        self.assertEqual(validate_car_catalog(read_json(ROOT / 'cars.json')), [])

    def test_duplicate_and_conflicting_identities_are_rejected(self):
        original = {'cars': [{'title': 'Car X', 'nickname': 'X', 'zones': ['五区']},
                             {'title': 'Car Y', 'nickname': 'Y', 'zones': ['四区']}]}
        for mode in ('duplicate', 'nickname', 'title_collision', 'alias'):
            cars = deepcopy(original)
            if mode == 'duplicate':
                cars['cars'].append(deepcopy(cars['cars'][0]))
            elif mode == 'nickname':
                cars['cars'][1]['nickname'] = 'X'
            elif mode == 'title_collision':
                cars['cars'][1]['nickname'] = 'Car X'
            else:
                cars['_nickname_map'] = {'X': 'Car Y'}
            self.assertTrue(validate_car_catalog(cars), mode)

    def test_malformed_pools_and_star_rules_are_rejected(self):
        cases = [
            {'zones': ['五区', '五区']}, {'zones': ['三区']}, {'zones': '五区'},
            {'zones': ['五区'], 'nickname': None},
            {'star_rule': {'min': True}}, {'star_rule': {'max': 7}},
            {'star_rule': {'min': 4, 'max': 3}}, {'star_rule': {'min': 4, 'zone4Max': 2}},
            {'star_rule': {'min': 3, 'default': 1}}, {'star_rule': []},
        ]
        for fields in cases:
            cars = {'cars': [dict(title='Car X', nickname='X', **{})]}
            cars['cars'][0].update(fields)
            self.assertTrue(validate_car_catalog(cars), fields)

    def test_special_modification_score_is_not_used_to_infer_rules(self):
        cars = {'cars': [{'title': 'Car X', 'nickname': 'X', 'score': 5000,
                         'zones': ['五区', '四区'], 'star_rule': {'min': 2, 'zone4Max': 3, 'default': 6}}]}
        self.assertEqual(validate_car_catalog(cars), [])


if __name__ == '__main__':
    unittest.main()
