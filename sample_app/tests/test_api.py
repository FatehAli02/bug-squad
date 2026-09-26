"""
tests/test_api.py — Integration tests for api.py (ExpenseTracker)
"""

import os
import sys
import tempfile
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from api import ExpenseTracker


@pytest.fixture
def tracker(tmp_path):
    """Return a fresh ExpenseTracker backed by a temp file."""
    store_file = str(tmp_path / "test_expenses.json")
    return ExpenseTracker(store_path=store_file)


class TestAddExpense:
    def test_add_returns_expense(self, tracker):
        e = tracker.add_expense("Taxi", 15.00, "transport")
        assert e.title == "Taxi"
        assert e.amount == 15.00

    def test_add_persists(self, tracker):
        tracker.add_expense("Taxi", 15.00, "transport")
        # Re-open the same store
        tracker2 = ExpenseTracker(store_path=tracker.store.filepath)
        assert len(tracker2.store.expenses) == 1

    def test_add_invalid_category(self, tracker):
        with pytest.raises(ValueError):
            tracker.add_expense("Taxi", 15.00, "flying_carpet")

    def test_add_with_date(self, tracker):
        e = tracker.add_expense("Pizza", 12.00, "food", expense_date="2024-03-10")
        assert e.date == "2024-03-10"


class TestGetUpdateDelete:
    def test_get_existing(self, tracker):
        e = tracker.add_expense("Water", 1.00, "food")
        fetched = tracker.get_expense(e.id)
        assert fetched.id == e.id

    def test_get_missing_returns_none(self, tracker):
        assert tracker.get_expense("nonexistent-id") is None

    def test_update_title(self, tracker):
        e = tracker.add_expense("Wter", 1.00, "food")
        updated = tracker.update_expense(e.id, title="Water")
        assert updated.title == "Water"

    def test_update_amount(self, tracker):
        e = tracker.add_expense("Coffee", 3.00, "food")
        updated = tracker.update_expense(e.id, amount=4.00)
        assert updated.amount == 4.00

    def test_update_missing_raises(self, tracker):
        with pytest.raises((ValueError, AttributeError)):
            tracker.update_expense("no-such-id", title="X")

    def test_delete_existing(self, tracker):
        e = tracker.add_expense("Juice", 2.00, "food")
        assert tracker.delete_expense(e.id) is True
        assert tracker.get_expense(e.id) is None

    def test_delete_missing(self, tracker):
        assert tracker.delete_expense("no-such-id") is False


class TestListFiltering:
    def test_list_all(self, tracker):
        tracker.add_expense("A", 1.00, "food")
        tracker.add_expense("B", 2.00, "transport")
        assert len(tracker.list_expenses()) == 2

    def test_filter_category(self, tracker):
        tracker.add_expense("A", 1.00, "food")
        tracker.add_expense("B", 2.00, "transport")
        results = tracker.list_expenses(category="food")
        assert len(results) == 1
        assert results[0].title == "A"

    def test_filter_date_range(self, tracker):
        tracker.add_expense("A", 1.00, "food", expense_date="2024-03-05")
        tracker.add_expense("B", 1.00, "food", expense_date="2024-03-15")
        tracker.add_expense("C", 1.00, "food", expense_date="2024-04-01")
        results = tracker.list_expenses(start_date="2024-03-01", end_date="2024-03-31")
        assert len(results) == 2


class TestMonthlyExpenses:
    def test_monthly_expenses(self, tracker):
        tracker.add_expense("A", 10.00, "food", expense_date="2024-05-01")
        tracker.add_expense("B", 20.00, "food", expense_date="2024-05-15")
        tracker.add_expense("C", 5.00, "food", expense_date="2024-06-01")
        may = tracker.monthly_expenses(2024, 5)
        assert len(may) == 2

    def test_monthly_total(self, tracker):
        tracker.add_expense("A", 10.00, "food", expense_date="2024-05-10")
        tracker.add_expense("B", 20.00, "food", expense_date="2024-05-15")
        assert tracker.monthly_total(2024, 5) == pytest.approx(30.00)


class TestBudget:
    def test_set_and_get(self, tracker):
        budget = tracker.set_budget("food", 200.0, "2024-05")
        fetched = tracker.get_budget("food", "2024-05")
        assert fetched.monthly_limit == 200.0

    def test_replace_budget(self, tracker):
        tracker.set_budget("food", 200.0, "2024-05")
        tracker.set_budget("food", 300.0, "2024-05")
        assert tracker.get_budget("food", "2024-05").monthly_limit == 300.0

    def test_check_budget_no_budget(self, tracker):
        assert tracker.check_budget("food", 2024, 5) is None

    def test_check_budget_under(self, tracker):
        tracker.set_budget("food", 200.0, "2024-05")
        tracker.add_expense("Lunch", 50.00, "food", expense_date="2024-05-10")
        status = tracker.check_budget("food", 2024, 5)
        assert status["over_budget"] is False
        assert status["spent"] == pytest.approx(50.00)

    def test_over_budget_categories(self, tracker):
        tracker.set_budget("food", 20.0, "2024-05")
        tracker.add_expense("Big dinner", 100.00, "food", expense_date="2024-05-10")
        over = tracker.over_budget_categories(2024, 5)
        assert "food" in over


class TestExport:
    def test_export_csv(self, tracker, tmp_path):
        tracker.add_expense("Coffee", 3.50, "food")
        out = str(tmp_path / "out.csv")
        tracker.export_to_csv(out)
        with open(out) as fh:
            lines = fh.read().splitlines()
        assert lines[0].startswith("id,")
        assert len(lines) == 2  # header + 1 data row

    def test_export_empty(self, tracker, tmp_path):
        out = str(tmp_path / "empty.csv")
        tracker.export_to_csv(out)
        with open(out) as fh:
            lines = fh.read().splitlines()
        assert len(lines) == 1  # header only
