#!/usr/bin/env bash
# New isolated release directory only. Does not create state, users, services or routes.
set -euo pipefail
umask 022
cd "$(dirname "$0")/../.."
python3 -B -c 'import sys; assert sys.version_info[:2] == (3,12)'
test ! -e .venv || { echo 'STOP: .venv already exists; inspect rather than overwrite'; exit 1; }
python3 -m venv .venv
.venv/bin/python -m pip install --no-index --find-links wheels --require-hashes -r production/mini-guest/requirements.lock
.venv/bin/python -m pip check
.venv/bin/python -B -m backend.mini_guest_service inspect --snapshot-dir snapshot
echo 'Offline runtime installed; no guest state initialized and no service started.'
