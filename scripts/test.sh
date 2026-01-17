#!/usr/bin/env bash

args=("$@")
if [ "$#" -eq 0 ]; then
  args=(financial_planner/tax_calculator_tests.py)
fi

python3 -m pytest -n auto "${args[@]}"
