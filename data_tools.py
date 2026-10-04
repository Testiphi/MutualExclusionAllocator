"""Shared identities, paths and safe JSON I/O."""
import json
import math
import os
from pathlib import Path
import shutil
import tempfile
from datetime import datetime

ROOT = Path(__file__).resolve().parent
ZONES = ('五区', '四区')
TIERS = ('理论', '高手', '普通', '自动')
SC_SUFFIX = '特殊跑法'
# 特殊跑法类型白名单: 新增跑法类型须先在此登记（校验脚本据此拦截拼写变体）
SC_TYPES = ('滑栏杆', '滑雪', '跳楼', '跳图', '跳船', '挂桥', '稳定跳图', '旧跳图', '新跳图')


def read_json(path):
    with Path(path).open(encoding='utf-8') as source:
        return json.load(source)


def json_text(value):
    return json.dumps(value, ensure_ascii=False, separators=(',', ':'), allow_nan=False)


def is_time(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and value > 0


def validate_car_catalog(cars):
    """车辆库身份和规则校验；不推导或调整人工指定的特改规则。"""
    errors = []
    if not isinstance(cars, dict) or not isinstance(cars.get('cars'), list):
        return ['车辆库必须包含 cars 列表']
    names, titles = {}, set()
    for index, car in enumerate(cars['cars']):
        label = f'车辆库第{index + 1}项'
        if not isinstance(car, dict) or not isinstance(car.get('title'), str) or not car['title']:
            errors.append(f'无效车辆记录: {label}')
            continue
        title = car['title']
        if title in titles:
            errors.append(f'重复车辆真名: {title}')
        titles.add(title)
        nickname = car.get('nickname')
        if nickname is not None and (not isinstance(nickname, str) or not nickname):
            errors.append(f'无效车辆昵称: {title}')
        for name in (title, nickname):
            if not isinstance(name, str) or not name:
                continue
            if name in names and names[name] != title:
                errors.append(f'车名或昵称冲突: {name}')
            names[name] = title
        zones = car.get('zones', [])
        if (not isinstance(zones, list) or any(zone not in ZONES for zone in zones)
                or len(zones) != len(set(zones))):
            errors.append(f'无效车池定义: {title}')
        if zones and not isinstance(nickname, str):
            errors.append(f'入池车辆缺昵称: {title}')
        rule = car.get('star_rule', {})
        if not isinstance(rule, dict):
            errors.append(f'无效星级规则: {title}')
            continue
        bad = False
        for field in ('min', 'max', 'zone4Max', 'default'):
            if field in rule and (type(rule[field]) is not int or not 1 <= rule[field] <= 6):
                errors.append(f'无效星级规则字段: {title} {field}')
                bad = True
        if not bad:
            minimum, maximum = rule.get('min', 1), rule.get('max', 6)
            if minimum > maximum or minimum > rule.get('zone4Max', maximum):
                errors.append(f'星级上下限倒置: {title}')
            if not minimum <= rule.get('default', maximum) <= maximum:
                errors.append(f'默认星级越界: {title}')
    aliases = cars.get('_nickname_map', {})
    if not isinstance(aliases, dict):
        errors.append('无效昵称映射')
    else:
        for alias, title in aliases.items():
            if not isinstance(alias, str) or not alias or not isinstance(title, str) or title not in titles:
                errors.append(f'无效昵称映射: {alias}')
            elif alias in names and names[alias] != title:
                errors.append(f'昵称映射冲突: {alias}')
    return errors


def car_records(cars):
    """车名 → 车辆记录。车名可为 title、记录自带 nickname 或 `_nickname_map` 别名。

    车池（`zones`）与星级规则（`star_rule`）都挂在记录上，前端与校验共用 cars.json。
    """
    records = {}
    for car in cars['cars']:
        records[car['title']] = car
        if car.get('nickname'):
            records[car['nickname']] = car
    for alias, title in cars.get('_nickname_map', {}).items():
        if title in records:
            records.setdefault(alias, records[title])
    return records


def car_zone_names(cars, zone):
    """给定分区的车池车名（记录顺序，与前端 buildCarRules 的派生口径一致）"""
    return [car['nickname'] for car in cars['cars']
            if car.get('nickname') and zone in (car.get('zones') or [])]


def star_limits(record, zone):
    """该车在指定分区的 (最低, 最高) 可用星级；无规则时 (1, 6)。

    与前端 `index.html` 的 getStarRange 逐条对齐：
    `zone4Max` 覆盖 `max`，`min` 两区通用，且上限不低于下限。
    """
    rule = (record or {}).get('star_rule') or {}
    minimum = rule.get('min') or 1
    maximum = rule.get('max') or 6
    if zone == '四区' and rule.get('zone4Max') is not None:
        maximum = rule['zone4Max']
    return minimum, max(maximum, minimum)


def atomic_write(path, text, backup=True):
    path = Path(path)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', newline='\n', dir=path.parent, delete=False) as target:
            temporary = Path(target.name)
            target.write(text)
            target.flush()
            os.fsync(target.fileno())
        replace_with_backup(temporary, path, backup)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def replace_with_backup(temporary, path, backup=True):
    path = Path(path)
    if backup and path.exists():
        stamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        shutil.copy2(path, path.with_name(f'{path.name}.{stamp}.bak'))
    os.replace(temporary, path)


def atomic_save_workbook(workbook, path):
    """Save and check the XLSX archive before replacing an existing workbook."""
    import zipfile
    path = Path(path)
    descriptor, name = tempfile.mkstemp(suffix='.xlsx', dir=path.parent)
    os.close(descriptor)
    temporary = Path(name)
    try:
        workbook.save(temporary)
        with zipfile.ZipFile(temporary) as archive:
            if archive.testzip() is not None:
                raise ValueError('导出的工作簿损坏')
        replace_with_backup(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def car_key(car):
    return car['name'], car.get('stars')


def entry_sort_key(entry):
    """理论/高手档排序键: 成绩升序, 无 time 的条目(占位)恒排末尾。

    写入这两个档位的工具必须用它回排, 否则会写出「成绩乱序」的库。
    """
    return entry.get('time') is None, entry.get('time') or 0


def parse_sheet_name(title):
    """数据表名 → (zone, tier, sc)；非数据表返回 None

    普通表 `五区_理论`；特殊跑法表 `五区_理论_特殊跑法`（多一列跑法行键）。
    """
    parts = str(title).split('_')
    if len(parts) == 2 and parts[0] in ZONES and parts[1] in TIERS:
        return parts[0], parts[1], False
    if len(parts) == 3 and parts[0] in ZONES and parts[1] in TIERS and parts[2] == SC_SUFFIX:
        return parts[0], parts[1], True
    return None


def parse_column(label):
    if not isinstance(label, str) or not label:
        raise ValueError(f'无效车辆列: {label!r}')
    if '★' in label:
        name, stars = label.rsplit('★', 1)
        if not name:
            raise ValueError(f'无效车辆列: {label!r}')
        return name, int(stars)
    return label, None


def configure_stdout():
    import sys
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
