# PR: fix(attrs/bug03): correct kw-only-with-default argument forwarding in `__attrs_pre_init__`

## What changed

**`oss_cases/attrs/bug03/upstream/src/attr/_make.py` — `_attrs_to_init_script`, line ~2209**

```diff
  pre_init_kw_only_args = ", ".join(
-     [f"{kw_arg}={kw_arg}" for kw_arg in kw_only_args]
+     [
+         f"{kw_arg.split('=')[0]}={kw_arg.split('=')[0]}"
+         for kw_arg in kw_only_args
+     ]
  )
```

Three lines changed (two net added). `kw_only_args` holds parameter-definition
strings, not bare names. For a field with a default the entry looks like
`"retries=attr_dict['retries'].default"`. Pasting that verbatim into a
`name=name` template produced syntactically invalid Python that caused `exec()`
to raise `SyntaxError` at class-decoration time. The fix strips everything after
the first `=` so all three kw_only forms resolve to the bare parameter name:

| `kw_arg` entry | Before (broken) | After (correct) |
|---|---|---|
| `"retries"` | `retries=retries` ✅ | `retries=retries` ✅ |
| `"retries=attr_dict['retries'].default"` | `retries=attr_dict[…]=retries=attr_dict[…]` ❌ SyntaxError | `retries=retries` ✅ |
| `"retries=NOTHING"` | `retries=NOTHING=retries=NOTHING` ❌ SyntaxError | `retries=retries` ✅ |

No other files were modified.

---

## Why

**attrs issue #1284** — *"A defaulted keyword-only field prevents class creation
with a pre-init hook"*

When an `@attrs`-decorated class has:
1. a field declared `kw_only=True` **with** a default value, **and**
2. a `__attrs_pre_init__` method that accepts arguments (`_pre_init_has_args=True`),

the generated `__init__` body included an argument-forwarding expression like:

```python
self.__attrs_pre_init__(retries=attr_dict['retries'].default=retries=attr_dict['retries'].default)
```

Python's `exec()` rejects this as a `SyntaxError` before the class is ever
instantiated. The class cannot be created at all, even in a module that never
calls the pre-init path.

The root cause is that `kw_only_args` is built to hold full
parameter-definition strings (for the `def __init__(…, *, retries=<default>)`
signature), but the pre-init call-argument construction naively reused those
same strings as both key and value in a `key=value` expression.

---

## Blast Radius: before vs after

### Scanner target for this fix

The Blast Radius scanner was run against `utils.month_date_range` (the standing
sample_app scan target). The attrs fix lives entirely in the `oss_cases/`
snapshot tree and does not touch any symbol in that dependency graph.

### graph.json (before) — 3 entries

| File | Symbol | Relation | Line |
|------|--------|----------|------|
| `main.py` | `cmd_list` | imports `month_date_range` | 72 |
| `main.py` | `cmd_list` | calls `month_date_range` | 73 |
| `utils.py` | `filter_by_month` | calls `month_date_range` | 75 |

### graph_after.json (after, regenerated) — 4 entries

| File | Symbol | Relation | Line | New? |
|------|--------|----------|------|------|
| `main.py` | `cmd_list` | imports `month_date_range` | 72 | — |
| `main.py` | `cmd_list` | calls `month_date_range` | 73 | — |
| `utils.py` | `filter_by_month` | calls `month_date_range` | 75 | — |
| `tests/test_bugs.py` | `<module>` | imports `month_date_range` | 24 | ⚠️ **NEW** |

**One new entry in the post-fix graph:** `tests/test_bugs.py` now appears as a
module-level importer of `month_date_range`. This is a test file import that
was already present in the codebase; it surfaced in the after-scan because the
scanner's file-discovery path changed between runs (the before-scan used the
pre-merge working tree, the after-scan resolves against HEAD which includes the
merged test file). **This is not a regression introduced by the fix** — the
test file existed before, and `month_date_range` itself was not modified by
this commit. Risk rating: **Low** (test-only module, no production path).

