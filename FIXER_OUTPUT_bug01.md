# Fix summary

### Diff

**File changed:** `oss_cases/attrs/bug01/upstream/src/attr/converters.py`

```diff
-from ._make import NOTHING, Factory, pipe
+from ._make import NOTHING, Converter, Factory, pipe

-    def optional_converter(val):
+    def optional_converter(val, instance, field):
         if val is None:
             return None
+        if isinstance(converter, Converter):
+            return converter(val, instance, field)
         return converter(val)

-    xtr = _AnnotationExtractor(converter)
+    c = converter.__call__ if isinstance(converter, Converter) else converter
+    xtr = _AnnotationExtractor(c)

     ...

-    return optional_converter
+    return Converter(optional_converter, takes_self=True, takes_field=True)
```

### Root cause addressed

The old `optional_converter` was a plain single-argument closure `(val)`. When its inner `converter` argument is a `Converter` object — as returned by `pipe()` in `_make.py` — the stored `__call__` slot is `lambda value, instance, field: ...` (three arguments). Calling it with only `val` raises `TypeError`.

The fix makes `optional_converter` accept `(val, instance, field)` and dispatch: if the inner converter is a `Converter`, pass all three arguments through; otherwise call it as a plain callable with just `val`. Returning a `Converter(optional_converter, takes_self=True, takes_field=True)` ensures that `_make_init` generates the correct three-argument call in the synthesized `__init__`.

### Test results

| Suite | Before fix | After fix |
|---|---|---|
| `attrs/bug01` | ❌ FAILED | ✅ PASSED |
| All other OSS bugs (14) | ❌ FAILED (expected — pre-fix snapshots) | ❌ FAILED (unchanged — correct) |
| `sample_app/tests/` (35) | ✅ PASSED | ✅ PASSED |

### High-risk impacted items

The Investigator flagged three **High** items:

1. **`converters.py / optional`** (High) — **This is the item patched.** The fix is surgical: only `optional` changes; no other function is touched.

2. **`_make.py / pipe`** (High) — No change needed. `pipe()` correctly returns a `Converter` with `takes_self=True, takes_field=True`. The bug was never in `pipe`; it was in `optional` failing to handle what `pipe` returns. After the fix, `pipe` + `optional` compose correctly.

3. **`_make.py / Converter.__call__`** (High) — No change needed. `Converter.__call__` is a correctly implemented slot that dispatches based on `takes_self`/`takes_field` flags. The bug was not in `Converter` itself; it was in `optional` calling it with too few arguments.

The **Medium** item (`src/attrs/converters.py`) is a pure re-export (`from attr.converters import *`) and picks up the fix automatically — no change required there either.
