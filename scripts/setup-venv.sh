#!/usr/bin/env bash
# Provision the development environment entirely inside .tooling/ using uv:
#   - a uv-managed CPython downloaded into .tooling/python
#   - a virtualenv at .tooling/venv
#   - axonctl[dev] installed editable into that venv
# Nothing is installed system-wide and uv's cache is kept project-local.
#
# Usage:   scripts/setup-venv.sh
# Env:     PYVER  Python version for the venv (default: 3.12)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TOOLING="$ROOT/.tooling"
UV="$TOOLING/uv/uv"
VENV="$TOOLING/venv"
PYVER="${PYVER:-3.12}"

# Keep every uv-managed artifact under .tooling so the host stays clean.
export UV_PYTHON_INSTALL_DIR="$TOOLING/python"
export UV_CACHE_DIR="$TOOLING/uv-cache"
# Do NOT create python shims in ~/.local/bin — that would pollute the host.
export UV_PYTHON_INSTALL_BIN=0

if [ ! -x "$UV" ]; then
    echo "error: uv not found at $UV — run scripts/install-uv.sh first" >&2
    exit 1
fi

echo ">> installing uv-managed CPython $PYVER into $UV_PYTHON_INSTALL_DIR"
"$UV" python install "$PYVER"

echo ">> creating venv at $VENV"
"$UV" venv --clear --python "$PYVER" "$VENV"

echo ">> installing axonctl[dev] (editable)"
"$UV" pip install --python "$VENV/bin/python" -e "$ROOT[dev]"

echo ">> done. Activate with:  source .tooling/venv/bin/activate"
