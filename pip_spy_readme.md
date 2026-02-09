# pip_spy_max.py README

## Overview
`pip_spy_max.py` is an advanced Python dependency analyzer and requirements generator. It scans your project, detects all imports, and generates a clean, annotated `requirements.txt`. It also helps you maintain a healthy codebase by cleaning up `__pycache__` folders and detecting orphan (unused) Python files.

## Default Behavior
By default, running:

    python pip_spy_max.py

will:
- Clean all `__pycache__` folders (`--clean-pycache`)
- Scan all `.py` files in the project
- Generate a `requirements.txt` with short descriptions for each library (`--output requirements.txt`)
- Skip slow live PyPI checks for faster, offline runs (`--no-pypi-check`)
- Show a summary of third-party packages (`--summary`)
- Detect and report orphan (unreachable) `.py` files (`--find-orphans`)

## Key Features
- **Dependency Analysis:** Detects all third-party imports, resolves PyPI names, and annotates each with a short description.
- **Requirements Generation:** Outputs a clean, ready-to-use `requirements.txt` (comments are ignored by pip).
- **PyCache Cleanup:** Recursively deletes all `__pycache__` folders for a clean environment.
- **Orphan File Detection:** Finds `.py` files not reachable from any main entrypoint (e.g., `start_llm.py`, `zena.py`, `main.py`).
- **Fast by Default:** Skips live PyPI checks unless you override with `--no-no-pypi-check`.

## Useful Flags
- `--summary` (default): Show only a summary of third-party packages.
- `--verbose`: Show detailed import locations and frequency.
- `--output <file>`: Set output requirements file name (default: `requirements.txt`).
- `--no-pypi-check`: Skip live PyPI checks (default: enabled for speed).
- `--clean-pycache`: Delete all `__pycache__` folders before scanning (default: enabled).
- `--find-orphans`: Detect and report orphan `.py` files (default: enabled).

## Orphan Files
Orphan files are `.py` files not reachable from any main entrypoint. These may be unused or legacy code. Review and clean them up as needed.

## Example Usage
Just run:

    python pip_spy_max.py

Or, for a full verbose scan with live PyPI checks:

    python pip_spy_max.py --verbose --no-no-pypi-check

## Best Practices
- Run before packaging, deploying, or refactoring your project.
- Review orphan files and requirements for possible cleanup.
- Use with version control to safely review changes.

## Limitations
- Static analysis only: cannot detect dynamic imports or runtime dependencies.
- Orphan detection is heuristic and may not catch all cases in complex projects.

## License
MIT or project license.

---
For questions or improvements, edit this file or the script itself.
