# AGENTS.md

This file provides guidance to agents when working with code in this repository.

## What this repo is

**Bug Squad** — an IBM Bob pipeline that takes a bug ticket through four subagent roles (Reproducer → Investigator → Fixer → Reviewer) and produces a reviewed PR. It also runs **Blast Radius**, a static dependency-impact analyzer. Read [`CONTEXT.md`](CONTEXT.md) before starting any Bob task.

## Commands

### Sample app tests (pytest, no config file — run from repo root)
```sh
# All sample_app tests
pytest sample_app/tests/ -v

# Single test
pytest sample_app/tests/test_api.py::TestBudget::test_check_budget_under -v
```

### OSS reproducer tests (require deps)
```sh
# Install deps first (no pyproject.toml — manual install required)
python -m pip install pytest -r oss_cases/requirements.txt
npm ci --prefix oss_cases/yup --ignore-scripts --no-audit --no-fund

# All 15 reproducer tests (expected: 15 FAILED — bugs are intentionally present)
python -m pytest oss_cases/attrs/test_bugs.py oss_cases/schedule/test_bugs.py \
  oss_cases/jsonschema/test_bugs.py oss_cases/arrow/test_bugs.py \
  oss_cases/yup/test_bugs.py -v

# Single OSS test
pytest oss_cases/attrs/test_bugs.py::test_attrs_bug01_optional_pipe_converter_accepts_value -v
```

### Blast Radius scan
```sh
python blast_radius/scan.py --repo sample_app --target utils.month_date_range --out blast_radius/graph.json
# After fix: use --out blast_radius/graph_after.json
```

## Critical gotchas

- **OSS tests are expected to FAIL** on pre-fix snapshots — a passing OSS test means the bug is gone (wrong baseline). Only run them to confirm a bug is present, not to validate a fix.
- **`sample_app/` tests use `sys.path.insert`** in each test file to add `..` — no `conftest.py`, no `setup.py`. Tests must be run with `pytest` from the repo root, not from inside `sample_app/`.
- **`oss_cases/yup/` reproduce scripts run via `run.cjs`** (esbuild + node) — not directly with pytest. The pytest wrapper in `test_bugs.py` spawns node. Requires `npm ci` to be run first.
- **No `pyproject.toml`, `setup.cfg`, or `pytest.ini`** — no linter, formatter, or type-checker is configured. Follow the style in existing files.
- **Blast Radius `build_graph()`** is the public API; the CLI is a thin wrapper around it. Before-fix output → `blast_radius/graph.json`; after-fix → `blast_radius/graph_after.json`.
- **Bobcoin discipline:** static scanning, dashboard work, and data curation must be plain code (not Bob tasks). Only the four pipeline roles and Blast Radius reasoning should use Bobcoins.

## Code style (Python)

- `from __future__ import annotations` at the top of every module.
- Type hints everywhere; use `Optional[T]` (not `T | None`) and `List[T]` / `Dict[K,V]` from `typing` (not the built-in generics).
- Section headers with 79-char dashes: `# ---------------------------------------------------------------------------`.
- `dataclass` for models; `__slots__` on small data-only classes (see `blast_radius/scan.py::Impact`).
- Error reporting to `sys.stderr`; structured return codes (`0` / `1`) from `main()`.
- Dates stored as ISO-8601 strings (`"YYYY-MM-DD"`), not `date` objects, in model fields.
