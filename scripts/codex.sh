#!/usr/bin/env bash

if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi

.venv/bin/python -m pip install -r requirements.txt

npm i -g @openai/codex@latest

codex "$@"
