#!/usr/bin/env bash
set -euo pipefail

targets=("$@")
if [ "$#" -eq 0 ]; then
  targets=(financial_planner config manage.py)
fi

fail=0
if [ "${SKIP_FORMAT_CHECKS:-0}" -ne 1 ]; then
  python3 -m black --check "${targets[@]}" || fail=1
  python3 -m isort --check-only "${targets[@]}" || fail=1
fi
python3 -m flake8 "${targets[@]}" || fail=1
python3 -m pylint "${targets[@]}" || fail=1

if [ "$fail" -ne 0 ]; then
  red="$(printf '\033[0;31m')"
  reset="$(printf '\033[0m')"
  printf "%sStatic checks failed.%s\n" "$red" "$reset"
  exit 1
fi

green="$(printf '\033[0;32m')"
reset="$(printf '\033[0m')"
printf "%sStatic checks passed.%s\n" "$green" "$reset"
