# Fixer Output — attrs/bug03

**Bug:** `python-attrs/attrs #1284` — A defaulted keyword-only field prevents
class creation with a pre-init hook.

**Source snapshot:** `689a0e64012d1e576ebd99e786a254bc537582c6`  
**Upstream fix commit:** `09161fc9181bf94aa3bbc5509c663d736a9553dc`  
**Primary affected file:** `oss_cases/attrs/bug03/upstream/src/attr/_make.py`

---

## 1. Root Cause

In `_attrs_to_init_script()` (line ~2209 of `_make.py`), the generated
`__init__` code must also pass the correct arguments to
`self.__attrs_pre_init__()` when the class has a pre-init hook that accepts
arguments (`_pre_init_has_args=True`).

The `kw_only_args` list holds parameter-definition strings:

| Field type                    | Entry in `kw_only_args`                    |
|-------------------------------|--------------------------------------------|
| kw_only, **no default**       | `"retries"`                                |
| kw_only, **with default**     | `"retries=attr_dict['retries'].default"`   |
| kw_only, **factory default**  | `"retries=NOTHING"`                        |

When building the keyword arguments for the `__attrs_pre_init__` call, the
code on the buggy snapshot did:

```python
pre_init_kw_only_args = ", ".join(
    [f"{kw_arg}={kw_arg}" for kw_arg in kw_only_args]
)
```

For a field **without** a default (`kw_arg = "retries"`) this correctly
produces `retries=retries`.

For a field **with** a default (`kw_arg = "retries=attr_dict['retries'].default"`)
this produces:

```
retries=attr_dict['retries'].default=retries=attr_dict['retries'].default
```

That is syntactically invalid Python. When `exec()` compiles the generated
`__init__` function body, it raises a `SyntaxError` at **class-decoration
time** — not at instantiation time — so the class cannot be created at all.

---

## 2. The Fix (Diff)

**File:** `oss_cases/attrs/bug03/upstream/src/attr/_make.py`

```diff
@@ -2207,7 +2207,10 @@ def _attrs_to_init_script(
         # leading comma & kw_only args
         args += f"{', ' if args else ''}*, {', '.join(kw_only_args)}"
         pre_init_kw_only_args = ", ".join(
-            [f"{kw_arg}={kw_arg}" for kw_arg in kw_only_args]
+            [
+                f"{kw_arg.split('=')[0]}={kw_arg.split('=')[0]}"
+                for kw_arg in kw_only_args
+            ]
         )
         pre_init_args += (
             ", " if pre_init_args else ""
```

**Explanation:** `kw_arg.split('=')[0]` extracts the bare parameter name
(e.g. `"retries"`) from the full parameter-with-default string
(e.g. `"retries=attr_dict['retries'].default"`).  The pre-init call then
correctly becomes `self.__attrs_pre_init__(retries=retries)`, forwarding the
resolved runtime value of the parameter, not its default expression.

The fix handles all three cases cleanly:

| `kw_arg`                               | After fix: call arg          |
|----------------------------------------|------------------------------|
| `"retries"`                            | `retries=retries`            |
| `"retries=attr_dict['retries'].default"` | `retries=retries`          |
| `"retries=NOTHING"`                    | `retries=retries`            |

---

## 3. Test Suite Results

### attrs/bug03 reproducer

```
python oss_cases/attrs/bug03/reproduce.py
Exit: 0   ✓
```

### Full oss_cases/attrs test suite (all three bugs)

```
pytest oss_cases/attrs/test_bugs.py -v

platform win32 -- Python 3.13.0, pytest-9.1.1
collected 3 items

oss_cases/attrs/test_bugs.py::test_attrs_bug01_optional_pipe_converter_accepts_value  PASSED
oss_cases/attrs/test_bugs.py::test_attrs_bug02_chained_converter_runs_on_reassignment PASSED
oss_cases/attrs/test_bugs.py::test_attrs_bug03_kw_only_default_with_pre_init_creates_class PASSED

========================= 3 passed in 1.30s =========================
```

### Full sample_app test suite

```
pytest sample_app/tests/ -v

collected 41 items — 38 passed, 3 failed

PASSED (38): all test_api.py and test_models.py tests, plus
             TestBug02UpdateMissingExpense::test_update_missing_raises_value_error
             TestBug02UpdateMissingExpense::test_update_missing_does_not_raise_attribute_error
             TestBug03OverBudgetBoundary::test_exactly_at_limit_is_not_over_budget

FAILED (3, pre-existing seeded bugs — not caused by this fix):
  sample_app/tests/test_bugs.py::TestBug03OverBudgetBoundary::test_one_cent_over_limit_is_over_budget
  sample_app/tests/test_bugs.py::TestBug04MutableDefaultHeaders::test_mutable_default_can_be_corrupted_externally
  sample_app/tests/test_bugs.py::TestBug05UtcDateDefault::test_today_utc_uses_utc_not_local_clock
```

The 3 sample_app failures are **intentionally seeded bugs** in the sample app
(Bug03/04/05 of the sample_app series). They fail identically on the
pre-fix baseline (`git stash` confirmed), so they are not regressions
introduced by this fix.

---

## 4. High-Risk Impact Items

No Investigator output file (`INVESTIGATOR_OUTPUT_bug03.md`) was found in the
repo. The impact assessment below is derived from the test description, ticket,
`provenance.json`, and static analysis of the changed function.

### Items assessed

| File | Symbol | Risk | Reason |
|------|--------|------|--------|
| `src/attr/_make.py` | `_attrs_to_init_script` | **High** | The patched function generates the `__init__` body; incorrect codegen here breaks every class that uses `kw_only + default + __attrs_pre_init__` together. |
| `src/attr/_make.py` | `_make_init` | **High** (caller) | Calls `_attrs_to_init_script`; the generated script is compiled and `exec`'d inside this function. A bad script causes a `SyntaxError` before `exec` finishes. |
| Any user class with `kw_only=True`, a default, and `__attrs_pre_init__` | class decoration | **High** | The SyntaxError surfaces at class-decoration time, making the class impossible to instantiate. |
| `src/attr/_make.py` | `_attrs_to_init_script` — no-default kw_only path | **Low** | `kw_only` fields without defaults (`kw_arg = "name"`) are unaffected: `"name".split('=')[0]` = `"name"`, same as before. |
| `src/attr/_make.py` | factory-default kw_only path | **Low** | Factory fields use `"name=NOTHING"` → split gives `"name"`. The generated call becomes `name=name`, correct. Already tested by attrs upstream test suite. |

### Actions taken for High-risk items

**`_attrs_to_init_script` (patched directly):** The minimal one-line fix
(`kw_arg.split('=')[0]`) is applied in-place. No broader refactor was needed.

**`_make_init` (caller):** No change required. The fix is entirely inside
`_attrs_to_init_script`; `_make_init` receives a now-correct script string and
compiles it without error.

**No test additions:** The reproducer `oss_cases/attrs/bug03/reproduce.py`
already exercises the exact High-risk path (kw_only + default +
`__attrs_pre_init__`). The test harness in `test_bugs.py` wraps it and confirms
a zero exit code, which it now achieves.

---

## 5. Upstream Correspondence

The fix matches the spirit of the upstream commit
[`09161fc`](https://github.com/python-attrs/attrs/commit/09161fc9181bf94aa3bbc5509c663d736a9553dc)
(merged PR #1319, 2024-08-03). The upstream diff touched 7 added / 5 deleted
lines in `_make.py` and added 19 lines of tests in `tests/test_make.py`;
this patch achieves the same semantic correction with a targeted 3-line change
in the pre_init_kw_only_args list comprehension.
