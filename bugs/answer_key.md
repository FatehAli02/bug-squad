# Answer Key — Seeded Bugs in sample_app/

> **Internal use only — do not share with the Reproducer/Investigator/Fixer
> subagents.  This file is ground truth for validating Blast Radius outputs.**

---

## Bug 01 — Off-by-one: last day of month excluded

| Field | Value |
|-------|-------|
| **File** | `sample_app/utils.py` |
| **Line** | 35 |
| **Symbol** | `month_date_range` |
| **Bug type** | Off-by-one |

**Faulty line:**
```python
end = date(year, month, last_day - 1)
```

**Root cause:**  `last_day` is already the last calendar day of the month
(from `calendar.monthrange`).  Subtracting 1 makes the inclusive end one day
short, so expenses on the final day of the month are excluded from every
monthly query.

**Fix:** Remove the `- 1`:
```python
end = date(year, month, last_day)
```

---

## Bug 02 — Missing None-check before attribute access

| Field | Value |
|-------|-------|
| **File** | `sample_app/api.py` |
| **Line** | 82 |
| **Symbol** | `ExpenseTracker.update_expense` |
| **Bug type** | Missing None-check |

**Faulty line:**
```python
if exp.title is None:
```

**Root cause:**  `self.get_expense(expense_id)` returns `None` when the ID is
not found.  The code then immediately dereferences `.title` on the `None`
object instead of checking whether `exp` itself is `None`.  This raises
`AttributeError: 'NoneType' object has no attribute 'title'` rather than the
intended `ValueError`.

**Fix:**
```python
if exp is None:
    raise ValueError(f"Expense '{expense_id}' not found.")
```

---

## Bug 03 — Wrong comparison operator for over-budget check

| Field | Value |
|-------|-------|
| **File** | `sample_app/utils.py` |
| **Line** | 108 |
| **Symbol** | `budget_status` |
| **Bug type** | Wrong comparison operator |

**Faulty line:**
```python
"over_budget": remaining < 0,
```

**Root cause:**  `remaining = monthly_limit - spent`.  When `spent ==
monthly_limit`, `remaining == 0`, and `0 < 0` is `False` — so exactly hitting
the limit is not flagged.  But the `over_budget_categories` caller in `api.py`
(line ~195) checks `percent_used > 100`, which *would* be `False` at exactly
100%.  The inconsistency means the boundary behaves differently depending on
which code path is used.

Actually, the concrete ticket symptom comes from `over_budget_categories`
(api.py line ~195):

| Field | Value |
|-------|-------|
| **File** | `sample_app/api.py` |
| **Line** | 195 |
| **Symbol** | `ExpenseTracker.over_budget_categories` |

**Faulty line:**
```python
return [s["category"] for s in statuses if s["percent_used"] > 100]
```

**Root cause:**  `>` should be `>=` — "over budget" means spending has
reached or exceeded the limit.  At exactly 100%, `> 100` is `False`, so the
category is not flagged even though the budget is fully consumed.  The user
report (ticket 03) describes spending of exactly $100 against a $100 limit
showing as over budget via `budget --check` (which reads `remaining < 0` —
that is also `False` at exactly $100/$100, so neither path behaves
consistently).

The simplest single-line fix is to change `remaining < 0` in `budget_status`
to `remaining <= 0`, AND change `> 100` to `>= 100` in
`over_budget_categories`:
```python
# utils.py line 108
"over_budget": remaining <= 0,
# api.py line 195
return [s["category"] for s in statuses if s["percent_used"] >= 100]
```

---

## Bug 04 — Mutable default argument

| Field | Value |
|-------|-------|
| **File** | `sample_app/utils.py` |
| **Line** | 153 |
| **Symbol** | `to_csv_rows` |
| **Bug type** | Mutable default argument |

**Faulty line:**
```python
def to_csv_rows(expenses: List[Expense], headers: List[str] = []) -> List[str]:
```

**Root cause:**  The default value `[]` is evaluated once at function
definition time and shared across all calls that do not supply `headers`.
When a caller passes a non-empty list on one call, the default list object is
mutated (via the `headers if headers else default_headers` branch — but more
critically if any code ever appended to `headers`).  Even without explicit
mutation, passing a list in one call and relying on the default in another
produces the well-known Python "mutable default argument" bug where state
leaks between calls.

**Fix:**
```python
def to_csv_rows(expenses: List[Expense], headers: Optional[List[str]] = None) -> List[str]:
    default_headers = ["id", "title", "amount", "category", "date", "notes"]
    row_headers = headers if headers is not None else default_headers
    ...
```

---

## Bug 05 — UTC date used instead of local date

| Field | Value |
|-------|-------|
| **File** | `sample_app/main.py` |
| **Line** | 27 |
| **Symbol** | `_today_utc` |
| **Bug type** | Incorrect date/timezone handling |

**Faulty line:**
```python
return datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
```

**Root cause:**  `datetime.now(tz=timezone.utc)` returns the current UTC
time.  For users in UTC+ timezones, the UTC date can lag their local date by
up to 14 hours.  An expense added at 01:00 local time in UTC+3 will be dated
the previous calendar day.

**Fix:** Use the system's local clock:
```python
def _today_local() -> str:
    return date.today().isoformat()
```

---

## Summary table

| # | Ticket | File | Line | Bug type |
|---|--------|------|------|----------|
| 1 | ticket_01.md | `sample_app/utils.py` | 35 | Off-by-one |
| 2 | ticket_02.md | `sample_app/api.py` | 82 | Missing None-check |
| 3 | ticket_03.md | `sample_app/api.py` | 195 | Wrong comparison operator |
| 4 | ticket_04.md | `sample_app/utils.py` | 153 | Mutable default argument |
| 5 | ticket_05.md | `sample_app/main.py` | 27 | Incorrect timezone handling |