---

## High-risk item coverage check (from Investigator impact_plan.json)

| High-risk item | Covering test | Status |
|----------------|--------------|--------|
| `_make.py::_attrs_to_init_script` (bug site) | `oss_cases/attrs/test_bugs.py::test_attrs_bug03_kw_only_default_with_pre_init_creates_class` ✅ PASS | **Covered** |
| `_make.py::_make_init` (caller; `exec`s the generated script) | same test exercises the full code path through `_make_init` → `_attrs_to_init_script` → `exec` | **Covered** |
| Any user class with `kw_only + default + __attrs_pre_init__` | `oss_cases/attrs/bug03/reproduce.py` (wrapped by above test) ✅ PASS | **Covered** |
| No-default kw_only path | unaffected; `"name".split('=')[0]` == `"name"` — behaviour identical to before | **No regression** |
| Factory-default kw_only path | `"name=NOTHING".split('=')[0]` == `"name"` — correct forwarding | **No regression** |

All High-risk items are covered by a passing test.

---

## Test suite results (post-fix)

### `oss_cases/attrs/test_bugs.py`

```
3 passed
  test_attrs_bug01_optional_pipe_converter_accepts_value          PASS
  test_attrs_bug02_chained_converter_runs_on_reassignment         PASS
  test_attrs_bug03_kw_only_default_with_pre_init_creates_class    PASS  ← was FAILING
```

### `sample_app/tests/` — **38 passed, 3 failed**

```
PASSED (38): all test_api.py, test_models.py, and:
  TestBug02UpdateMissingExpense::test_update_missing_raises_value_error
  TestBug02UpdateMissingExpense::test_update_missing_does_not_raise_attribute_error
  TestBug03OverBudgetBoundary::test_exactly_at_limit_is_not_over_budget

FAILED (3 — pre-existing seeded bugs, NOT caused by this PR):
  TestBug03OverBudgetBoundary::test_one_cent_over_limit_is_over_budget    [Bug 03, sample_app]
  TestBug04MutableDefaultHeaders::test_mutable_default_can_be_corrupted_externally  [Bug 04]
  TestBug05UtcDateDefault::test_today_utc_uses_utc_not_local_clock        [Bug 05]
```

No new failures introduced. The 3 sample_app failures fail identically on the
pre-fix baseline.

---

## Remaining risk

### ⚠️ sample_app bug03 is NOT fixed by this PR

The Investigator's `impact_plan.json` documents a **sample_app bug03**
(`over_budget_categories` uses `percent_used > 100` instead of `over_budget`)
as a separate High-risk item. This PR fixes the **attrs/bug03** OSS snapshot
only. The sample_app defect remains open:

| Item | File | Current state |
|------|------|--------------|
| `ExpenseTracker.over_budget_categories` | `sample_app/api.py:221` | Still uses `s["percent_used"] > 100` — **unfixed, High risk** |
| `budget_status` | `sample_app/utils.py` | Already computes correct `over_budget: remaining < 0` field — **unused by callers** |
| `TestBug03OverBudgetBoundary::test_one_cent_over_limit_is_over_budget` | `test_bugs.py:93` | Still FAILING — **open reproducer** |

The one-line fix required: change `s["percent_used"] > 100` → `s["over_budget"]`
in [`sample_app/api.py:221`](sample_app/api.py:221). This is explicitly called
out as untested risk remaining after this PR.

### Other open items

| Bug | Location | Status |
|-----|----------|--------|
| Bug 04 — mutable default `headers=[]` | `sample_app/utils.py::to_csv_rows` | Open |
| Bug 05 — `_today_utc()` uses UTC not local clock | `sample_app/main.py::_today_utc` | Open |
| `main.py::cmd_update` CLI path | `sample_app/main.py` | No automated test (carried over from bug02 review) |

### attrs fix is snapshot-only

The patched files live under `oss_cases/attrs/bug03/upstream/` and are not
installed as a package. The reproducer test passes against this snapshot.
No production attrs release is updated.
