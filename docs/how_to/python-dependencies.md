# Python Dependencies

Use the setup script to install Python dependencies for this project.
It installs the runtime, test (pytest, pytest-xdist), and static analysis
dependencies like black, flake8, isort, pylint, and pre-commit.

```bash
./scripts/setup.sh
```

```bash
pip install -r requirements.txt
```

Use the Codex launcher to ensure the virtual environment is created, Codex is
up to date via npm, and the CLI is launched:

```bash
./scripts/codex.sh
```
