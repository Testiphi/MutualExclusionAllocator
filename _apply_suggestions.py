# -*- coding: utf-8 -*-
"""应用网友建议（review.html 导出的 accepted_suggestions.json）→ gauntlet_data.json
用法: python _apply_suggestions.py [accepted_suggestions.json]
规则:
1. 建议只涉及 理论/高手 档普通跑法（无 sc）的已有条目: 填空占位 或 改值
2. 每条 assert 现状校验: old 必须与 json 当前值一致（数据中途变化则中止, 防止覆盖新数据）
3. 应用后 理论/高手 条目按 time 升序重排（8/27 教训: 位置与成绩一致）
4. 校验 + 格式化由调用方执行（_validate_0823.py + format_json.py）
"""
import sys, json, os
sys.stdout.reconfigure(encoding='utf-8')

FNAME = sys.argv[1] if len(sys.argv) > 1 else 'accepted_suggestions.json'
d = json.load(open('gauntlet_data.json', encoding='utf-8'))
sug = json.load(open(FNAME, encoding='utf-8'))
props = sug.get('proposals', [])
assert isinstance(props, list) and props, f'{FNAME} 无 proposals'

def find_track(name):
    for t in d['tracks']:
        if t['小地图'] == name:
            return t
    raise KeyError(f'赛道不存在: {name}')

def find_entry(track, zone, tier, car, stars):
    for e in track[zone].get(tier, []):
        if e.get('sc'):
            continue
        if len(e['cars']) == 1:
            c = e['cars'][0]
            if c.get('name') == car and (c.get('stars') if c.get('stars') is not None else None) == stars:
                return e
    return None

log = []
for p in props:
    zone, tier = p['zone'], p['tier']
    assert zone in ('五区', '四区') and tier in ('理论', '高手'), f'档位非法: {p}'
    t = find_track(p['track'])
    e = find_entry(t, zone, tier, p['car'], p.get('stars'))
    created = False
    if e is None:
        # 2026-09-02: 地图主导维度模型下理论档可提交全新条目(fill.html 新建建议)
        assert tier == '理论' and p.get('stars') is None, f'新建条目仅限理论档: {p}'
        e = {'cars': [{'name': p['car']}], 'time': p['new']}
        t[zone][tier].append(e)
        created = True
    else:
        cur = e.get('time')
        assert cur == p.get('old'), f'现状与建议不符(数据已变?): {p} 当前={cur} 建议old={p.get("old")}'
        assert isinstance(p['new'], (int, float)) and p['new'] > 0, f'new 非法: {p}'
        e['time'] = p['new']
    log.append(f'{"新建" if created else ("填占位" if p.get("old") is None else "更新")} {zone}_{tier} {p["track"]} {p["car"]}★{p.get("stars")}: -> {p["new"]}')

# 理论/高手 按 time 升序重排（无 time 置末尾保持相对顺序）
for t in d['tracks']:
    for zone in ('五区', '四区'):
        for tier in ('理论', '高手'):
            entries = t[zone].get(tier, [])
            timed = [(i, e) for i, e in enumerate(entries) if e.get('time') is not None]
            notime = [e for e in entries if e.get('time') is None]
            timed.sort(key=lambda x: x[1]['time'])
            t[zone][tier] = [e for _, e in timed] + notime

json.dump(d, open('gauntlet_data.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
print(f'已应用 {len(log)} 条建议:')
for x in log:
    print('  ' + x)
print('下一步: python _validate_0823.py && python format_json.py')
