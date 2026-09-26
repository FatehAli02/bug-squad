# Ticket 02 — `update_expense` crashes with AttributeError instead of a clear "not found" error

**Component:** Expense Tracker — Expense Management
**Severity:** High
**Reporter:** priya.k

---

## Description

When I try to update an expense using an ID that does not exist, the app
crashes with a confusing `AttributeError: 'NoneType' object has no attribute
'title'` instead of a clear "not found" error message.

The error bubbles up to the terminal with a full traceback, which looks very
unprofessional and is unhelpful for end users.

---

## Steps to Reproduce

1. Run the app with a non-existent expense ID:
   ```
   python main.py update --id 00000000-0000-0000-0000-000000000000 --title "New name"
   ```

**Expected:**
```
Error: Expense '00000000-0000-0000-0000-000000000000' not found.
```

**Actual:**
```
Traceback (most recent call last):
  File "main.py", line ...
  File "api.py", line ...
AttributeError: 'NoneType' object has no attribute 'title'
```

---

## Additional Notes

The `delete_expense` method handles the missing-ID case gracefully (returns
`False`).  The `update_expense` method should follow the same pattern and
raise a `ValueError` with a user-friendly message when the ID is not found.
