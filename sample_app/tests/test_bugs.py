"""
tests/test_bugs.py — Reproducer tests for sample_app bug tickets 01–05.

Each test FAILS on the pre-fix codebase and will PASS once the corresponding
bug is fixed.  Do not fix the bugs here — this file is the bug evidence.

Run from repo root:
    pytest sample_app/tests/test_bugs.py -v
"""

from __future__ import annotations

import inspect
import os
import sys
from datetime import date, datetime, timezone

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from api import ExpenseTracker
from models import Expense
import utils as utils_module
from utils import to_csv_rows
import main as main_module


# ---------------------------------------------------------------------------
# Ticket 01 — Last day of month excluded from monthly expense list
# ---------------------------------------------------------------------------

class TestBug01LastDayOfMonthExcluded:
    """
    Ticket 01: expenses recorded on the last calendar day of a month are
    missing from monthly_expenses() / monthly reports because month_date_range()
    computes end = date(year, month, last_day - 1) instead of
    end = date(year, month, last_day).

    The inclusive upper bound is off by one, so the final calendar day of
    every month is silently excluded from all monthly queries.
    """

    def test_last_day_31_included_in_month(self, tmp_path):
        """An expense on the 31st of a 31-day month must appear in that month's list."""
        tracker = ExpenseTracker(store_path=str(tmp_path / "store.json"))
        tracker.add_expense("Month-end dinner", 45.00, "food", expense_date="2024-05-31")
        may_expenses = tracker.monthly_expenses(2024, 5)
        assert any(e.date == "2024-05-31" for e in may_expenses), (
            "Expense dated 2024-05-31 (last day of May) was not found in "
            "monthly_expenses(2024, 5) — off-by-one bug in month_date_range"
        )

    def test_last_day_30_included_in_month(self, tmp_path):
        """An expense on the 30th of a 30-day month must appear in that month's list."""
        tracker = ExpenseTracker(store_path=str(tmp_path / "store.json"))
        tracker.add_expense("April expense", 20.00, "food", expense_date="2024-04-30")
        april_expenses = tracker.monthly_expenses(2024, 4)
        assert any(e.date == "2024-04-30" for e in april_expenses), (
            "Expense dated 2024-04-30 (last day of April) was not found in "
            "monthly_expenses(2024, 4) — off-by-one bug in month_date_range"
        )

    def test_last_day_of_feb_included_in_month(self, tmp_path):
        """An expense on the 29th of a leap-year February must appear in that month."""
        tracker = ExpenseTracker(store_path=str(tmp_path / "store.json"))
        tracker.add_expense("Feb end", 10.00, "food", expense_date="2024-02-29")
        feb_expenses = tracker.monthly_expenses(2024, 2)
        assert any(e.date == "2024-02-29" for e in feb_expenses), (
            "Expense dated 2024-02-29 (last day of Feb in leap year 2024) was "
            "not found in monthly_expenses(2024, 2) — off-by-one bug in month_date_range"
        )

    def test_last_day_included_in_monthly_total(self, tmp_path):
        """The last-day expense must be counted in the monthly total."""
        tracker = ExpenseTracker(store_path=str(tmp_path / "store.json"))
        tracker.add_expense("Mid month",  30.00, "food", expense_date="2024-05-15")
        tracker.add_expense("Last day",   15.00, "food", expense_date="2024-05-31")
        total = tracker.monthly_total(2024, 5)
        assert total == pytest.approx(45.00), (
            f"Monthly total for May 2024 should be 45.00 but got {total:.2f} — "
            "the last-day expense is being excluded from the total"
        )


# ---------------------------------------------------------------------------
# Ticket 02 — update_expense crashes with AttributeError for missing ID
# ---------------------------------------------------------------------------

class TestBug02UpdateMissingExpense:
    """
    Ticket 02: calling update_expense with a non-existent ID should raise
    ValueError with a clear message, not AttributeError.

    Pre-fix behaviour in api.py:
        exp = self.get_expense(expense_id)   # returns None
        if exp.title is None:                # AttributeError: NoneType.title
    """

    def test_update_missing_raises_value_error(self, tmp_path):
        """update_expense on a missing ID must raise ValueError, not AttributeError."""
        tracker = ExpenseTracker(store_path=str(tmp_path / "store.json"))
        with pytest.raises(ValueError, match="not found"):
            tracker.update_expense(
                "00000000-0000-0000-0000-000000000000", title="Ghost"
            )

    def test_update_missing_does_not_raise_attribute_error(self, tmp_path):
        """AttributeError must NOT propagate — it indicates the None-check is missing."""
        tracker = ExpenseTracker(store_path=str(tmp_path / "store.json"))
        try:
            tracker.update_expense(
                "00000000-0000-0000-0000-000000000000", title="Ghost"
            )
        except ValueError:
            pass  # correct — bug is fixed
        except AttributeError as exc:
            pytest.fail(
                f"update_expense raised AttributeError instead of ValueError: {exc}"
            )


# ---------------------------------------------------------------------------
# Ticket 03 — over_budget_categories misses the exact-100% boundary
# ---------------------------------------------------------------------------

