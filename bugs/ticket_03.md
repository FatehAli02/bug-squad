# Ticket 03 — Budget "over budget" alert triggers at exactly 100% but not beyond

**Component:** Expense Tracker — Budget Tracking
**Severity:** Medium
**Reporter:** t.chen

---

## Description

The `over_budget_categories` feature is supposed to warn me when I have
**exceeded** my monthly budget for a category.  However, when my spending is
**exactly equal to** the budget limit, the category shows up as "over budget"
even though I have not gone over.  Conversely, if I am even a few cents
**above** the limit (e.g., limit = $100.00, spent = $100.01), the category is
also flagged — so the flag triggers in the wrong place.

In short: the over-budget condition fires one spending unit too early.

---

## Steps to Reproduce

1. Set a food budget of $100 for May 2024:
   ```
   python main.py budget --set food 100 2024-05
   ```
2. Add expenses totalling exactly $100:
   ```
   python main.py add --title "Groceries" --amount 60.00 --category food --date 2024-05-10
   python main.py add --title "Dinner"    --amount 40.00 --category food --date 2024-05-20
   ```
3. Check budget status:
   ```
   python main.py budget --check food 2024-05
   ```

**Expected:** `over_budget: False` (spending equals the limit, not over it).

**Actual:** The category is flagged as over budget; `percent_used` is `100.0`
and `over_budget` is `True`.

---

## Additional Notes

Spending of $100.01 against a $100 limit should flag as over budget.  Spending
of exactly $100.00 should not.  The boundary condition appears to be
implemented with the wrong operator.
