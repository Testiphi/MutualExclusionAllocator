import json

with open('data.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

entries = data['擂台选车表']
new_entries = []
for e in entries:
    new_e = {
        '大地图': e['大地图'],
        '小地图': e['小地图'],
        '五区': [[c['车']] for c in e['五区']],
        '四区': [[c['车']] for c in e['四区']]
    }
    new_entries.append(new_e)

# Write compact: each entry on its own lines, with proper indentation
lines = ['[']
for i, e in enumerate(new_entries):
    line = json.dumps(e, ensure_ascii=False)
    # add indentation: 2 spaces
    indent = '  '
    # Pretty-print: split by top-level keys
    # Actually, let's just use json.dumps with separators to make it compact but readable
    # We want: same indent=2 but with arrays on single lines
    # The trick: use indent=2 but custom separators for arrays
    pass

# Simpler approach: manually format
lines = []
lines.append('{')
lines.append('  "擂台选车表": [')
for i, e in enumerate(new_entries):
    comma = ',' if i < len(new_entries) - 1 else ''
    z5_str = json.dumps(e['五区'], ensure_ascii=False)
    z4_str = json.dumps(e['四区'], ensure_ascii=False)
    lines.append(f'    {{"大地图": {json.dumps(e["大地图"], ensure_ascii=False)}, "小地图": {json.dumps(e["小地图"], ensure_ascii=False)}, "五区": {z5_str}, "四区": {z4_str}}}{comma}')
lines.append('  ]')
lines.append('}')

output = '\n'.join(lines)
with open('data.json', 'w', encoding='utf-8') as f:
    f.write(output)

# Verify
with open('data.json', 'r', encoding='utf-8') as f:
    verified = json.load(f)

print(f'转换完成！{len(verified["擂台选车表"])} 条')
print()
print('=== 示例 ===')
for v in verified['擂台选车表'][:2]:
    print(json.dumps(v, ensure_ascii=False))
print()
print(f'文件体积: {len(output)} 字节 ({len(output)/1024:.1f} KB)')
