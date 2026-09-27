# PR: fix(utils): replace mutable default `headers=[]` with `None` sentinel in `to_csv_rows` (sample_app bug04)

## What changed

**`sample_app/utils.py` — `to_csv_rows`, line 172**

```diff
-def to_csv_rows(expenses: List[Expense], headers: List[str] = []) -> List[str]:
+def to_csv_rows(expenses: List[Expense], headers: Optional[List[str]] = None) -> List[str]:
     """
     Convert a list of expenses to CSV-formatted strings.
     Optionally prepend a header row.
     """
     default_headers = ["id", "title", "amount", "category", "date", "notes"]
-    row_headers = headers if headers else default_headers
+    row_headers = headers if headers is not None else default_headers
```

One file changed, two lines changed, no other files touched.

---

## Why

Python evaluates default argument expressions **exactly once**, at function-definition
time. The `[]` literal in `headers: List[str] = []` is therefore a single shared list
object across every call that omits `headers`. Any code that obtained a reference to
that object and mutated it (`.append()`, `.extend()`, `+=`) would silently corrupt the
headers seen by all subsequent headerless calls for the lifetime of the process.

A secondary bug was fixed in the same line: the truthiness guard `headers if headers`
would fall through to `default_headers` when `headers=[]` (an explicitly supplied empty
list), because `bool([])` is `False`. The `is not None` identity check distinguishes
"no argument supplied" (`None`) from "an explicitly supplied empty list" (`[]`).

Both defects are resolved by:
1. Using `None` (an immutable singleton) as the sentinel — it cannot be mutated and is
   never shared in a cross-call-polluting way.
2. Guarding with `headers is not None` instead of truthiness.

---

## Blast Radius impact — before vs after

The Blast Radius scan target is `utils.month_date_range` (the original Bug01 target
that seeds the call graph). `to_csv_rows` does not appear in either graph because it is
not reachable from `month_date_range`; Blast Radius scope for this bug was determined
by manual static analysis rather than the automated graph.

### Before (`blast_radius/graph.json`)

| File | Symbol | Relation | Line |
|------|--------|----------|------|
| `main.py` | `cmd_list` | imports | 72 |
| `main.py` | `cmd_list` | calls | 73 |
| `utils.py` | `filter_by_month` | calls | 75 |

**3 impacted entries.**

### After (`blast_radius/graph_after.json`)

| File | Symbol | Relation | Line | New? |
|------|--------|----------|------|------|
| `main.py` | `cmd_list` | imports | 72 | — |
| `tests/test_bugs.py` | `<module>` | imports | 24 | ⚠️ NEW |
| `main.py` | `cmd_list` | calls | 73 | — |
| `utils.py` | `filter_by_month` | calls | 75 | — |

**4 impacted entries (+1 new).**

### New entry analysis

The one new entry — `tests/test_bugs.py / <module> / imports / line 24` — is a
**module-level import** of `month_date_range` added by the Reproducer agent's test
file. This is a test-harness artefact, not a production call site. The import was
added to enable the Bug01 regression tests; it carries no risk to production
behaviour and requires no follow-up action.

**Conclusion:** the fix introduced **zero new production-code impact nodes**. The
single new graph entry is benign (test-only import).

---

## High-risk item audit

| Item | Risk (original) | Test coverage | Status |
|------|----------------|---------------|--------|
| `utils.py / to_csv_rows` | **High** — bug site; shared mutable default corrupts all callers | `test_bugs.py::TestBug04MutableDefaultHeaders::test_default_is_not_mutable_list` ✅ | Patched + passing |
| | | `test_bugs.py::TestBug04MutableDefaultHeaders::test_two_calls_with_same_headers_produce_identical_output` ✅ | |
| | | `test_bugs.py::TestBug04MutableDefaultHeaders::test_no_headers_uses_default_six_columns` ✅ | |
| `utils.py / export_csv` | Medium — caller of `to_csv_rows`; inherits corruption risk | `test_api.py::TestExport::test_export_csv` ✅ | Made safe by callee fix; no change required |
| | | `test_api.py::TestExport::test_export_empty` ✅ | |
| `api.py / ExpenseTracker.export_to_csv` | Medium — transitive caller via `export_csv` | `test_api.py::TestExport::test_export_csv` ✅ | Made safe by callee fix; no change required |
| | | `test_api.py::TestExport::test_export_empty` ✅ | |
| `main.py / cmd_export` | Low — CLI entry point; corrupted header would silently appear in output file | *(no dedicated test)* | ⚠️ **Untested risk** — see note below |

All **High** and **Medium** items are covered by passing tests.

> **Untested risk note — `main.py / cmd_export`:** The CLI `cmd_export` function has no
> dedicated unit or integration test. A corrupted header row would appear silently in
> the output CSV file with no exception raised. The risk is now **eliminated** by the
> fix (there is nothing left to corrupt), but the absence of a CLI-level export test
> remains a gap. Recommend adding a `test_cmd_export` integration test in a follow-up.

---

## Full test suite

```
48 passed, 0 failed  (pytest sample_app/tests/ -v)
```

Three previously failing tests now pass:

- `TestBug04MutableDefaultHeaders::test_default_is_not_mutable_list`
- `TestBug04MutableDefaultHeaders::test_two_calls_with_same_headers_produce_identical_output`
- `TestBug04MutableDefaultHeaders::test_no_headers_uses_default_six_columns`

No regressions introduced.

---

## Remaining risk

| Area | Severity | Notes |
|------|----------|-------|
| `main.py / cmd_export` — no integration test | Low | The bug is fixed; the gap is coverage only. No untested code path that could trigger the old defect still exists. Follow-up ticket recommended. |
| Blast Radius scan target mismatch | Informational | The automated graph is rooted at `utils.month_date_range` (Bug01's target). `to_csv_rows` is unreachable from that root, so the graph does not model this export call chain. A dedicated scan rooted at `utils.to_csv_rows` would give a more precise impact map for future export-path changes. |
