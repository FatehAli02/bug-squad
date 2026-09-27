# Fixer Output — sample_app/bug04

**Bug:** Mutable default argument in `to_csv_rows` corrupts headers across calls  
**Ticket:** `bugs/ticket_04.md`  
**Investigator artefact:** `bob_sessions/Investigation bug04.png` + `impact_plan.json` (entry `sample_app_bug04`)  
**Primary affected file:** `sample_app/utils.py`

---

## 1. Inputs Confirmed

| Artefact | Status |
|---|---|
| `bugs/ticket_04.md` | ✅ Read |
| `bob_sessions/Investigation bug04.png` (Investigator session screenshot) | ✅ Read |
| `impact_plan.json` — `sample_app_bug04` entry | ✅ Read |
| `sample_app/tests/test_bugs.py` — `TestBug04MutableDefaultHeaders` (3 tests) | ✅ Read |
| `blast_radius/graph.json` | ✅ Read — target is `utils.month_date_range`; `to_csv_rows` is not in the graph, so no blast-radius-driven secondary changes are required |

---

## 2. Root Cause

`to_csv_rows()` in [`sample_app/utils.py`](sample_app/utils.py) was declared with a
mutable list as its default argument:

```python
# Pre-fix (buggy)
def to_csv_rows(expenses: List[Expense], headers: List[str] = []) -> List[str]:
    ...
    row_headers = headers if headers else default_headers
```

Python evaluates default argument expressions **exactly once**, at
function-definition time. The `[]` object is therefore a single shared instance
across every call that omits `headers`. Any code that obtained a reference to
that shared default and mutated it (via `.extend()`, `.append()`, or `+=`)
would corrupt all subsequent headerless calls — they would receive the
already-mutated list instead of the canonical six-column default.

There is a secondary subtlety: even if no external code mutated the default,
the guard `headers if headers else default_headers` would silently fall through
to `default_headers` whenever `headers` was passed as an empty list `[]`,
because `bool([])` is `False`. Both defects are resolved together.

---

## 3. Diff

**File changed:** `sample_app/utils.py`

```diff
--- a/sample_app/utils.py
+++ b/sample_app/utils.py
@@ -172,9 +172,9 @@ def summary_report(expenses: List[Expense], month_label: str = "") -> str:
 # Export helpers
 # ---------------------------------------------------------------------------
 
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

**Summary of changes:**

1. **Signature:** `headers: List[str] = []` → `headers: Optional[List[str]] = None`  
   `None` is an immutable sentinel; it cannot be mutated and is never shared in
   a way that causes cross-call pollution.

2. **Guard:** `headers if headers else default_headers` → `headers if headers is not None else default_headers`  
   The `is not None` identity check correctly distinguishes "no headers supplied"
   (`None`) from "an explicitly supplied empty list" (`[]`), eliminating the
   secondary false-fallback on empty lists.

No other file was changed for this bug.

---

## 4. Full Test Suite Results

```
platform win32 -- Python 3.13.0, pytest-9.1.1
collected 48 items

