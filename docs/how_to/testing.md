# Running Tests

Use the test script to run the project's pytest suite in parallel.
Unit tests live alongside the modules they validate, named
`<file_name>_tests.py` (for example, `financial_planner/tax_calculator_tests.py`).
Pytest is configured in `pytest.ini` to discover `*_tests.py` files.
Experiment scripts also have targeted tests under `financial_planner/experiments/`.

```bash
./scripts/test.sh
```

Run static checks and formatting verification (black, isort, flake8, pylint).
Black and isort use settings in `pyproject.toml`.
Flake8 defaults to single-worker mode; set `FLAKE8_JOBS` to a higher number if
your environment supports multiprocessing semaphores.
Pylint runs with the duplicate-code check disabled via `scripts/static.sh`.

Install the pre-commit hook to run black and isort on staged files:

```bash
pre-commit install
```

Run the commit preparation script to format, test, and lint before commits
(typical runtime: ~1 minute):

```bash
./scripts/commit_prep.sh
```

```bash
./scripts/static.sh
```

Pass extra pytest arguments as needed:

```bash
./scripts/test.sh -q
```
