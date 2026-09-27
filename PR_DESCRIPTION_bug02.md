# PR: fix(api): guard `update_expense` against missing-ID AttributeError (sample_app bug02)

## What changed

**`sample_app/api.py` — `ExpenseTracker.update_expense`, line 88**

```diff
- if exp.title is None:
+ if exp is None:
```

One token changed. The guard that raises `ValueError("Expense '…' not found.")`
was testing `exp.title` rather than `exp` itself, so it dereferenced a `None`
object before ever reaching the error path.

**`oss_cases/attrs/bug02/upstream/src/attr/_make.py` — `Converter.__init__`**

Added a `__call__` slot assignment at the end of `__init__` so that every
`Converter` instance is directly callable. Four branches cover the four
`takes_self` / `takes_field` combinations, forwarding `(val, self_, field)`
with the correct arity.

**`oss_cases/attrs/bug02/upstream/src/attr/setters.py` — `convert()`**

Added a `hasattr(c, "takes_self")` branch before the bare `c(new_value)` call.
When the converter is a `Converter` object (from `_make.py`), it now receives
`(new_value, instance, attrib)` so that `takes_self=True` / `takes_field=True`
converters get the extra arguments they require on reassignment.

---

## Why

**sample_app bug02** — Ticket: *"update_expense crashes with AttributeError for
missing ID"*

`get_expense()` legitimately returns `None` when an ID is not found. The guard
two lines later did `if exp.title is None:` which caused:

```
AttributeError: 'NoneType' object has no attribute 'title'
```

instead of the intended clean `ValueError`. Every caller — the CLI's `cmd_update`,
integration tests, and any third-party consumer — received a raw traceback with
no actionable message.

**attrs bug02** — Issue #1327: *"Reassigning a field with chained converters
raises `AttributeError: __call__`"*

`Converter.__init__` allocated a `__call__` slot but never assigned it. The
generated `__init__` bypassed the slot entirely (calling the converter by name
through a local dict), so the omission was invisible at construction time. On
field **reassignment** the `on_setattr` hook called `setters.convert()` which
invoked `c(new_value)` — hitting the empty slot and raising `AttributeError`.

---

## Blast Radius: before vs after

### Before fix (`blast_radius/graph.json`)

| File | Symbol | Relation | Risk | Reason |
|------|--------|----------|------|--------|
| `sample_app/api.py` | `ExpenseTracker.update_expense` | bug site | **High** | Missing None-guard; AttributeError propagates to all callers |
| `sample_app/main.py` | `cmd_list` | imports + calls `month_date_range` | **High** | CLI entry point; unguarded AttributeError surfaces as raw traceback |
| `sample_app/main.py` | `cmd_update` | calls `update_expense` | **High** | Direct caller; no try/except around AttributeError |
| `sample_app/utils.py` | `filter_by_month` | calls `month_date_range` | **Medium** | Indirect dependent; unaffected by this bug but flagged by static scan |
| `sample_app/api.py` | `ExpenseTracker.get_expense` | called by bug site | **Medium** | Correctly returns None; caller failed to handle it |
| `sample_app/tests/test_api.py` | `TestGetUpdateDelete.test_update_missing_raises` | weak coverage | **Low** | Accepted `(ValueError, AttributeError)` — masked the bug |

### After fix (`blast_radius/graph_after.json`)

The static call/import graph is **identical** to before — 3 entries:

| File | Symbol | Relation |
|------|--------|----------|
| `main.py` | `cmd_list` | imports `month_date_range` (line 72) |
| `main.py` | `cmd_list` | calls `month_date_range` (line 73) |
| `utils.py` | `filter_by_month` | calls `month_date_range` (line 75) |

**No new impacted files or functions introduced by the fix.** The one-line
change in `api.py` did not alter any import, add any new dependency, or shift
any call boundary. The graph footprint is unchanged.

---

## High-risk item coverage check

| High-risk item | Test coverage after fix | Status |
|----------------|------------------------|--------|
| `api.py::ExpenseTracker.update_expense` | `test_bugs.py::TestBug02UpdateMissingExpense::test_update_missing_raises_value_error` ✅ PASS | **Covered** |
| `api.py::ExpenseTracker.update_expense` | `test_bugs.py::TestBug02UpdateMissingExpense::test_update_missing_does_not_raise_attribute_error` ✅ PASS | **Covered** |
| `api.py::ExpenseTracker.update_expense` | `test_api.py::TestGetUpdateDelete::test_update_title` ✅ PASS | **Covered** |
| `api.py::ExpenseTracker.update_expense` | `test_api.py::TestGetUpdateDelete::test_update_amount` ✅ PASS | **Covered** |
| `api.py::ExpenseTracker.update_expense` | `test_api.py::TestGetUpdateDelete::test_update_missing_raises` ✅ PASS | **Covered** (now raises only `ValueError`) |
| `main.py::cmd_update` | *no dedicated test* | ⚠️ **Untested risk** — see below |

**`cmd_update` is untested.** The CLI integration layer has no test that
exercises `main.py list --month` or `main.py update --id <missing>` end-to-end.
This was flagged High-risk before the fix (AttributeError would surface as a raw
traceback to the user). After the fix, `main()`'s top-level
`except ValueError` handler catches the new `ValueError` cleanly and prints
`Error: Expense '…' not found.` — so the behaviour is now safe, but there is
**no automated test confirming that the CLI error path works**. This is
pre-existing untested risk inherited from the original test suite.

---

## Test suite results (post-fix)

```
38 passed, 3 failed
```

All 3 failures are **pre-existing seeded bugs, out of scope for this PR**:

| Test | Bug | Notes |
|------|-----|-------|
| `TestBug03OverBudgetBoundary::test_one_cent_over_limit_is_over_budget` | Bug 03 | `over_budget_categories` uses `> 100` instead of `>= 100` |
| `TestBug04MutableDefaultHeaders::test_mutable_default_can_be_corrupted_externally` | Bug 04 | `to_csv_rows` mutable default argument |
| `TestBug05UtcDateDefault::test_today_utc_uses_utc_not_local_clock` | Bug 05 | `_today_utc()` returns UTC date not local date |

No new failures introduced. The two Bug02 reproducer tests that were failing
before this fix now both pass.

---

## Remaining risk

1. **`main.py::cmd_update` — no CLI-level test** (inherited; rated High before
   fix, now medium-low because `ValueError` is caught by `main()`'s handler).
2. **Bugs 03, 04, 05 remain open** — `over_budget_categories` boundary,
   `to_csv_rows` mutable default, `_today_utc` UTC skew. None are touched by
   this PR.
3. **attrs bug02 fix is snapshot-only** — the patched files live under
   `oss_cases/attrs/bug02/upstream/` and are not wired into a package install.
   The OSS reproducer test passes against this snapshot but the fix is not
   deployed to any production attrs release.
