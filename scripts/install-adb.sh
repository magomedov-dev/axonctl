#!/usr/bin/env bash
# Download Android platform-tools (adb) into .tooling/ so the host machine is
# never touched. Idempotent: re-running replaces the existing copy.
#
# Usage:   scripts/install-adb.sh
# Result:  .tooling/platform-tools/adb
#
# axonctl resolves adb in this order (see fleet/adb.py, Stage 5):
#   1. $AXONCTL_ADB                  explicit override
#   2. .tooling/platform-tools/adb   this script's output
#   3. adb on $PATH                  system fallback
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TOOLING="$ROOT/.tooling"

case "$(uname -s)" in
    Linux*)  PKG="platform-tools-latest-linux.zip" ;;
    Darwin*) PKG="platform-tools-latest-darwin.zip" ;;
    *)       echo "error: unsupported OS '$(uname -s)'" >&2; exit 1 ;;
esac
URL="https://dl.google.com/android/repository/$PKG"

for tool in curl unzip; do
    command -v "$tool" >/dev/null 2>&1 || { echo "error: '$tool' is required" >&2; exit 1; }
done

mkdir -p "$TOOLING"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

echo ">> downloading $URL"
curl -fsSL "$URL" -o "$TMP/platform-tools.zip"

echo ">> extracting into $TOOLING"
rm -rf "$TOOLING/platform-tools"
unzip -q "$TMP/platform-tools.zip" -d "$TOOLING"

ADB="$TOOLING/platform-tools/adb"
echo ">> installed: $ADB"
"$ADB" version