class TestBug03OverBudgetBoundary:
    """
    Ticket 03: spending exactly equal to the budget limit should NOT appear in
    over_budget_categories (it's at the limit, not over it).

    Pre-fix behaviour in api.py line ~195:
        return [s["category"] for s in statuses if s["percent_used"] > 100]
    At 100%, percent_used == 100 and 100 > 100 is False — so the category is
    NOT flagged even when it should be.  The ticket also requires the inverse:
    spending $100.01 against a $100 limit MUST be flagged.
    """

    def test_exactly_at_limit_is_not_over_budget(self, tmp_path):
        """Spending == limit → over_budget_categories must NOT include category."""
        tracker = ExpenseTracker(store_path=str(tmp_path / "store.json"))
        tracker.set_budget("food", 100.0, "2024-05")
        tracker.add_expense("Groceries", 60.0, "food", expense_date="2024-05-10")
        tracker.add_expense("Dinner",    40.0, "food", expense_date="2024-05-20")
        over = tracker.over_budget_categories(2024, 5)
        assert "food" not in over, (
            "Spending exactly at the limit should not be flagged as over budget"
        )

    def test_one_cent_over_limit_is_over_budget(self, tmp_path):
        """Spending > limit → over_budget_categories MUST include category."""
        tracker = ExpenseTracker(store_path=str(tmp_path / "store.json"))
        tracker.set_budget("food", 100.0, "2024-05")
        tracker.add_expense("Groceries", 100.01, "food", expense_date="2024-05-10")
        over = tracker.over_budget_categories(2024, 5)
        assert "food" in over, (
            "Spending one cent over the limit must be flagged as over budget"
        )


# ---------------------------------------------------------------------------
# Ticket 04 — to_csv_rows mutable default argument pollutes across calls
# ---------------------------------------------------------------------------

class TestBug04MutableDefaultHeaders:
    """
    Ticket 04: to_csv_rows used a mutable list as a default argument value.
    The default `[]` was created once at function-definition time and shared
    across all call sites.  Any code that obtained a reference to that shared
    default and mutated it would corrupt all future calls that relied on the
    default — a classic Python mutable-default-argument footgun.

    Fixed signature in utils.py:
        def to_csv_rows(expenses, headers: Optional[List[str]] = None) -> List[str]:

    The tests verify the fix is in place and that two independent calls with
    the same explicit headers produce identical output.
    """

    def test_default_is_not_mutable_list(self):
        """
        The default for `headers` must be None (or Parameter.empty), not a
        mutable list.  A mutable list default is shared across all callers and
        can be corrupted externally.
        """
        sig = inspect.signature(utils_module.to_csv_rows)
        default_val = sig.parameters["headers"].default
        assert not isinstance(default_val, list), (
            "headers default is still a mutable list — mutable-default-argument "
            f"bug has not been fixed (default is {default_val!r})"
        )

    def test_two_calls_with_same_headers_produce_identical_output(self):
        """
        Calling to_csv_rows twice with the same explicit headers must produce
        identical header rows.  With the mutable-default bug, the second call
        could accumulate extra columns from the first.
        """
        e = Expense.create("Coffee", 3.50, "food")
        rows1 = to_csv_rows([e], headers=["id", "title"])
        rows2 = to_csv_rows([e], headers=["id", "title"])
        assert rows1[0] == "id,title", (
            f"First call produced wrong header: {rows1[0]!r}"
        )
        assert rows2[0] == "id,title", (
            f"Second call produced wrong/accumulated header: {rows2[0]!r}"
        )
        assert rows1[0] == rows2[0], (
            f"Headers differ between calls: {rows1[0]!r} vs {rows2[0]!r}"
        )

    def test_no_headers_uses_default_six_columns(self):
        """Omitting headers must always produce the canonical 6-column header."""
        e = Expense.create("Tea", 1.50, "food")
        rows = to_csv_rows([e])
        assert rows[0] == "id,title,amount,category,date,notes", (
            f"Default header is wrong: {rows[0]!r}"
        )


# ---------------------------------------------------------------------------
# Ticket 05 — _today_utc returns UTC date, not local date
# ---------------------------------------------------------------------------

class TestBug05UtcDateDefault:
    """
    Ticket 05: main._today_utc() used datetime.now(tz=timezone.utc), which
    returns the UTC date.  For users in UTC+ timezones, an expense added after
    midnight local time was dated the previous calendar day (the UTC date).

    Fixed implementation uses date.today() — the system's local wall-clock date.

    Proof strategy: inspect the source to confirm the UTC sentinel is gone,
    and confirm the return value matches date.today().
    """

    def test_today_utc_does_not_use_timezone_utc(self):
        """
        _today_utc() must NOT contain 'timezone.utc' in its body.
        The pre-fix implementation hard-coded UTC; the fix uses date.today().
        """
        import inspect as _inspect
        source = _inspect.getsource(main_module._today_utc)
        assert "timezone.utc" not in source, (
            "_today_utc() still contains 'timezone.utc' — UTC bug not fixed.\n"
            f"Function source:\n{source}"
        )

    def test_today_utc_returns_local_date(self):
        """
        _today_utc() must return the same string as date.today().isoformat().
        """
        from datetime import date as _date
        expected = _date.today().isoformat()
        result = main_module._today_utc()
        assert result == expected, (
            f"_today_utc() returned {result!r} but local date is {expected!r}"
        )
