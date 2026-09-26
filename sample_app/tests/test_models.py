"""
tests/test_models.py — Unit tests for models.py
"""

import json
import os
import tempfile
import pytest

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from models import Expense, Budget, ExpenseStore, VALID_CATEGORIES


class TestExpense:
    def test_create_basic(self):
        e = Expense.create("Coffee", 3.50, "food")
        assert e.title == "Coffee"
        assert e.amount == 3.50
        assert e.category == "food"
        assert e.id is not None

    def test_create_strips_title(self):
        e = Expense.create("  Tea  ", 2.00, "food")
        assert e.title == "Tea"

    def test_create_rounds_amount(self):
        e = Expense.create("Lunch", 12.346, "food")
        assert e.amount == 12.35

    def test_create_invalid_category(self):
        with pytest.raises(ValueError, match="Unknown category"):
            Expense.create("X", 1.00, "invalid_cat")

    def test_create_zero_amount(self):
        with pytest.raises(ValueError, match="positive"):
            Expense.create("X", 0, "food")

    def test_create_negative_amount(self):
        with pytest.raises(ValueError, match="positive"):
            Expense.create("X", -5, "food")

    def test_round_trip(self):
        e = Expense.create("Gym", 50.00, "health", "2024-03-15", "monthly fee")
        d = e.to_dict()
        e2 = Expense.from_dict(d)
        assert e2.id == e.id
        assert e2.title == e.title
        assert e2.amount == e.amount
        assert e2.notes == e.notes

    def test_all_valid_categories(self):
        for cat in VALID_CATEGORIES:
            e = Expense.create("Test", 1.00, cat)
            assert e.category == cat


class TestBudget:
    def test_create_and_round_trip(self):
        b = Budget(category="food", monthly_limit=300.0, month="2024-05")
        d = b.to_dict()
        b2 = Budget.from_dict(d)
        assert b2.category == b.category
        assert b2.monthly_limit == b.monthly_limit
        assert b2.month == b.month


class TestExpenseStore:
    def test_save_and_load(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            store = ExpenseStore(filepath=path)
            e = Expense.create("Bus", 2.50, "transport")
            store.expenses.append(e)
            b = Budget(category="transport", monthly_limit=100.0, month="2024-05")
            store.budgets.append(b)
            store.save()

            store2 = ExpenseStore(filepath=path)
            store2.load()
            assert len(store2.expenses) == 1
            assert store2.expenses[0].title == "Bus"
            assert len(store2.budgets) == 1
            assert store2.budgets[0].category == "transport"
        finally:
            os.unlink(path)

    def test_load_missing_file(self):
        store = ExpenseStore(filepath="/tmp/does_not_exist_xyz.json")
        store.load()
        assert store.expenses == []
        assert store.budgets == []

    def test_save_creates_valid_json(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            store = ExpenseStore(filepath=path)
            store.save()
            with open(path) as fh:
                data = json.load(fh)
            assert "expenses" in data
            assert "budgets" in data
        finally:
            os.unlink(path)
