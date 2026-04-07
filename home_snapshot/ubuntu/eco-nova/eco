#!/bin/bash
set -euo pipefail

SOURCE_PATH="${BASH_SOURCE[0]}"
if command -v readlink >/dev/null 2>&1; then
  RESOLVED="$(readlink -f "$SOURCE_PATH" 2>/dev/null || true)"
  if [ -n "${RESOLVED:-}" ]; then
    SOURCE_PATH="$RESOLVED"
  fi
fi

SCRIPT_DIR="$(cd "$(dirname "$SOURCE_PATH")" && pwd)"
python3 "$SCRIPT_DIR/eco-nova-cli.py" "$@"
