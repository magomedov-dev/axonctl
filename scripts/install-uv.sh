#!/usr/bin/env bash
# Download the uv standalone binary into .tooling/ (project-local, never
# system-wide). uv then manages the Python toolchain and the dev venv.
#
# Usage:   scripts/install-uv.sh
# Env:     UV_VERSION  release tag to pin (default: latest)
# Result:  .tooling/uv/uv  and  .tooling/uv/uvx
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
UV_DIR="$ROOT/.tooling/uv"
UV_VERSION="${UV_VERSION:-latest}"

os="$(uname -s)"
arch="$(uname -m)"
case "$os" in
    Linux)
        case "$arch" in
            x86_64)        TRIPLE="x86_64-unknown-linux-gnu" ;;
            aarch64|arm64) TRIPLE="aarch64-unknown-linux-gnu" ;;
            *) echo "error: unsupported arch '$arch'" >&2; exit 1 ;;
        esac ;;
    Darwin)
        case "$arch" in
            arm64)  TRIPLE="aarch64-apple-darwin" ;;
            x86_64) TRIPLE="x86_64-apple-darwin" ;;
            *) echo "error: unsupported arch '$arch'" >&2; exit 1 ;;
        esac ;;
    *) echo "error: unsupported OS '$os'" >&2; exit 1 ;;
esac

if [ "$UV_VERSION" = "latest" ]; then
    URL="https://github.com/astral-sh/uv/releases/latest/download/uv-$TRIPLE.tar.gz"
else
    URL="https://github.com/astral-sh/uv/releases/download/$UV_VERSION/uv-$TRIPLE.tar.gz"
fi

for tool in curl tar; do
    command -v "$tool" >/dev/null 2>&1 || { echo "error: '$tool' is required" >&2; exit 1; }
done

mkdir -p "$UV_DIR"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

echo ">> downloading $URL"
curl -fsSL "$URL" -o "$TMP/uv.tar.gz"
tar -xzf "$TMP/uv.tar.gz" -C "$TMP"
cp "$TMP/uv-$TRIPLE/uv" "$TMP/uv-$TRIPLE/uvx" "$UV_DIR/"

echo ">> installed: $UV_DIR/uv"
"$UV_DIR/uv" --version
