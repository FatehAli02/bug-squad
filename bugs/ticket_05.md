# Ticket 05 — Expenses added after midnight UTC show yesterday's date for users in UTC+ timezones

**Component:** Expense Tracker — Expense Date Defaulting
**Severity:** Medium
**Reporter:** fatima.al

---

## Description

When I add an expense without specifying a `--date`, the app is supposed to
default to **today's date**.  However, for users located in UTC+ timezones
(e.g., UTC+3, UTC+5:30, UTC+8), expenses added in the early hours of the
morning (after midnight local time but before midnight UTC) are recorded with
**yesterday's date**.

For example: I am in Riyadh (UTC+3).  At 1:00 AM local time on 2024-05-15
(which is 22:00 UTC on 2024-05-14), I add an expense.  The app records the
date as `2024-05-14` instead of `2024-05-15`.

This causes expenses to land in the wrong month at month boundaries, making
my reports inaccurate.

---

## Steps to Reproduce

*This is easiest to reproduce by temporarily changing your system timezone or
by mocking `datetime.now`.*

1. Set your system timezone to `Asia/Riyadh` (UTC+3) or any positive UTC
   offset.
2. Ensure the current time is between 00:00 and 02:59 local time (i.e., the
   previous day in UTC).
3. Add an expense without a date:
   ```
   python main.py add --title "Midnight snack" --amount 8.00 --category food
   ```
4. List expenses:
   ```
   python main.py list
   ```

**Expected:** The expense is dated with **today's local date**.

**Actual:** The expense is dated with **yesterday's date** (UTC date, not
local date).

---

## Additional Notes

The issue is in the date defaulting logic in `main.py`.  The app calls
`datetime.now(tz=timezone.utc)` to get the current date, which returns the
UTC date rather than the user's local date.  It should use
`datetime.now()` (no timezone, relying on the system clock) or
`date.today()` to get the local wall-clock date.
