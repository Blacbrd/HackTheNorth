#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHON_BIN="$SCRIPT_DIR/../AQual/.venv/bin/python"

if [ ! -x "$PYTHON_BIN" ]; then
  echo "AQual's Python environment is missing: $PYTHON_BIN"
  echo "Set up AQual first, then rerun this file."
  read -r -p "Press Enter to close..."
  exit 1
fi

exec "$PYTHON_BIN" "$SCRIPT_DIR/ring_robot_mapper.py" \
  --mapping-file "$SCRIPT_DIR/ring_keymap.json"
