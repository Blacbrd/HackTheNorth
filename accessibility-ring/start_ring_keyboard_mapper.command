#!/bin/bash

set -u

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
AQUAL_PYTHON="$SCRIPT_DIR/../AQual/.venv/bin/python"

if [ -x "$AQUAL_PYTHON" ]; then
  PYTHON_BIN="$AQUAL_PYTHON"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN="$(command -v python3)"
else
  echo "python3 was not found."
  read -r -p "Press Enter to close..."
  exit 1
fi

echo "Using Python: $PYTHON_BIN"
echo "Starting ring keyboard mapper..."
echo

"$PYTHON_BIN" "$SCRIPT_DIR/ring_keyboard_mapper.py" --mapping-file "$SCRIPT_DIR/ring_keymap.json"
STATUS=$?

echo
if [ "$STATUS" -ne 0 ]; then
  echo "Ring keyboard mapper exited with status $STATUS."
  read -r -p "Press Enter to close..."
fi

exit "$STATUS"
