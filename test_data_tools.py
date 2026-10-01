"""Regression tests for reviewed updates and lossless maintenance operations."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import contextlib
import io

import openpyxl
from apply_changes import apply_changes
from data_tools import ROOT, atomic_write, read_json, star_limits
from diff_workbooks import compare_workbooks
from export_xlsx import build_workbook
from format_json import format_data
from sync_zones import ACTION_KEYS, main as sync_main, sync
from validate_data import validate_data
from xlsx_tools import load_workbook_data


def empty_tiers():
    """两区 × 四档的空骨架；新校验要求四区、五区与四个档位都必须显式存在"""
    return {zone: {tier: [] for tier in ('理论', '高手', '普通', '自动')} for zone in ('五区', '四区')}


def fixture():
    return {'_version': 1, '_comment': 'quote " and \\ and\nnewline', 'tier_info': {},
            'extra': {'keep': True}, 'tracks': [
                {'大地图': big, '小地图': 'Same', 'note': 'keep " me', **empty_tiers()}
                for big in ('A', 'B')]}


CARS = {'cars': [{'title': name, 'nickname': name, 'zones': ['五区', '四区']}
                 for name in ('X', 'Y', 'Z', '恶魔')]}

# 统一规则后暴露的既有违规（2026-09-28）；2026-10-01 已由用户决定处理完毕：
#   肥龙 min 4→3、21c min 3→2（规则）、删除 21c★1 全部条目 8 条、biome 加入五区车池。
# 此列表应保持为空——一旦出现内容，说明实库又有了违反 star_rule / 车池的条目。
PENDING_RULE_VIOLATIONS = []


def sc_fixture():
    """两区齐全的赛道骨架, 供特殊跑法透视表测试使用"""
    return {'_version': 1, 'tracks': [
        {'大地图': big, '小地图': 'Same', **empty_tiers()} for big in ('A', 'B')]}


def change(**overrides):
    value = {'accepted': True, 'big': 'A', 'small': 'Same', 'zone': '五区',
             'tier': '高手', 'car': 'X', 'stars': 6, 'sc': False, 'sc_type': None,
             'old_present': False, 'new_present': True, 'old': None, 'new': 20}
    value.update(overrides)
    return value


def report(*changes):
    return {'version': 1, 'changes': list(changes), 'structure': []}


SYNC_CARS = {'cars': [{'title': name, 'nickname': name, 'score': 4000, 'zones': ['五区', '四区']}
                      for name in ('X', 'Y', 'Z')]}


def expert(name, time, stars=6):
    return {'cars': [{'name': name, 'stars': stars}], 'time': time}


def sync_track(expert5, expert4):
    """单条赛道骨架；普通档自动按高手档补同车同星镜像，保证初始状态可通过校验"""
    def tiers(expert_entries):
        return {'理论': [], '高手': list(expert_entries),
                '普通': [{'cars': [dict(entry['cars'][0])]} for entry in expert_entries if not entry.get('sc')],
                '自动': []}
    return {'大地图': 'A', '小地图': 'Same', '五区': tiers(expert5), '四区': tiers(expert4)}


class SyncZonesTests(unittest.TestCase):
    """三个改动分支都会写入理论/高手档，必须回排升序，否则写出「成绩乱序」的库"""

    def test_create_inserts_faster_value_in_order(self):
        data = {'tracks': [sync_track([expert('X', 20), expert('Y', 30)],
                                     [expert('Z', 10), expert('X', 20), expert('Y', 30)])]}
        self.assertEqual(validate_data(data, SYNC_CARS)[0], [])
        changes, _ = sync(data, SYNC_CARS)
        self.assertEqual(len(changes['创建']), 1)
        self.assertEqual([e['time'] for e in data['tracks'][0]['五区']['高手']], [10, 20, 30])
        self.assertEqual(validate_data(data, SYNC_CARS)[0], [])

    def test_placeholder_fill_moves_entry_to_sorted_position(self):
        placeholder = {'cars': [{'name': 'X', 'stars': 6}]}
        data = {'tracks': [sync_track([expert('Y', 30), placeholder],
                                     [expert('X', 10), expert('Y', 30)])]}
        self.assertEqual(validate_data(data, SYNC_CARS)[0], [])
        changes, _ = sync(data, SYNC_CARS)
        self.assertEqual(len(changes['填占位']), 1)
        self.assertEqual([(e['cars'][0]['name'], e['time']) for e in data['tracks'][0]['五区']['高手']],
                         [('X', 10), ('Y', 30)])
        self.assertEqual(validate_data(data, SYNC_CARS)[0], [])

    def test_slower_value_overwrite_moves_entry_to_sorted_position(self):
        data = {'tracks': [sync_track([expert('X', 20), expert('Y', 25)],
                                     [expert('Y', 10), expert('X', 20)])]}
        changes, _ = sync(data, SYNC_CARS)
        self.assertEqual(len(changes['覆盖慢值']), 1)
        self.assertEqual([e['time'] for e in data['tracks'][0]['五区']['高手']], [10, 20])
        self.assertEqual(validate_data(data, SYNC_CARS)[0], [])

    def test_second_run_is_a_no_op(self):
        data = {'tracks': [sync_track([expert('X', 20), expert('Y', 30)],
                                     [expert('Z', 10), expert('X', 20), expert('Y', 30)])]}
        sync(data, SYNC_CARS)
        changes, _ = sync(data, SYNC_CARS)
        self.assertEqual(sum(len(entries) for entries in changes.values()), 0)

    def test_expert_mirror_is_added_only_for_non_special_routes(self):
        """SC 条目不补普通镜像（与 apply_changes 同一口径；validate 拦不住这类多余镜像）"""
        route = {'cars': [{'name': 'Y', 'stars': 6}], 'time': 21, 'sc': True, 'sc_type': '跳图'}
        data = {'tracks': [sync_track([], [expert('X', 20), route])]}
        self.assertEqual(validate_data(data, SYNC_CARS)[0], [])
        changes, _ = sync(data, SYNC_CARS)
        self.assertEqual(len(changes['创建']), 2)
        self.assertEqual(len(changes['镜像']), 1)
        self.assertIn('X★6', changes['镜像'][0])
        self.assertEqual([e['cars'][0]['name'] for e in data['tracks'][0]['五区']['普通']], ['X'])
        self.assertEqual(validate_data(data, SYNC_CARS)[0], [])

    def test_special_route_only_entry_adds_no_mirror(self):
        route = {'cars': [{'name': 'X', 'stars': 6}], 'time': 20, 'sc': True, 'sc_type': '跳图'}
        data = {'tracks': [sync_track([], [route])]}
        changes, _ = sync(data, SYNC_CARS)
        self.assertEqual(len(changes['创建']), 1)
        self.assertEqual(changes['镜像'], [])
        self.assertEqual(data['tracks'][0]['五区']['普通'], [])
        self.assertEqual(validate_data(data, SYNC_CARS)[0], [])

    def test_single_zone_car_is_skipped_without_changing_data(self):
        cars = deepcopy(SYNC_CARS)
        cars['cars'][0]['zones'] = ['五区']
        data = {'tracks': [sync_track([expert('X', 20)], [])]}
        original = deepcopy(data)
        changes, _ = sync(data, cars)
        self.assertEqual(data, original)
        self.assertEqual(sum(len(changes[k]) for k in ACTION_KEYS), 0)
        self.assertIn('不在四区车池', changes['跳过'][0])
        self.assertIn('sc=False sc_type=None', changes['跳过'][0])

    def test_stars_outside_other_zone_range_are_skipped(self):
        cars = deepcopy(SYNC_CARS)
        cars['cars'][0]['star_rule'] = {'min': 2, 'max': 6, 'zone4Max': 4}
        data = {'tracks': [sync_track([expert('X', 20, stars=5)], [])]}
        original = deepcopy(data)
        changes, _ = sync(data, cars)
        self.assertEqual(data, original)
        self.assertIn('四区星级范围 2-4', changes['跳过'][0])

    def test_theory_without_stars_and_score_gate_are_preserved(self):
        cars = deepcopy(SYNC_CARS)
        cars['cars'][0]['star_rule'] = {'min': 2, 'zone4Max': 4}
        cars['cars'][1]['score'] = 4300
        data = {'tracks': [sync_track([], [])]}
        data['tracks'][0]['五区']['理论'] = [
            {'cars': [{'name': 'X'}], 'time': 20}, {'cars': [{'name': 'Y'}], 'time': 21}]
        changes, _ = sync(data, cars)
        target = data['tracks'][0]['四区']['理论']
        self.assertEqual([e['cars'][0]['name'] for e in target], ['X'])
        self.assertIsNone(target[0]['cars'][0].get('stars'))
        self.assertEqual(len(changes['创建']), 1)

    def test_preexisting_violation_is_not_hidden_by_skip(self):
        cars = deepcopy(SYNC_CARS)
        cars['cars'][0]['zones'] = ['五区']
        data = {'tracks': [sync_track([], [expert('X', 20)])]}
        original = deepcopy(data)
        with self.assertRaisesRegex(ValueError, '同步前校验失败'):
            sync(data, cars)
        self.assertEqual(data, original)

    def test_cli_dry_run_write_and_source_drift(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            source, cars = directory / 'data.json', directory / 'cars.json'
            original = {'tracks': [sync_track([expert('X', 20)], [])]}
            source.write_text(json.dumps(original), encoding='utf-8')
            cars.write_text(json.dumps(SYNC_CARS), encoding='utf-8')
            args = ['--input', str(source), '--cars', str(cars)]
            before = source.read_bytes()
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(sync_main(args), 0)
            self.assertEqual(source.read_bytes(), before)
            self.assertFalse(list(directory.glob('*.bak')))

            def drift(data, car_data, max_score):
                result = sync(data, car_data, max_score)
                source.write_text(json.dumps(original) + '\n', encoding='utf-8')
                return result

            with patch('sync_zones.sync', side_effect=drift), patch('sync_zones.atomic_write') as write:
                with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                    with self.assertRaises(SystemExit) as error:
                        sync_main(args + ['--write'])
                self.assertEqual(error.exception.code, 1)
                write.assert_not_called()
            self.assertEqual(read_json(source), original)
            self.assertFalse(list(directory.glob('*.bak')))
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(sync_main(args + ['--write']), 0)
                self.assertEqual(sync_main(args + ['--write']), 0)
            self.assertEqual(len(list(directory.glob('*.bak'))), 1)
            self.assertEqual(read_json(source)['tracks'][0]['四区']['高手'][0]['time'], 20)

    def test_cli_only_skips_do_not_count_as_writes(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            source, cars = directory / 'data.json', directory / 'cars.json'
            car_data = deepcopy(SYNC_CARS)
            car_data['cars'][0]['zones'] = ['五区']
            source.write_text(json.dumps({'tracks': [sync_track([expert('X', 20)], [])]}), encoding='utf-8')
            cars.write_text(json.dumps(car_data), encoding='utf-8')
            before = source.read_bytes()
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(sync_main(['--input', str(source), '--cars', str(cars), '--write']), 0)
            self.assertIn('跳过 (1)', output.getvalue())
            self.assertIn('合计变更 0 条', output.getvalue())
            self.assertEqual(source.read_bytes(), before)
            self.assertFalse(list(directory.glob('*.bak')))


def structural_data():
    """结构完整（两区 × 四档）的单赛道数据，用于结构性错误测试"""
    return {'tracks': [{'大地图': 'A', '小地图': 'Same', 'note': 'keep', **empty_tiers()}]}


class ValidationStructureTests(unittest.TestCase):
    """结构校验：缺区/缺档/类型错误必须报错，SC 只能落在理论、高手档"""

    def test_complete_skeleton_passes(self):
        data = structural_data()
        self.assertEqual(validate_data(data, CARS)[0], [])
        # 空列表合法——档位存在即可，不要求有内容
        self.assertEqual(sum(validate_data(data, CARS)[1].values()), 0)

    def test_missing_zone_is_reported(self):
        for zone in ('五区', '四区'):
            data = structural_data()
            del data['tracks'][0][zone]
            errors = validate_data(data, CARS)[0]
            self.assertIn(f'缺{zone}', errors[0], zone)

    def test_wrong_zone_type_is_reported(self):
        data = structural_data()
        data['tracks'][0]['四区'] = []
        self.assertIn('无效四区结构', validate_data(data, CARS)[0][0])

    def test_missing_tier_is_reported(self):
        for zone in ('五区', '四区'):
            for tier in ('理论', '高手', '普通', '自动'):
                data = structural_data()
                del data['tracks'][0][zone][tier]
                errors = validate_data(data, CARS)[0]
                self.assertIn(f'缺档位: {("A", "Same")} {zone}/{tier}', errors[0], (zone, tier))

    def test_wrong_tier_type_is_reported(self):
        for tier in ('理论', '高手', '普通', '自动'):
            for bad in (None, {}, 3, 'wrong'):
                data = structural_data()
                data['tracks'][0]['五区'][tier] = bad
                self.assertIn('无效档位结构', validate_data(data, CARS)[0][0])

    def test_malformed_entries_return_errors_instead_of_crashing(self):
        for entry in (None, {'cars': None}, {'cars': [None]}, {'cars': [{}]},
                      {'cars': [{'name': 'X', 'stars': []}]}):
            data = structural_data()
            data['tracks'][0]['五区']['高手'] = [entry]
            self.assertTrue(validate_data(data, CARS)[0])

    def test_unknown_tier_key_is_reported_but_unknown_fields_are_kept(self):
        data = structural_data()
        data['tracks'][0]['五区']['精英'] = []
        self.assertIn('未知档位: ', validate_data(data, CARS)[0][0])
        # 未知的顶层/赛道扩展字段不受影响（has_special_route / special_route_note 即此类）
        data = structural_data()
        data['tracks'][0]['has_special_route'] = True
        data['tracks'][0]['special_route_note'] = '跳图'
        self.assertEqual(validate_data(data, CARS)[0], [])

    def test_special_route_rejected_in_normal_and_auto_tiers(self):
        for zone in ('五区', '四区'):
            for tier in ('普通', '自动'):
                data = structural_data()
                data['tracks'][0][zone][tier] = [
                    {'cars': [{'name': 'X', 'stars': 6}], 'sc': True, 'sc_type': '跳图'}]
                errors = validate_data(data, CARS)[0]
                self.assertEqual(len(errors), 1, (zone, tier, errors))
                self.assertIn('特殊跑法档位错误', errors[0])

    def test_special_route_allowed_in_theory_and_expert_tiers(self):
        for tier, stars in (('理论', None), ('高手', 6)):
            data = structural_data()
            car = {'name': 'X'} if stars is None else {'name': 'X', 'stars': stars}
            data['tracks'][0]['五区'][tier] = [{'cars': [car], 'time': 20, 'sc': True, 'sc_type': '跳图'}]
            if tier == '高手':
                data['tracks'][0]['五区']['普通'] = [{'cars': [{'name': 'X', 'stars': stars}]}]
            self.assertEqual(validate_data(data, CARS)[0], [], tier)


class DataToolsTests(unittest.TestCase):
    def test_format_preserves_unknown_fields_escaping_and_missing_zones(self):
        data = fixture()
        self.assertEqual(json.loads(format_data(data)), data)
        self.assertEqual(format_data(json.loads(format_data(data))), format_data(data))
        with self.assertRaises(ValueError):
            format_data({'time': float('nan')})

    def test_real_data_validation_and_format(self):
        data = read_json(ROOT / 'gauntlet_data.json')
        errors, counts = validate_data(data, read_json(ROOT / 'cars.json'))
        self.assertGreater(sum(counts.values()), 0)
        self.assertEqual(json.loads(format_data(data)), data)
        # 结构错误必须为 0；规则违规单独核对，见 PENDING_RULE_VIOLATIONS 的说明
        rule = [e for e in errors if e.startswith(('星级', '车名不在'))]
        self.assertEqual([e for e in errors if e not in rule], [])
        self.assertEqual(rule, PENDING_RULE_VIOLATIONS)

    def test_rejected_changes_and_no_source_mutation(self):
        data = fixture()
        original = deepcopy(data)
        result, logs = apply_changes(data, report(change(accepted=False)), CARS)
        self.assertEqual(result, original)
        self.assertEqual(logs, [])
        apply_changes(data, report(change()), CARS)
        self.assertEqual(data, original)

    def test_placeholder_fill_mirror_and_composite_track_key(self):
        data = fixture()
        data['tracks'][0]['五区']['高手'] = [{'cars': [{'name': 'X', 'stars': 6}], 'note': 'retain'}]
        result, _ = apply_changes(data, report(change()), CARS)
        tiers = result['tracks'][0]['五区']
        self.assertEqual(len(tiers['高手']), 1)
        self.assertEqual(tiers['高手'][0]['note'], 'retain')
        self.assertEqual(tiers['高手'][0]['time'], 20)
        self.assertEqual(len(tiers['普通']), 1)
        self.assertEqual(result['tracks'][1]['五区']['高手'], [])

    def test_theory_and_sc_do_not_add_mirrors(self):
        for value in (change(tier='理论'), change(sc=True, sc_type='跳图')):
            result, _ = apply_changes(fixture(), report(value), CARS)
            self.assertEqual(result['tracks'][0]['五区']['普通'], [])

    def test_sc_placeholder_fill_accepts_absent_old_and_keeps_route(self):
        """sc 占位条目(有 sc_type 无 time)对应 xlsx 空单元格, 填值应视作新增而非旧值不匹配"""
        data = fixture()
        data['tracks'][0]['五区']['理论'] = [{'cars': [{'name': 'X'}], 'sc': True, 'sc_type': '跳图'}]
        result, _ = apply_changes(data, report(
            change(tier='理论', stars=None, sc=True, sc_type='跳图', new=15)), CARS)
        entries = result['tracks'][0]['五区']['理论']
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]['sc_type'], '跳图')
        self.assertEqual(entries[0]['time'], 15)
        self.assertEqual(result['tracks'][0]['五区']['普通'], [])

    def test_deletion_removes_expert_mirror_and_slower_update_is_explicit(self):
        data, _ = apply_changes(fixture(), report(change()), CARS)
        slower = change(old_present=True, old=20, new=21)
        updated, _ = apply_changes(data, report(slower), CARS)
        self.assertEqual(updated['tracks'][0]['五区']['高手'][0]['time'], 21)
        deleted, _ = apply_changes(data, report(change(old_present=True, old=20, new=None, new_present=False)), CARS)
        self.assertEqual(deleted['tracks'][0]['五区']['高手'], [])
        self.assertEqual(deleted['tracks'][0]['五区']['普通'], [])

    def test_conflicts_drift_unknown_car_invalid_time_and_stars_fail(self):
        data, _ = apply_changes(fixture(), report(change()), CARS)
        with self.assertRaisesRegex(ValueError, '旧值不匹配'):
            apply_changes(data, report(change(old_present=True, old=19)), CARS)
        with self.assertRaisesRegex(ValueError, '多个改动'):
            apply_changes(fixture(), report(change(), change(new=21)), CARS)
        for value in (change(car='missing'), change(stars=7), change(new=True), change(new=-1), change(accepted='true')):
            with self.assertRaises(ValueError):
                apply_changes(fixture(), report(value), CARS)

    def test_sorting_and_special_route_identity(self):
        result, _ = apply_changes(fixture(), report(change(new=30), change(car='Y', new=20),
                                                   change(tier='理论', sc=True, sc_type='跳图', new=10),
                                                   change(tier='理论', sc=True, sc_type='滑雪', new=11)), CARS)
        self.assertEqual([e['time'] for e in result['tracks'][0]['五区']['高手']], [20, 30])
        result, _ = apply_changes(result, report(change(tier='理论', sc=True, sc_type='跳图', old_present=True, old=10, new=9)), CARS)
        self.assertEqual([e['time'] for e in result['tracks'][0]['五区']['理论']], [9, 11])

    def test_special_route_pivot_sheets_share_rows_with_per_tier_columns(self):
        data, _ = apply_changes(sc_fixture(), report(
            change(tier='理论', car='X', stars=None, sc=True, sc_type='跳图', new=20),
            change(tier='理论', car='Y', stars=None, sc=True, sc_type='跳图', new=21),
            change(zone='四区', tier='高手', sc=True, sc_type='跳图', new=19),
            change(big='B', sc=True, sc_type='滑雪', new=30)), CARS)
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'data.xlsx'
            workbook, _ = build_workbook(data['tracks'])
            workbook.save(path)
            workbook.close()
            sheets = load_workbook_data(path)
        for zone in ('五区', '四区'):
            for tier in ('理论', '高手'):
                name = f'{zone}_{tier}_特殊跑法'
                self.assertIn(name, sheets)
                # 全部跑法组合在四张表都出现, 空行可直接填值
                self.assertEqual(set(sheets[name]['rows']), {('A', 'Same', '跳图'), ('B', 'Same', '滑雪')}, name)
        # 列集按区档各自收集: 理论档无星列, 高手档带星列
        self.assertEqual(sheets['五区_理论_特殊跑法']['headers'], ['X', 'Y'])
        self.assertEqual(sheets['五区_高手_特殊跑法']['headers'], ['X★6'])
        self.assertEqual(sheets['四区_理论_特殊跑法']['headers'], [])
        self.assertEqual(sheets['四区_高手_特殊跑法']['headers'], ['X★6'])
        # 有值格只落在本区本档的列上
        self.assertEqual(sheets['五区_理论_特殊跑法']['rows'][('A', 'Same', '跳图')], {'X': 20, 'Y': 21})
        self.assertEqual(sheets['五区_理论_特殊跑法']['rows'][('B', 'Same', '滑雪')], {})
        self.assertEqual(sheets['五区_高手_特殊跑法']['rows'][('B', 'Same', '滑雪')], {'X★6': 30})
        self.assertEqual(sheets['五区_高手_特殊跑法']['rows'][('A', 'Same', '跳图')], {})
        self.assertEqual(sheets['四区_高手_特殊跑法']['rows'][('A', 'Same', '跳图')], {'X★6': 19})
        self.assertEqual(sheets['四区_理论_特殊跑法']['rows'][('A', 'Same', '跳图')], {})
        # 只有特殊跑法成绩的车不占主表列
        self.assertEqual(sheets['五区_理论']['headers'], [])
        self.assertEqual(sheets['五区_高手']['headers'], [])
        self.assertEqual(sheets['四区_理论']['headers'], [])

    def test_special_route_edit_review_apply_round_trip(self):
        data, _ = apply_changes(sc_fixture(), report(
            change(tier='理论', car='X', stars=None, sc=True, sc_type='跳图', new=20),
            change(tier='理论', car='Y', stars=None, sc=True, sc_type='跳图', new=21)), CARS)
        with tempfile.TemporaryDirectory() as temp:
            base, user = [Path(temp) / name for name in ('base.xlsx', 'user.xlsx')]
            workbook, _ = build_workbook(data['tracks'])
            self.assertEqual(set(workbook.sheetnames), {f'{zone}_{tier}' for zone in ('五区', '四区')
                             for tier in ('理论', '高手', '普通', '自动')} | {f'{zone}_{tier}_特殊跑法'
                             for zone in ('五区', '四区') for tier in ('理论', '高手')})
            workbook.save(base)
            self.assertEqual(compare_workbooks(load_workbook_data(base), load_workbook_data(base))['changes'], [])
            sheet = workbook['五区_理论_特殊跑法']
            # 理论档列集无星, 两车按成绩升序排
            self.assertEqual(sheet.cell(1, 4).value, 'X')
            self.assertEqual(sheet.cell(1, 5).value, 'Y')
            self.assertEqual(sheet.cell(2, 4).value, 20)
            sheet.cell(2, 4).value = 19.5      # 改值
            sheet.cell(2, 5).value = 22        # 改值
            workbook.save(user)
            workbook.close()
            changes = compare_workbooks(load_workbook_data(base), load_workbook_data(user))
            self.assertEqual(len(changes['changes']), 2)
            for finding in changes['changes']:
                self.assertTrue(finding['sc'])
                self.assertEqual(finding['sc_type'], '跳图')
                self.assertEqual((finding['zone'], finding['tier']), ('五区', '理论'))
                self.assertIsNone(finding['stars'])
                finding['accepted'] = True
            result, _ = apply_changes(data, changes, CARS)
            times = {e['cars'][0]['name']: e['time'] for e in result['tracks'][0]['五区']['理论']}
            self.assertEqual(times, {'X': 19.5, 'Y': 22})
            # 删值: 清空 Y 的单元格 → 删除条目
            fresh, _ = build_workbook(result['tracks'])
            fresh['五区_理论_特殊跑法'].cell(2, 5).value = None
            fresh.save(base)
            fresh.close()
            deletion = compare_workbooks(load_workbook_data(user), load_workbook_data(base))
            self.assertEqual([c['kind'] for c in deletion['changes']], ['deleted'])
            deletion['changes'][0]['accepted'] = True
            trimmed, _ = apply_changes(result, deletion, CARS)
            self.assertEqual(len(trimmed['tracks'][0]['五区']['理论']), 1)

    def test_special_route_high_tier_keeps_starred_columns(self):
        """高手档带星条目进高手表带星列, 且不混入理论表"""
        data, _ = apply_changes(sc_fixture(), report(
            change(tier='高手', car='X', stars=6, sc=True, sc_type='跳图', new=20),
            change(tier='理论', car='Y', stars=None, sc=True, sc_type='跳图', new=21)), CARS)
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'data.xlsx'
            workbook, _ = build_workbook(data['tracks'])
            workbook.save(path)
            workbook.close()
            sheets = load_workbook_data(path)
        self.assertEqual(sheets['五区_理论_特殊跑法']['headers'], ['Y'])
        self.assertEqual(sheets['五区_高手_特殊跑法']['headers'], ['X★6'])
        self.assertEqual(sheets['五区_理论_特殊跑法']['rows'][('A', 'Same', '跳图')], {'Y': 21})
        self.assertEqual(sheets['五区_高手_特殊跑法']['rows'][('A', 'Same', '跳图')], {'X★6': 20})

    def test_validation_requires_known_special_route_type(self):
        data, _ = apply_changes(sc_fixture(), report(change(tier='理论', sc=True, sc_type='跳图', new=20)), CARS)
        entry = data['tracks'][0]['五区']['理论'][0]
        self.assertEqual(validate_data(data, CARS)[0], [])
        for sc_type, message in ((None, '缺类型'), ('jump', '未知')):
            entry['sc_type'] = sc_type
            errors = validate_data(data, CARS)[0]
            self.assertTrue(errors, sc_type)
            self.assertIn(message, errors[0])

    def test_expert_and_explicit_mirror_changes_share_original_snapshot(self):
        mirror = change(tier='普通', new='✓')
        result, _ = apply_changes(fixture(), report(change(), mirror), CARS)
        self.assertEqual(len(result['tracks'][0]['五区']['普通']), 1)
        deletion = change(old_present=True, old=20, new_present=False, new=None)
        mirror_deletion = change(tier='普通', old_present=True, old='✓', new_present=False, new=None)
        result, _ = apply_changes(result, report(deletion, mirror_deletion), CARS)
        self.assertEqual(result['tracks'][0]['五区']['普通'], [])

    def test_diff_review_apply_export_end_to_end(self):
        data, _ = apply_changes(fixture(), report(change(tier='理论')), CARS)
        with tempfile.TemporaryDirectory() as temp:
            base, user = [Path(temp) / name for name in ('base.xlsx', 'user.xlsx')]
            workbook, _ = build_workbook(data['tracks'])
            workbook.save(base)
            workbook['五区_理论'].cell(2, 3).value = 19
            workbook.save(user)
            workbook.close()
            changes = compare_workbooks(load_workbook_data(base), load_workbook_data(user))
            self.assertEqual(len(changes['changes']), 1)
            self.assertEqual(changes['changes'][0]['kind'], 'faster')
            self.assertFalse(changes['changes'][0]['accepted'])
            changes['changes'][0]['accepted'] = True
            result, _ = apply_changes(data, changes, CARS)
            workbook, _ = build_workbook(result['tracks'])
            workbook.save(base)
            workbook.close()
            self.assertEqual(compare_workbooks(load_workbook_data(base), load_workbook_data(user))['changes'], [])

    def test_columns_can_move_and_missing_columns_are_not_deletions(self):
        data, _ = apply_changes(fixture(), report(change(), change(car='Y', new=21)), CARS)
        with tempfile.TemporaryDirectory() as temp:
            base, user = [Path(temp) / name for name in ('base.xlsx', 'user.xlsx')]
            workbook, _ = build_workbook(data['tracks'])
            workbook.save(base)
            sheet = workbook['五区_高手']
            for row in range(1, sheet.max_row + 1):
                left, right = sheet.cell(row, 3).value, sheet.cell(row, 4).value
                sheet.cell(row, 3).value = right
                sheet.cell(row, 4).value = left
            workbook.save(user)
            self.assertEqual(compare_workbooks(load_workbook_data(base), load_workbook_data(user))['changes'], [])
            sheet.delete_cols(4)
            workbook.save(user)
            workbook.close()
            changes = compare_workbooks(load_workbook_data(base), load_workbook_data(user))
            self.assertEqual(changes['changes'], [])
            self.assertEqual(changes['structure'][0]['kind'], 'column_missing')

    def test_shared_car_rules_match_frontend_semantics(self):
        """star_limits 与前端 getStarRange 同口径：min 两区通用、zone4Max 覆盖 max、上限不低于下限"""
        self.assertEqual(star_limits({'star_rule': {'min': 3, 'max': 6, 'zone4Max': 4}}, '五区'), (3, 6))
        self.assertEqual(star_limits({'star_rule': {'min': 3, 'max': 6, 'zone4Max': 4}}, '四区'), (3, 4))
        self.assertEqual(star_limits({'star_rule': {'min': 5, 'max': 5}}, '五区'), (5, 5))
        self.assertEqual(star_limits(None, '四区'), (1, 6))
        self.assertEqual(star_limits({'star_rule': {}}, '五区'), (1, 6))
        # zone4Max 低于 min 时前端取 max(max, min)，此处必须一致
        self.assertEqual(star_limits({'star_rule': {'min': 6, 'zone4Max': 4}}, '四区'), (6, 6))

    def test_zone_pool_and_star_limits_are_validated(self):
        """车池与星级规则来自传入的车辆库，与前端共用同一份定义"""
        data, _ = apply_changes(fixture(), report(change()), CARS)
        entry = data['tracks'][0]['五区']['高手'][0]['cars'][0]
        entry['stars'] = 7
        self.assertIn('星级超出 1-6', validate_data(data, CARS)[0][0])
        entry['stars'] = 6

        outside = deepcopy(CARS)
        outside['cars'][0]['zones'] = ['四区']          # X 移出五区车池
        self.assertIn('车名不在五区车池', validate_data(data, outside)[0][0])

        below = deepcopy(CARS)
        below['cars'][0]['star_rule'] = {'min': 4}      # X 最低 4 星
        entry['stars'] = 3
        self.assertTrue(any('星级越界' in e for e in validate_data(data, below)[0]))

        above = deepcopy(CARS)
        above['cars'][0]['star_rule'] = {'max': 5}      # X 最高 5 星
        entry['stars'] = 6
        self.assertTrue(any('星级越界' in e for e in validate_data(data, above)[0]))

    def test_validation_detects_each_business_error(self):
        data, _ = apply_changes(fixture(), report(change()), CARS)
        for mode in ('duplicate', 'star', 'name', 'mirror', 'order', 'time'):
            invalid = deepcopy(data)
            tiers = invalid['tracks'][0]['五区']
            if mode == 'duplicate':
                tiers['高手'].append(deepcopy(tiers['高手'][0]))
            elif mode == 'star':
                tiers['高手'][0]['cars'][0]['stars'] = 0
            elif mode == 'name':
                tiers['高手'][0]['cars'][0]['name'] = 'missing'
            elif mode == 'mirror':
                tiers['普通'].clear()
            elif mode == 'order':
                tiers['理论'] = [{'cars': [{'name': 'X'}], 'time': 30}, {'cars': [{'name': 'Y'}], 'time': 20}]
            else:
                tiers['高手'][0]['time'] = float('inf')
            self.assertTrue(validate_data(invalid, CARS)[0], mode)

    def test_atomic_backup_and_write_failure(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'data.json'
            path.write_text('original', encoding='utf-8')
            atomic_write(path, 'replacement')
            self.assertEqual(path.read_text(), 'replacement')
            self.assertEqual(next(Path(temp).glob('*.bak')).read_text(), 'original')
            with self.assertRaises(OSError):
                atomic_write(Path(temp) / 'missing' / 'file.json', 'bad')
            self.assertEqual(path.read_text(), 'replacement')

    def test_workbook_export_and_keyed_reordering(self):
        data, _ = apply_changes(fixture(), report(change()), CARS)
        with tempfile.TemporaryDirectory() as temp:
            left, right = (Path(temp) / n for n in ('left.xlsx', 'right.xlsx'))
            workbook, _ = build_workbook(data['tracks'])
            workbook.save(left)
            # Swap track rows with the same small-map name; keys must preserve the big map.
            sheet = workbook['五区_高手']
            rows = [[c.value for c in sheet[row]] for row in (2, 3)]
            for r, values in zip((2, 3), reversed(rows)):
                for c, value in enumerate(values, 1):
                    sheet.cell(r, c).value = value
            workbook.save(right)
            workbook.close()
            self.assertEqual(compare_workbooks(load_workbook_data(left), load_workbook_data(right))['changes'], [])
            workbook = openpyxl.load_workbook(right)
            workbook.remove(workbook['五区_高手'])
            workbook.save(right)
            workbook.close()
            diff = compare_workbooks(load_workbook_data(left), load_workbook_data(right))
            self.assertEqual(diff['changes'], [])
            self.assertEqual(diff['structure'][0]['kind'], 'sheet_missing')

    def test_duplicate_columns_rows_and_formulas_rejected(self):
        for mode in ('column', 'row', 'formula'):
            with tempfile.TemporaryDirectory() as temp:
                path = Path(temp) / 'bad.xlsx'
                workbook, _ = build_workbook(fixture()['tracks'])
                sheet = workbook['五区_理论']
                if mode == 'column':
                    sheet.cell(1, 3, 'X')
                    sheet.cell(1, 4, 'X')
                elif mode == 'row':
                    sheet.cell(3, 1, 'A')
                else:
                    sheet.cell(2, 3, '=1+1')
                workbook.save(path)
                workbook.close()
                with self.assertRaises(ValueError):
                    load_workbook_data(path)

    def test_cli_review_to_preview_and_protected_inputs(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            source, review, cars, preview = [directory / name for name in ('source.json', 'review.json', 'cars.json', 'preview.json')]
            source.write_text(json.dumps(fixture(), ensure_ascii=False), encoding='utf-8')
            cars.write_text(json.dumps(CARS, ensure_ascii=False), encoding='utf-8')
            review.write_text(json.dumps(report(change()), ensure_ascii=False), encoding='utf-8')
            digest = hashlib.sha256(source.read_bytes()).digest()
            command = [sys.executable, str(ROOT / 'apply_changes.py'), '--input', str(source), '--cars', str(cars), '--review', str(review)]
            result = subprocess.run(command, cwd=directory, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse(preview.exists())
            result = subprocess.run(command + ['--output', str(preview)], cwd=directory, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(read_json(preview)['tracks'][0]['五区']['高手'][0]['time'], 20)
            self.assertEqual(hashlib.sha256(source.read_bytes()).digest(), digest)
            self.assertNotEqual(subprocess.run(command + ['--output', str(source)], capture_output=True).returncode, 0)
            result = subprocess.run(command + ['--write'], capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(list(directory.glob('source.json.*.bak')))


if __name__ == '__main__':
    unittest.main()
