#!/usr/bin/env bash

args=("$@")
if [ "$#" -eq 0 ]; then
  args=(.)
fi

python3 -m pytest -n auto "${args[@]}"
