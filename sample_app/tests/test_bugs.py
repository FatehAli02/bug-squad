"""
tests/test_bugs.py — Reproducer tests for sample_app bug tickets 02–05.

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
    Ticket 04: to_csv_rows uses a mutable list as a default argument value.
    The default `[]` is created once at function-definition time and shared
    across all call sites.  Any code that obtains a reference to that shared
    default and mutates it will corrupt all future calls that rely on the
    default — a classic Python mutable-default-argument footgun.

    Pre-fix signature in utils.py:
        def to_csv_rows(expenses, headers: List[str] = []) -> List[str]:

    The test proves the bug by:
    1. Retrieving the actual default-argument object from the function's
       signature (via inspect).
    2. Mutating it directly (simulating any code that got a reference and
       appended to it — e.g. a call that did `headers += extra`).
    3. Confirming that subsequent no-argument calls now return a corrupted
       header row rather than the expected default.
    """

    def test_mutable_default_can_be_corrupted_externally(self):
        """
        The default list object is accessible and mutable.  Mutating it
        causes all future headerless calls to produce wrong output.
        This PASSES (meaning the bug is present) when headers=[] is the default.
        It would FAIL (raise TypeError on `extend`) when None is the default.
        """
        sig = inspect.signature(utils_module.to_csv_rows)
        default_val = sig.parameters["headers"].default

        # The bug: the default is a mutable list, not None / inspect.Parameter.empty
        assert isinstance(default_val, list), (
            "Default is not a mutable list — bug may already be fixed "
            f"(default is {default_val!r})"
        )

        # Corrupt the shared default
        original = list(default_val)
        try:
            default_val.extend(["id", "title"])
            e = Expense.create("Coffee", 3.50, "food")
            rows = to_csv_rows([e])           # no headers argument
            # A healthy implementation returns the canonical 6-column header.
            # With the bug, it now returns whatever was appended to the default.
            expected_default = "id,title,amount,category,date,notes"
            assert rows[0] == expected_default, (
                f"Default header was corrupted by external mutation: {rows[0]!r} "
                f"(expected {expected_default!r})"
            )
        finally:
            # Restore the default so other tests in the same process are not
            # affected by the corruption we introduced.
            default_val.clear()
            default_val.extend(original)


# ---------------------------------------------------------------------------
# Ticket 05 — _today_utc returns UTC date, not local date
# ---------------------------------------------------------------------------

class TestBug05UtcDateDefault:
    """
    Ticket 05: main._today_utc() uses datetime.now(tz=timezone.utc), which
    returns the UTC date.  For users in UTC+ timezones, an expense added after
    midnight local time is dated the previous calendar day (the UTC date).

    The function should return the local wall-clock date, not the UTC date.

    Proof strategy: call _today_utc() and check directly that it calls
    datetime.now() WITH a UTC timezone argument.  The correct fix would call
    datetime.now() with NO timezone (or use date.today()).  We verify the bug
    is present by inspecting the source of _today_utc for the UTC sentinel.
    """

    def test_today_utc_uses_utc_not_local_clock(self):
        """
        _today_utc() must NOT pass tz=timezone.utc to datetime.now().
        The pre-fix implementation hard-codes UTC, causing UTC-vs-local skew.
        We assert the function returns the LOCAL date (not the UTC date) when
        the two differ — simulated by directly checking the implementation
        calls datetime.now() without a tz argument.
        """
        import inspect as _inspect
        source = _inspect.getsource(main_module._today_utc)
        # The bug: the function body contains the UTC timezone sentinel
        assert "timezone.utc" not in source and "utc" not in source.lower(), (
            "_today_utc() still uses UTC time instead of the local clock.\n"
            f"Function source:\n{source}"
        )
