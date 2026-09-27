# Fixer Output — attrs/bug02

**Bug:** Reassigning a field with chained converters raises an internal error  
**Issue:** [python-attrs/attrs #1327](https://github.com/python-attrs/attrs/issues/1327)  
**Pre-fix snapshot:** `53e632c5218b729da6ac37a35b4b68379dc18999`  
**Fix commit (upstream reference):** `6fda0a4e086b56d7058855e4c15112c8f58de74c`

---

## Root Cause

`Converter` in `src/attr/_make.py` declares `"__call__"` in `__slots__` but
**never assigns it** inside `__init__`.  The slot is therefore always unset.

During `__init__` construction this doesn't matter — the generated `__init__`
code calls the converter function by name via a local dict (`__attr_converter_<name>(val)`),
completely bypassing the `__call__` slot.

On **reassignment** (`counter.value = "19"`), the default `on_setattr` hook fires
`setters.convert(instance, attrib, new_value)`, which does:

```python
c = attrib.converter   # a Converter object
if c:
    return c(new_value)   # calls Converter.__call__ — the unset slot
```

Because the slot was never set, Python raises:

```
AttributeError: __call__
```

instead of applying the `[str, int]` converter pipeline.

**Two-file fix required:**

1. **`_make.py` — `Converter.__init__`:** assign `self.__call__` to a closure
   that delegates to `self.converter` with the correct positional arguments
   based on `takes_self` / `takes_field`.

2. **`setters.py` — `convert()`:** when the converter is a `Converter` object
   (detected via `hasattr(c, "takes_self")` to avoid a circular import), pass
   `instance` and `attrib` in addition to `new_value` so that converters with
   `takes_self=True` or `takes_field=True` receive all required arguments.

---

## Diff

```diff
diff --git a/oss_cases/attrs/bug02/upstream/src/attr/_make.py b/oss_cases/attrs/bug02/upstream/src/attr/_make.py
index e251e0c..90be305 100644
--- a/oss_cases/attrs/bug02/upstream/src/attr/_make.py
+++ b/oss_cases/attrs/bug02/upstream/src/attr/_make.py
@@ -2709,6 +2709,28 @@ class Converter:
             converter
         ).get_first_param_type()
 
+        # Build a __call__ that invokes self.converter with the correct
+        # signature depending on takes_self / takes_field.  This slot must
+        # be set here so that Converter instances are directly callable
+        # (e.g. from setters.convert which does ``c(new_value)``).
+        if not (takes_self or takes_field):
+            self.__call__ = converter
+        elif takes_self and takes_field:
+            def __call__(val, self_=None, field=None):
+                return converter(val, self_, field)
+
+            self.__call__ = __call__
+        elif takes_self:
+            def __call__(val, self_=None, field=None):
+                return converter(val, self_)
+
+            self.__call__ = __call__
+        else:
+            def __call__(val, self_=None, field=None):
+                return converter(val, field)
+
+            self.__call__ = __call__
+
     @staticmethod
     def _get_global_name(attr_name: str) -> str:

diff --git a/oss_cases/attrs/bug02/upstream/src/attr/setters.py b/oss_cases/attrs/bug02/upstream/src/attr/setters.py
index 3922adb..5f32f75 100644
--- a/oss_cases/attrs/bug02/upstream/src/attr/setters.py
+++ b/oss_cases/attrs/bug02/upstream/src/attr/setters.py
@@ -63,6 +63,12 @@ def convert(instance, attrib, new_value):
     """
     c = attrib.converter
     if c:
+        # A Converter object (from _make.py) carries takes_self / takes_field
+        # metadata. Its __call__ slot accepts (val, self_, field) so we must
+        # pass instance and attrib when calling it from a setattr hook.
+        # We use hasattr rather than isinstance to avoid a circular import.
+        if hasattr(c, "takes_self"):
+            return c(new_value, instance, attrib)
         return c(new_value)
 
     return new_value

diff --git a/sample_app/api.py b/sample_app/api.py
index b44aec2..29d19e4 100644
--- a/sample_app/api.py
+++ b/sample_app/api.py
@@ -85,7 +85,7 @@ class ExpenseTracker:
         the expense does not exist.
         """
         exp = self.get_expense(expense_id)
-        if exp.title is None:
+        if exp is None:
             raise ValueError(f"Expense '{expense_id}' not found.")
         if title is not None:
             exp.title = title.strip()
```

---

## Full Test Suite Results

### `sample_app/tests/` — 38 passed, 3 failed (pre-existing)

```
PASSED  sample_app/tests/test_api.py::TestAddExpense::test_add_returns_expense
PASSED  sample_app/tests/test_api.py::TestAddExpense::test_add_persists
PASSED  sample_app/tests/test_api.py::TestAddExpense::test_add_invalid_category
PASSED  sample_app/tests/test_api.py::TestAddExpense::test_add_with_date
PASSED  sample_app/tests/test_api.py::TestGetUpdateDelete::test_get_existing
PASSED  sample_app/tests/test_api.py::TestGetUpdateDelete::test_get_missing_returns_none
PASSED  sample_app/tests/test_api.py::TestGetUpdateDelete::test_update_title
PASSED  sample_app/tests/test_api.py::TestGetUpdateDelete::test_update_amount
PASSED  sample_app/tests/test_api.py::TestGetUpdateDelete::test_update_missing_raises
PASSED  sample_app/tests/test_api.py::TestGetUpdateDelete::test_delete_existing
PASSED  sample_app/tests/test_api.py::TestGetUpdateDelete::test_delete_missing
PASSED  sample_app/tests/test_api.py::TestListFiltering::test_list_all
PASSED  sample_app/tests/test_api.py::TestListFiltering::test_filter_category
PASSED  sample_app/tests/test_api.py::TestListFiltering::test_filter_date_range
PASSED  sample_app/tests/test_api.py::TestMonthlyExpenses::test_monthly_expenses
PASSED  sample_app/tests/test_api.py::TestMonthlyExpenses::test_monthly_total
PASSED  sample_app/tests/test_api.py::TestBudget::test_set_and_get
PASSED  sample_app/tests/test_api.py::TestBudget::test_replace_budget
PASSED  sample_app/tests/test_api.py::TestBudget::test_check_budget_no_budget
PASSED  sample_app/tests/test_api.py::TestBudget::test_check_budget_under
PASSED  sample_app/tests/test_api.py::TestBudget::test_over_budget_categories
PASSED  sample_app/tests/test_api.py::TestExport::test_export_csv
PASSED  sample_app/tests/test_api.py::TestExport::test_export_empty
PASSED  sample_app/tests/test_bugs.py::TestBug02UpdateMissingExpense::test_update_missing_raises_value_error   ← WAS FAILING
PASSED  sample_app/tests/test_bugs.py::TestBug02UpdateMissingExpense::test_update_missing_does_not_raise_attribute_error  ← WAS FAILING
PASSED  sample_app/tests/test_bugs.py::TestBug03OverBudgetBoundary::test_exactly_at_limit_is_not_over_budget
FAILED  sample_app/tests/test_bugs.py::TestBug03OverBudgetBoundary::test_one_cent_over_limit_is_over_budget   (pre-existing, out of scope)
FAILED  sample_app/tests/test_bugs.py::TestBug04MutableDefaultHeaders::test_mutable_default_can_be_corrupted_externally  (pre-existing, out of scope)
FAILED  sample_app/tests/test_bugs.py::TestBug05UtcDateDefault::test_today_utc_uses_utc_not_local_clock       (pre-existing, out of scope)
PASSED  sample_app/tests/test_models.py::TestExpense::test_create_basic
PASSED  sample_app/tests/test_models.py::TestExpense::test_create_strips_title
PASSED  sample_app/tests/test_models.py::TestExpense::test_create_rounds_amount
PASSED  sample_app/tests/test_models.py::TestExpense::test_create_invalid_category
PASSED  sample_app/tests/test_models.py::TestExpense::test_create_zero_amount
PASSED  sample_app/tests/test_models.py::TestExpense::test_create_negative_amount
PASSED  sample_app/tests/test_models.py::TestExpense::test_round_trip
PASSED  sample_app/tests/test_models.py::TestExpense::test_all_valid_categories
PASSED  sample_app/tests/test_models.py::TestBudget::test_create_and_round_trip
PASSED  sample_app/tests/test_models.py::TestExpenseStore::test_save_and_load
PASSED  sample_app/tests/test_models.py::TestExpenseStore::test_load_missing_file
PASSED  sample_app/tests/test_models.py::TestExpenseStore::test_save_creates_valid_json
```

The 3 failing tests (`bug03`, `bug04`, `bug05`) were already failing before this
fix — verified by the pre-existing seeded bug list.  No new failures introduced.

### `oss_cases/attrs/test_bugs.py::test_attrs_bug02_chained_converter_runs_on_reassignment`

```
PASSED  oss_cases/attrs/test_bugs.py::test_attrs_bug02_chained_converter_runs_on_reassignment
```

---

## High-Risk Item Touched

### `sample_app/api.py` — `ExpenseTracker.update_expense` (Risk: **High**)

**Investigator finding:** The method called `self.get_expense(expense_id)` which
returns `None` for unknown IDs.  The very next line dereferenced `exp.title`
before checking whether `exp` was `None`, producing `AttributeError: 'NoneType'
object has no attribute 'title'` instead of the intended `ValueError`.

**Change made:** replaced `if exp.title is None:` with `if exp is None:` on
`sample_app/api.py` line 88.

**Why:** The Investigator rated this **High** risk because every caller of
`update_expense` (including `cmd_update` in `main.py` and both `TestBug02`
reproducer tests) would receive a raw `AttributeError` traceback rather than
a clean `ValueError`.  The fix is a one-character-class change that makes the
guard check the object itself instead of one of its attributes.

**Secondary impacted item confirmed safe:**
`TestGetUpdateDelete.test_update_missing_raises` (previously rated Low/weak
coverage because it accepted both `ValueError` and `AttributeError`) now only
ever sees a `ValueError` — it still passes, and the weak dual-exception
acceptance is no longer masking the bug.
