#!/usr/bin/env bash
# Only installs into a NEW isolated staged component; never starts or migrates anything.
set -euo pipefail
component="${1:?guest or bridge}"
case "$component" in guest|bridge) ;; *) exit 2 ;; esac
delivery_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
target="$delivery_root/$component"
test -d "$target/backend"
test ! -e "$target/.venv"
python3 -m venv "$target/.venv"
"$target/.venv/bin/python" -m pip install --no-index --require-hashes --find-links "$delivery_root/wheels" -r "$delivery_root/locks/$component.lock"
"$target/.venv/bin/python" -m pip check
