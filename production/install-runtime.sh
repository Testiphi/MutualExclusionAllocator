#!/usr/bin/env bash
set -euo pipefail
umask 022
cd "$(dirname "$0")/.."
test "$(uname -m)" = x86_64 || { echo '本包仅适用x86_64'; exit 1; }
python3 -c 'import sys; assert sys.version_info[:2] == (3,12), "需要Python3.12"'
test ! -e .venv || { echo '虚拟环境已存在，先核验状态，不覆盖'; exit 1; }
python3 -m venv .venv
.venv/bin/python -m pip install --no-index --find-links wheels --require-hashes -r production/requirements-linux-py312.lock
.venv/bin/python -m pip check
.venv/bin/python -B production/selfcheck.py
printf '运行环境及临时数据库冒烟通过；尚未初始化正式库或修改Nginx。\n'
