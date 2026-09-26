# Ticket 01 — Last day of month is excluded from monthly expense list

**Component:** Expense Tracker — Monthly Reports / Filtering
**Severity:** Medium
**Reporter:** j.morrison

---

## Description

When I view my monthly report or list expenses for a specific month, expenses
recorded on the **last day of the month** are consistently missing from the
output.  For example, if I enter an expense dated `2024-05-31`, it does not
appear in the May report or in `list --month 2024-05`.  It does appear when I
run `list` without a month filter.

This means my monthly totals are always slightly under-reported, and I cannot
reconcile my end-of-month spending.

---

## Steps to Reproduce

1. Add an expense on the last calendar day of any month:
   ```
   python main.py add --title "Month-end dinner" --amount 45.00 \
       --category food --date 2024-05-31
   ```
2. List expenses for that month:
   ```
   python main.py list --month 2024-05
   ```
3. Run a monthly report:
   ```
   python main.py report --month 2024-05
   ```

**Expected:** The expense dated `2024-05-31` appears in both outputs.

**Actual:** The expense is absent.  Running `python main.py list` (no month
filter) correctly shows the expense.

---

## Additional Notes

Affects all months.  Tested with January (31st), March (31st), April (30th),
and February (28th / 29th in leap years) — the last day is always missing.
