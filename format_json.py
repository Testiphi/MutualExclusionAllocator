"""
gauntlet_data.json 格式化脚本
用法: python format_json.py
每次修改数据后运行，保持格式统一
"""

import sys, json
sys.stdout.reconfigure(encoding='utf-8')

import os
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PATH = os.path.join(SCRIPT_DIR, 'gauntlet_data.json')

def format_entry(e):
    return json.dumps(e, ensure_ascii=False, separators=(',', ':'))

def format_tier(tier):
    if not tier:
        return '[]'
    return '[' + ','.join(format_entry(e) for e in tier) + ']'

with open(PATH, 'r', encoding='utf-8') as f:
    gd = json.load(f)

out = []
out.append('{')
out.append('  "_version": %d,' % gd['_version'])
out.append('  "_comment": "%s",' % gd['_comment'])
out.append('  "tier_info": %s,' % json.dumps(gd['tier_info'], ensure_ascii=False, separators=(',', ':')))
out.append('  "tracks": [')

tracks = gd['tracks']
for idx, t in enumerate(tracks):
    comma = ',' if idx < len(tracks) - 1 else ''
    out.append('    {')
    out.append('      "大地图": "%s",' % t['大地图'])
    out.append('      "小地图": "%s",' % t['小地图'])
    
    for ek in ['has_special_route', 'special_route_note']:
        if ek in t:
            out.append('      "%s": %s,' % (ek, json.dumps(t[ek], ensure_ascii=False)))
    
    for zi, zone in enumerate(['五区', '四区']):
        if zone not in t:
            continue
        out.append('      "%s": {' % zone)
        ztiers = []
        for tn in ['理论', '高手', '普通', '自动']:
            if tn in t[zone]:
                ztiers.append('        "%s": %s' % (tn, format_tier(t[zone][tn])))
        out.append(',\n'.join(ztiers))
        out.append('      }' + (',' if zi == 0 else ''))
    
    out.append('    }' + comma)

out.append('  ]')
out.append('}')

with open(PATH, 'w', encoding='utf-8') as f:
    f.write('\n'.join(out) + '\n')

old_lines = sum(1 for _ in open(PATH, 'r', encoding='utf-8'))
print('格式化完成: %d 行' % old_lines)
