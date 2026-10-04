"""本地生成完整静态发布包，默认不覆盖已有包。"""
import argparse
from pathlib import Path
from data_tools import ROOT, read_json
from validate_data import validate_data
from release_tools import pack


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=ROOT)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        errors, _ = validate_data(read_json(args.source / 'gauntlet_data.json'), read_json(args.source / 'cars.json'))
        if errors:
            raise ValueError('\n'.join(errors))
        info = pack(args.source, args.output)
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.exit(1, f'打包失败: {error}\n')
    print(f'发布包: {args.output}; 版本: {info["id"]}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
