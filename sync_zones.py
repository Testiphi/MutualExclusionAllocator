# -*- coding: utf-8 -*-
"""四五区成绩同步：性能分 ≤4200 的车辆，让四区与五区的成绩保持一致。

来源：2026-08-26 用户要求的同步规则（原脚本 `_sync_4200_0826.py`，本文件为其正式版）。

同步规则
--------
- 车辆集：`cars.json` 中 `score <= 4200` 的车（按真名 / nickname / `_nickname_map` 别名匹配）
- 档位：理论 + 高手（含特殊跑法，按 `sc_type` 匹配）
- 键：同赛道同档位下的 `(车名, 星级, sc, sc_type)`
  1. 只有一边有 `time` → 另一边填占位；占位不存在则新建条目
  2. 两边都有 `time` 且不等 → **保留更快值**，慢侧被覆盖（预检会逐条列出被覆盖的慢值）
  3. 两边都是占位 / 只有占位 → 不动
- 仅**非特殊跑法**高手档新建条目时，同区普通档补同车同星镜像（与 `apply_changes.py` 同一口径）
- 三个分支都会改动理论/高手档，故**改动过的列表按成绩升序回排**（占位在末尾），
  再跑一次全库校验；校验不通过则报错且不写文件（避免写出「成绩乱序」的库）

用法
----
    python sync_zones.py                 # 预检：只打印清单，不改任何文件
    python sync_zones.py --write         # 确认后写回（format_json 紧凑格式 + 原子替换 + 自动 .bak）

默认输入为脚本所在目录下的 `gauntlet_data.json` / `cars.json`；显式相对路径相对当前工作目录。
"""
import argparse
import json
import sys
from pathlib import Path

from data_tools import ROOT, atomic_write, configure_stdout, entry_sort_key, read_json
import format_json
from validate_data import validate_data

MAX_SCORE = 4200


def build_score_map(cars):
    """车名（含昵称与别名）→ 性能分"""
    score_map = {}
    for car in cars['cars']:
        score = car.get('score')
        if score is None:
            continue
        score_map[car['title']] = score
        if car.get('nickname'):
            score_map[car['nickname']] = score
    for alias, title in cars.get('_nickname_map', {}).items():
        if title in score_map:
            score_map[alias] = score_map[title]
    return score_map


def find_entry(entries, name, stars, sc, sc_type):
    for entry in entries:
        if len(entry.get('cars', [])) != 1:
            continue
        car = entry['cars'][0]
        if (car.get('name') == name and car.get('stars') == stars
                and bool(entry.get('sc')) == sc and entry.get('sc_type') == sc_type):
            return entry
    return None


def make_entry(name, stars, time, sc, sc_type):
    entry = {'cars': [{'name': name, 'stars': stars}], 'time': time}
    if sc:
        entry['sc'] = True
        if sc_type:
            entry['sc_type'] = sc_type
    return entry