sample_app/tests/test_api.py::TestAddExpense::test_add_returns_expense          PASSED
sample_app/tests/test_api.py::TestAddExpense::test_add_persists                 PASSED
sample_app/tests/test_api.py::TestAddExpense::test_add_invalid_category         PASSED
sample_app/tests/test_api.py::TestAddExpense::test_add_with_date                PASSED
sample_app/tests/test_api.py::TestGetUpdateDelete::test_get_existing            PASSED
sample_app/tests/test_api.py::TestGetUpdateDelete::test_get_missing_returns_none PASSED
sample_app/tests/test_api.py::TestGetUpdateDelete::test_update_title            PASSED
sample_app/tests/test_api.py::TestGetUpdateDelete::test_update_amount           PASSED
sample_app/tests/test_api.py::TestGetUpdateDelete::test_update_missing_raises   PASSED
sample_app/tests/test_api.py::TestGetUpdateDelete::test_delete_existing         PASSED
sample_app/tests/test_api.py::TestGetUpdateDelete::test_delete_missing          PASSED
sample_app/tests/test_api.py::TestListFiltering::test_list_all                  PASSED
sample_app/tests/test_api.py::TestListFiltering::test_filter_category           PASSED
sample_app/tests/test_api.py::TestListFiltering::test_filter_date_range         PASSED
sample_app/tests/test_api.py::TestMonthlyExpenses::test_monthly_expenses        PASSED
sample_app/tests/test_api.py::TestMonthlyExpenses::test_monthly_total           PASSED
sample_app/tests/test_api.py::TestBudget::test_set_and_get                      PASSED
sample_app/tests/test_api.py::TestBudget::test_replace_budget                   PASSED
sample_app/tests/test_api.py::TestBudget::test_check_budget_no_budget           PASSED
sample_app/tests/test_api.py::TestBudget::test_check_budget_under               PASSED
sample_app/tests/test_api.py::TestBudget::test_over_budget_categories           PASSED
sample_app/tests/test_api.py::TestExport::test_export_csv                       PASSED
sample_app/tests/test_api.py::TestExport::test_export_empty                     PASSED
sample_app/tests/test_bugs.py::TestBug01LastDayOfMonthExcluded::test_last_day_31_included_in_month   PASSED
sample_app/tests/test_bugs.py::TestBug01LastDayOfMonthExcluded::test_last_day_30_included_in_month   PASSED
sample_app/tests/test_bugs.py::TestBug01LastDayOfMonthExcluded::test_last_day_of_feb_included_in_month PASSED
sample_app/tests/test_bugs.py::TestBug01LastDayOfMonthExcluded::test_last_day_included_in_monthly_total PASSED
sample_app/tests/test_bugs.py::TestBug02UpdateMissingExpense::test_update_missing_raises_value_error  PASSED
sample_app/tests/test_bugs.py::TestBug02UpdateMissingExpense::test_update_missing_does_not_raise_attribute_error PASSED
sample_app/tests/test_bugs.py::TestBug03OverBudgetBoundary::test_exactly_at_limit_is_not_over_budget PASSED
sample_app/tests/test_bugs.py::TestBug03OverBudgetBoundary::test_one_cent_over_limit_is_over_budget  PASSED
sample_app/tests/test_bugs.py::TestBug04MutableDefaultHeaders::test_default_is_not_mutable_list                      PASSED  ← was FAILING
sample_app/tests/test_bugs.py::TestBug04MutableDefaultHeaders::test_two_calls_with_same_headers_produce_identical_output PASSED  ← was FAILING
sample_app/tests/test_bugs.py::TestBug04MutableDefaultHeaders::test_no_headers_uses_default_six_columns              PASSED  ← was FAILING
sample_app/tests/test_bugs.py::TestBug05UtcDateDefault::test_today_utc_does_not_use_timezone_utc     PASSED
sample_app/tests/test_bugs.py::TestBug05UtcDateDefault::test_today_utc_returns_local_date            PASSED
sample_app/tests/test_models.py::TestExpense::test_create_basic                 PASSED
sample_app/tests/test_models.py::TestExpense::test_create_strips_title          PASSED
sample_app/tests/test_models.py::TestExpense::test_create_rounds_amount         PASSED
sample_app/tests/test_models.py::TestExpense::test_create_invalid_category      PASSED
sample_app/tests/test_models.py::TestExpense::test_create_zero_amount           PASSED
sample_app/tests/test_models.py::TestExpense::test_create_negative_amount       PASSED
sample_app/tests/test_models.py::TestExpense::test_round_trip                   PASSED
sample_app/tests/test_models.py::TestExpense::test_all_valid_categories         PASSED
sample_app/tests/test_models.py::TestBudget::test_create_and_round_trip         PASSED
sample_app/tests/test_models.py::TestExpenseStore::test_save_and_load           PASSED
sample_app/tests/test_models.py::TestExpenseStore::test_load_missing_file       PASSED
sample_app/tests/test_models.py::TestExpenseStore::test_save_creates_valid_json PASSED

========================= 48 passed in 0.57s =========================
```

**48 passed, 0 failed.** No regressions introduced.

---

## 5. High-Risk Impacted Items

The Investigator's impact table (from `impact_plan.json`) listed one **High** item and two
**Medium** items for this bug. The **Low** item (`main.py / cmd_export`) required no change.

### High — `sample_app/utils.py` / `to_csv_rows` ✅ Patched

**This is the bug site.** The mutable default `headers: List[str] = []` made the
function's output silently depend on call-site mutation history across the entire
process lifetime. The fix (`headers: Optional[List[str]] = None` + `is not None` guard)
is the canonical Python idiom for this pattern and removes both the shareability
problem (an immutable sentinel cannot be mutated) and the empty-list false-negative
(identity check vs truthiness check).

### Medium — `sample_app/utils.py` / `export_csv`

`export_csv` calls `to_csv_rows(expenses)` with no `headers` argument. On the pre-fix
code, if any earlier caller had mutated the shared default, `export_csv` would silently
write a corrupted header row to the output file. With the fix in place `export_csv`
always receives `None` as the effective default and the internal guard always falls
through to the safe `default_headers` list. **No change to `export_csv` itself was
needed** — it is made safe automatically by fixing the callee.

### Medium — `sample_app/api.py` / `ExpenseTracker.export_to_csv`

`export_to_csv` delegates to `export_csv` which delegates to `to_csv_rows`.
It inherited the corruption risk transitively. For the same reason as `export_csv`,
**no change to `export_to_csv` was needed** — the fix is entirely in `to_csv_rows`.

Both Medium items are covered by the existing export tests
(`test_api.py::TestExport::test_export_csv` and `test_export_empty`), both of which
continue to pass after the fix.

---

## 6. Pipeline Context Note

The diff above was verified against the seeded bug baseline. The pre-fix signature
(`headers: List[str] = []`) was introduced in the initial commit `4c6e19f`. The fix
(`Optional[List[str]] = None`) was applied in commit `a909aff`, which also bundled the
bug03 fix (`over_budget_categories`) and the bug05 fix (`_today_utc`). All three fixes
are confirmed passing in the 48-test run above. No prior `FIXER_OUTPUT_bug04.md`
existed; this is the first and canonical fixer record for this bug.
