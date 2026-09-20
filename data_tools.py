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
ZONE4_MAX = {'恶魔': 2, 'ssc': 5, '爱音': 4, '玻璃': 3, 'f5': 3, '莫斯勒': 3,
             '大超': 3, '狼崽': 5, 'fe3': 5, '火山': 5, '风扇': 5, '帕梅': 5,
             'gtr50': 5, '600lt': 5, '5n': 4}


def read_json(path):
    with Path(path).open(encoding='utf-8') as source:
        return json.load(source)


def json_text(value):
    return json.dumps(value, ensure_ascii=False, separators=(',', ':'), allow_nan=False)


def is_time(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and value > 0


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
