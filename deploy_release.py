"""服务器校验并暂存发布包；仅 --activate 或 --rollback 才切换 current。"""
import argparse
from pathlib import Path
import zipfile
from release_tools import stage, activate


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', type=Path, default=Path('/var/www/racepick-releases'))
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--bundle', type=Path)
    group.add_argument('--rollback', help='切回已有版本ID，同样先验证内容')
    parser.add_argument('--activate', action='store_true')
    args = parser.parse_args(argv)
    try:
        if args.rollback and args.activate:
            raise ValueError('--rollback不能与--activate同时使用')
        if args.bundle:
            target = stage(args.bundle, args.base)
            print(f'已校验并暂存版本: {target.name}')
            identity = target.name
        else:
            identity = args.rollback
        if args.activate or args.rollback:
            previous = activate(args.base, identity)
            print(f'已切换current到{identity}; 上一版本: {previous or "无"}')
        else:
            print('尚未切换current；确认后用同一发布包加--activate')
    except (OSError, ValueError, KeyError, TypeError, zipfile.BadZipFile) as error:
        parser.exit(1, f'部署失败: {error}\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
