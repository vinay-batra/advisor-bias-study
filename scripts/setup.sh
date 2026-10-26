#!/usr/bin/env bash
# One-time setup. Run from the repo root.
set -e
PY=/opt/homebrew/bin/python3.11
[ -x "$PY" ] || PY=$(command -v python3.11 || command -v python3)
"$PY" -m venv .venv
.venv/bin/pip install --upgrade pip -q
.venv/bin/pip install -r requirements.txt -q
echo "done. activate with: source .venv/bin/activate"
