# Financial Planning

Project overview and quick-start information for this repository.

## Setup

Install Python dependencies:

```bash
./scripts/setup.sh
```

Launch Codex with the project virtual environment (updates `codex-cli` via npm):

```bash
./scripts/codex.sh
```

Run database migrations:

```bash
python manage.py migrate
```

Run tests in parallel:

```bash
./scripts/test.sh
```

Tests live alongside their modules in `<file_name>_tests.py` files (for
example, `financial_planner/tax_calculator_tests.py`) and use pytest.
Pytest discovery is configured in `pytest.ini` to pick up `*_tests.py` files.

Run static checks and formatting verification (black, isort, flake8, pylint).
Black and isort use settings in `pyproject.toml`.
Flake8 defaults to single-worker mode; set `FLAKE8_JOBS` higher if your
environment supports multiprocessing semaphores.

Install the pre-commit hook to run black and isort on staged files:

```bash
pre-commit install
```

Run the commit preparation script to format, test, and lint before commits:

```bash
./scripts/commit_prep.sh
```

```bash
./scripts/static.sh
```

Start the development server:

```bash
python manage.py runserver
```

## Apps

- `financial_planner`: Core domain app for financial planning features.
- `financial_planner/investments.py`: Investment account models and portfolio calculations.

## Experiments

Run the investment growth experiment script:

```bash
python -m financial_planner.experiments.investment_growth
```

Edit `financial_planner/experiments/investment_growth_config.py` to adjust the
assumptions. If present, `financial_planner/experiments/investment_growth_config_personal.py`
is used instead for local overrides. The script prints a formatted table of
yearly results.

## Repository Hygiene

- Log files are ignored via `.gitignore`.
