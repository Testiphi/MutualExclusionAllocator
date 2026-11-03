# -*- coding: utf-8 -*-
"""只读星级曲线复核：Node 执行 index.html 原函数作为生产基准。

python -B -X utf8 _star_curve_fit.py [--refit] [--node PATH]
只用已有 numpy 与 Node；不安装依赖、不写生产参数。
候选仅用训练折拟合，全量拟合仅供人工参考，不能作为折外性能。
"""
import argparse
import collections
import json
from pathlib import Path
import random
import re
import shutil
import statistics
import subprocess
import sys

ROOT = Path(__file__).resolve().parent


def frontend_source(path):
    """只提取指定常量与两个纯函数，结构变化时失败，不退回硬编码。"""
    path = Path(path)
    html = path.read_text(encoding='utf-8')
    if '<script src="race_scores.js"></script>' in html:
        html = (path.parent / 'race_scores.js').read_text(encoding='utf-8')
    constants = {}
    for name in ('STAR_PENALTY_A', 'STAR_PENALTY_B'):
        match = re.search(r'const\s+' + name + r'\s*=\s*([0-9.eE+\-]+)\s*;', html)
        if not match:
            raise ValueError(f'无法提取前端常量 {name}')
        constants[name] = float(match[1])
    functions = []
    for name in ('starPenalty', 'getStarAdjustedScore'):
        match = re.search(r'^    function ' + name + r'\([^\n]*\) \{.*?^    \}', html, re.M | re.S)
        if not match:
            raise ValueError(f'无法提取前端函数 {name}')
        functions.append(match[0])
    return '\n'.join(functions), constants


def predict_batch(requests, functions, constants, node, parameters=None):
    """基准与候选执行同一原函数（含 toFixed(3)），候选只替换 A/B。"""
    a, b = parameters or (constants['STAR_PENALTY_A'], constants['STAR_PENALTY_B'])
    script = (f'const STAR_PENALTY_A={json.dumps(a)}, STAR_PENALTY_B={json.dumps(b)};\n'
              + functions + "\nconst fs=require('node:fs');\n"
              + "const rows=JSON.parse(fs.readFileSync(0,'utf8'));\n"
              + "process.stdout.write(JSON.stringify(rows.map(r=>getStarAdjustedScore(r.points,r.stars))));")
    result = subprocess.run([node, '-e', script], input=json.dumps(requests),
                            capture_output=True, text=True, encoding='utf-8', timeout=30)
    if result.returncode:
        raise ValueError(f'前端函数执行失败: {result.stderr.strip()}')
    return json.loads(result.stdout)


def load_groups(path):
    data = json.loads(Path(path).read_text(encoding='utf-8'))
    groups, sc_groups = collections.defaultdict(dict), collections.defaultdict(dict)
    for track in data['tracks']:
        for zone in ('五区', '四区'):
            for entry in track[zone]['高手']:
                if entry.get('time') is None:
                    continue
                car = entry['cars'][0]
                if car.get('stars') is None:
                    continue
                key = (track['大地图'], track['小地图'], zone, car['name'])
                if entry.get('sc'):
                    sc_groups[(*key, entry.get('sc_type'))][car['stars']] = entry['time']
                else:
                    groups[key][car['stars']] = entry['time']
    return groups, sc_groups


def anchor(points, stars):
    return min(points, key=lambda s: (abs(s - stars), -s))


def opt_shape(train):
    import numpy as np
    distances, ratios, higher = [], [], []
    for points in train.values():
        for stars, actual in points.items():
            remaining = {s: t for s, t in points.items() if s != stars}
            # 插值不依赖 A/B，不纳入曲线训练目标。
            if any(s < stars for s in remaining) and any(s > stars for s in remaining):
                continue
            nearest = anchor(remaining, stars)
            distances.append(abs(stars - nearest))
            ratios.append(remaining[nearest] / actual)
            higher.append(nearest < stars)
    if not distances:
        raise ValueError('训练折缺少外推样本')
    d, q, h = np.array(distances), np.array(ratios), np.array(higher, dtype=bool)
    best = None
    # 连续外推误差选参数；折外报告使用 JS 实际三位小数输出。
    for a in np.arange(0.001, 0.0131, 0.00025):
        for b in np.arange(-0.0001, 0.00251, 0.000125):
            penalty = np.exp(a * d + b * d * d)
            error = float(np.abs(np.where(h, q / penalty, q * penalty) - 1).mean())
            if best is None or error < best[0]:
                best = error, float(a), float(b)
    return best[1:]


