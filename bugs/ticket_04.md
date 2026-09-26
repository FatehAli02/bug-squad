# Ticket 04 — Calling `to_csv_rows` a second time includes extra headers from a previous call

**Component:** Expense Tracker — CSV Export
**Severity:** Low
**Reporter:** alex.w

---

## Description

When I export expenses twice in the same Python session (e.g., in a script or
in the REPL), the second CSV export contains a corrupted header row that
includes extra column names appended from the first export's custom headers.

This does not affect typical single-run CLI usage, but breaks any workflow that
reuses the `to_csv_rows` helper with custom `headers` across multiple calls in
the same process.

---

## Steps to Reproduce

Run the following in a Python REPL (with the `sample_app/` directory on the
path):

```python
from models import Expense
from utils import to_csv_rows

e = Expense.create("Coffee", 3.50, "food")

# First call with a custom header list
rows1 = to_csv_rows([e], headers=["id", "title"])
print(rows1[0])   # Expected: "id,title"

# Second call, also with custom headers
rows2 = to_csv_rows([e], headers=["id", "title"])
print(rows2[0])   # Expected: "id,title"
                  # Actual:   "id,title,id,title"  (or similar duplication)
```

**Expected:** Both calls produce identical output.

**Actual:** On the second call, the `headers` parameter accumulates values from
the first call, producing duplicated column names.

---

## Additional Notes

The problem disappears if the Python process is restarted between calls.  This
is a classic Python footgun: a mutable object used as a default argument value
is shared across all calls that rely on the default.
