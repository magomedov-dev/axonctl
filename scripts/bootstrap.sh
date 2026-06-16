#!/usr/bin/env bash
# One-shot dev bootstrap: provision everything axonctl needs into .tooling/
# (project-local), so nothing is installed system-wide.
#
#   - .tooling/uv              uv binary
#   - .tooling/python          uv-managed CPython
#   - .tooling/venv            dev virtualenv with axonctl[dev]
#   - .tooling/platform-tools  Android adb
#
# Usage:   scripts/bootstrap.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

bash "$ROOT/scripts/install-uv.sh"
bash "$ROOT/scripts/setup-venv.sh"
bash "$ROOT/scripts/install-adb.sh"

cat <<'EOF'

Bootstrap complete. Next:
  source .tooling/venv/bin/activate
  pytest -q
EOF
