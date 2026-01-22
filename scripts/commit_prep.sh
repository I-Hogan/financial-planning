#!/usr/bin/env bash

# Typical runtime: ~1 minute.
python3 -m isort .
python3 -m black .
./scripts/test.sh
SKIP_FORMAT_CHECKS=1 ./scripts/static.sh