def make_folds(multi, seed, count=5):
    # 同赛道同车的双区成绩可能为同步副本，捆绑避免跨训练/验证折。
    identities = sorted({(key[0], key[1], key[3]) for key in multi})
    if len(identities) < count:
        raise ValueError('独立赛道/车辆组不足五组，无法进行五折交叉验证')
    random.Random(seed).shuffle(identities)
    buckets = [set(identities[i::count]) for i in range(count)]
    return [{key for key in multi if (key[0], key[1], key[3]) in bucket} for bucket in buckets]


def cv(multi, folds, functions, constants, node):
    baseline, candidate, distances = [], [], []
    for test in folds:
        train = {key: points for key, points in multi.items() if key not in test}
        parameters = opt_shape(train)
        requests, actuals = [], []
        for key in sorted(test):
            points = multi[key]
            for stars, actual in sorted(points.items()):
                remaining = {s: t for s, t in points.items() if s != stars}
                requests.append({'points': [{'stars': s, 'time': t} for s, t in remaining.items()], 'stars': stars})
                actuals.append(actual)
                inside = any(s < stars for s in remaining) and any(s > stars for s in remaining)
                distances.append(0 if inside else abs(stars - anchor(remaining, stars)))
        old = predict_batch(requests, functions, constants, node)
        new = predict_batch(requests, functions, constants, node, parameters)
        baseline.extend((pred / actual - 1) * 100 for pred, actual in zip(old, actuals))
        candidate.extend((pred / actual - 1) * 100 for pred, actual in zip(new, actuals))
    return baseline, candidate, distances


def summary(errors):
    absolute = sorted(abs(error) for error in errors)
    return statistics.median(absolute), statistics.mean(absolute), absolute[int(.9 * (len(absolute) - 1))], absolute[-1]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, default=ROOT / 'gauntlet_data.json')
    parser.add_argument('--frontend', type=Path, default=ROOT / 'index.html')
    parser.add_argument('--node', default=shutil.which('node'))
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--refit', action='store_true', help='额外打印全量拟合 JS 常量，不写文件')
    args = parser.parse_args(argv)
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    try:
        if not args.node:
            raise ValueError('未找到 Node，请用 --node 指定已有运行时')
        functions, constants = frontend_source(args.frontend)
        groups, sc_groups = load_groups(args.input)
        multi = {key: points for key, points in groups.items() if len(points) >= 2}
        folds = make_folds(multi, args.seed)
        baseline, candidate, distances = cv(multi, folds, functions, constants, args.node)
        print(f'生产基准: 前端成绩模块原函数，A={constants["STAR_PENALTY_A"]}, B={constants["STAR_PENALTY_B"]}')
        print(f'非 SC 组 {len(groups)}，多星组 {len(multi)}；SC 组 {len(sc_groups)}（不参与拟合和验证）')
        print(f'五折按赛道/车分组（双区捆绑），seed={args.seed}，折外留一预测 {len(baseline)} 个')
        print('候选仅用训练折的外推样本拟合；基准与候选均使用 JS 三位小数输出。')
        print('生产参数可能用过当前数据；此表是固定生产基准的回顾性复核，不代表独立未来样本验证。')
        print('方案 / 绝对相对误差：中位、均值、p90、最大')
        for name, errors in (('当前生产', baseline), ('训练折候选', candidate)):
            print(name + ': ' + ' / '.join(f'{value:.3f}%' for value in summary(errors)))
        print(f'插值样本 {distances.count(0)}，外推样本 {len(distances) - distances.count(0)}')
        a, b = opt_shape(multi)
        print(f'全量拟合（供人工参考，不是折外结果）: A={a:.5f}, B={b:.6f}')
        print('SC 精度未验证；本报告不更新生产曲线。')
        if args.refit:
            print(f'const STAR_PENALTY_A = {a:.5f};\nconst STAR_PENALTY_B = {b:.6f};')
    except ImportError:
        parser.exit(1, '分析失败: 缺少 numpy；未安装任何依赖\n')
    except (OSError, ValueError, KeyError, TypeError, subprocess.TimeoutExpired) as error:
        parser.exit(1, f'分析失败: {error}\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
