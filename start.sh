#!/usr/bin/env bash
# One-shot launcher for panels/VPS that give you a shell.
set -e
python3 -m pip install --no-cache-dir -r requirements.txt
exec python3 main.py
