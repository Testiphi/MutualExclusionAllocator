"""Lossless compact JSON formatting with atomic replacement and backup."""
import argparse
import json
from pathlib import Path
from data_tools import ROOT, ZONES, atomic_write, configure_stdout, json_text, read_json


def format_data(data):
    def render(value, indent=0, path=()):
        pad = ' ' * indent
        expanded = not path or path == ('tracks', '*') or (len(path) == 3 and path[:2] == ('tracks', '*') and path[2] in ZONES)
        if isinstance(value, dict) and expanded:
            if not value:
                return '{}'
            lines = [f'{pad}  {json_text(key)}: {render(item, indent + 2, path + (key,))}' for key, item in value.items()]
            return '{\n' + ',\n'.join(lines) + '\n' + pad + '}'
        if path == ('tracks',) and isinstance(value, list):
            if not value:
                return '[]'
            return '[\n' + ',\n'.join(' ' * (indent + 2) + render(item, indent + 2, path + ('*',)) for item in value) + '\n' + pad + ']'
        return json_text(value)
    output = render(data) + '\n'
    if json.loads(output) != data:
        raise ValueError('格式化前后数据不一致')
    return output


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, default=ROOT / 'gauntlet_data.json')
    parser.add_argument('--output', type=Path, help='默认原地格式化，替换前自动备份')
    args = parser.parse_args(argv)
    configure_stdout()
    try:
        output = format_data(read_json(args.input))
        atomic_write(args.output or args.input, output)
    except (OSError, ValueError, TypeError) as error:
        parser.exit(1, f'格式化失败: {error}\n')
    print(f'格式化完成: {len(output.splitlines())} 行')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
