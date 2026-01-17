# Financial Planning

Project overview and quick-start information for this repository.

## Setup

Install Python dependencies:

```bash
./scripts/setup.sh
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

## Repository Hygiene

- Log files are ignored via `.gitignore`.