def sync(data, cars, max_score=MAX_SCORE):
    """返回 (changes, stats)；changes 为逐条描述，stats 为动作计数

    改动过的理论/高手列表会被回排升序，并在返回前跑一次全库校验；
    校验失败抛 ValueError（调用方据此中止，不写文件）。
    """
    score_map = build_score_map(cars)
    sync_names = {n for n, s in score_map.items() if s <= max_score}
    changes = {'覆盖慢值': [], '填占位': [], '创建': [], '镜像': []}
    dirty = {}      # id(列表) → 列表：本次改动过的理论/高手列表，需回排升序

    for track in data['tracks']:
        label = f"{track['大地图']}/{track['小地图']}"
        for tier in ('理论', '高手'):
            zone5 = track['五区'].get(tier, [])
            zone4 = track['四区'].get(tier, [])
            keys = set()
            for entries in (zone5, zone4):
                for entry in entries:
                    if len(entry.get('cars', [])) == 1:
                        car = entry['cars'][0]
                        if car['name'] in sync_names:
                            keys.add((car['name'], car.get('stars'),
                                      bool(entry.get('sc')), entry.get('sc_type')))
            for name, stars, sc, sc_type in sorted(keys, key=lambda k: (k[0], k[1] or 0, k[2], k[3] or '')):
                tag = f'{name}★{stars}' if stars else name
                e5 = find_entry(zone5, name, stars, sc, sc_type)
                e4 = find_entry(zone4, name, stars, sc, sc_type)
                t5, t4 = (e5.get('time') if e5 else None), (e4.get('time') if e4 else None)
                if t5 is None and t4 is None:
                    continue
                if t5 is not None and t4 is not None:
                    if t5 == t4:
                        continue
                    # 慢值被覆盖成更快值 → 该条目要往列表前面挪
                    if t5 > t4:
                        fast_zone, fast, slow_zone, slow = '四区', t4, '五区', t5
                        target_zone, target = zone5, e5
                    else:
                        fast_zone, fast, slow_zone, slow = '五区', t5, '四区', t4
                        target_zone, target = zone4, e4
                    target['time'] = fast
                    dirty[id(target_zone)] = target_zone
                    changes['覆盖慢值'].append(
                        f'{label} {tier} {slow_zone} {tag}: {slow} → {fast}（采用{fast_zone}更快值）')
                    continue
                # 只有一边有成绩 → 另一边填占位 / 新建
                if t5 is not None:
                    source, target_zone, target_name = e5, zone4, '四区'
                else:
                    source, target_zone, target_name = e4, zone5, '五区'
                existing = find_entry(target_zone, name, stars, sc, sc_type)
                if existing is not None:
                    assert existing.get('time') is None, f'目标已有值: {label} {tier} {tag}'
                    existing['time'] = source['time']
                    dirty[id(target_zone)] = target_zone
                    changes['填占位'].append(f'{label} {tier} {target_name} {tag}: 填占位 = {source["time"]}')
                else:
                    target_zone.append(make_entry(name, stars, source['time'], sc, sc_type))
                    dirty[id(target_zone)] = target_zone
                    changes['创建'].append(f'{label} {tier} {target_name} {tag}: 新建 = {source["time"]}')
                    if tier == '高手' and not sc:
                        normal = track[target_name]['普通']
                        if find_entry(normal, name, stars, False, None) is None:
                            normal.append({'cars': [{'name': name, 'stars': stars}]})
                            changes['镜像'].append(f'{label} {tier} {target_name} {tag}: 普通档补镜像')
    for entries in dirty.values():
        entries.sort(key=entry_sort_key)
    errors, _ = validate_data(data, cars)
    if errors:
        raise ValueError('同步后校验失败:\n' + '\n'.join(errors))
    return changes, sync_names


def main(argv=None):
    parser = argparse.ArgumentParser(description='同步性能分 ≤4200 车辆的四五区成绩（默认仅预检）')
    parser.add_argument('--input', type=Path, default=ROOT / 'gauntlet_data.json', help='赛道数据 JSON')
    parser.add_argument('--cars', type=Path, default=ROOT / 'cars.json', help='车辆库 JSON')
    parser.add_argument('--max-score', type=int, default=MAX_SCORE, help=f'性能分上限（默认 {MAX_SCORE}）')
    parser.add_argument('--write', action='store_true', help='写回源文件（默认只预检）')
    args = parser.parse_args(argv)
    configure_stdout()
    try:
        data = read_json(args.input)
        cars = read_json(args.cars)
        changes, names = sync(data, cars, args.max_score)
    except (OSError, ValueError, KeyError, TypeError, AssertionError) as error:
        parser.exit(1, f'同步失败: {error}\n')

    total = sum(len(v) for v in changes.values())
    print(f'同步车辆集（score ≤ {args.max_score}）: {len(names)} 个名字')
    for key in ('覆盖慢值', '填占位', '创建', '镜像'):
        print(f'\n{key} ({len(changes[key])}):')
        for line in changes[key]:
            print('  ' + line)
    print(f'\n合计变更 {total} 条')

    if total == 0:
        print('无需变更，未写文件。')
        return 0
    if not args.write:
        print('预检完成（未写文件）；确认后加 --write 写回。')
        return 0

    text = format_json.format_data(data)
    if json.loads(text) != data:
        parser.exit(1, '同步失败: 格式化前后数据不一致\n')
    atomic_write(args.input, text)
    print(f'已写回 {args.input}（{len(text.splitlines())} 行，已自动备份 .bak）')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
