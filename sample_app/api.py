"""
api.py — High-level API for the expense tracker.

All user-facing operations go through this module.  It owns an
ExpenseStore instance and delegates data work to utils.py.
"""

from __future__ import annotations

import os
from datetime import date
from typing import Dict, List, Optional, Tuple

from models import Budget, Expense, ExpenseStore, VALID_CATEGORIES
from utils import (
    budget_status,
    export_csv,
    filter_by_category,
    filter_by_date_range,
    filter_by_month,
    grand_total,
    parse_date,
    summary_report,
    to_csv_rows,
    top_expenses,
    total_by_category,
)


# ---------------------------------------------------------------------------
# ExpenseTracker
# ---------------------------------------------------------------------------

class ExpenseTracker:
    """
    The main application object.  Wraps an ExpenseStore and provides
    clean methods for the CLI / test layer.
    """

    def __init__(self, store_path: str = "expenses.json") -> None:
        self.store = ExpenseStore(filepath=store_path)
        self.store.load()

    # ------------------------------------------------------------------
    # Expense CRUD
    # ------------------------------------------------------------------

    def add_expense(
        self,
        title: str,
        amount: float,
        category: str,
        expense_date: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> Expense:
        """Create and persist a new expense."""
        exp = Expense.create(
            title=title,
            amount=amount,
            category=category,
            expense_date=expense_date,
            notes=notes,
        )
        self.store.expenses.append(exp)
        self.store.save()
        return exp

    def get_expense(self, expense_id: str) -> Optional[Expense]:
        """Return the expense with the given id, or None."""
        for exp in self.store.expenses:
            if exp.id == expense_id:
                return exp
        return None

    def update_expense(
        self,
        expense_id: str,
        title: Optional[str] = None,
        amount: Optional[float] = None,
        category: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> Expense:
        """
        Update fields on an existing expense.  Raises ValueError if
        the expense does not exist.
        """
        exp = self.get_expense(expense_id)
        if exp.title is None:
            raise ValueError(f"Expense '{expense_id}' not found.")
        if title is not None:
            exp.title = title.strip()
        if amount is not None:
            if amount <= 0:
                raise ValueError("Amount must be positive.")
            exp.amount = round(amount, 2)
        if category is not None:
            if category not in VALID_CATEGORIES:
                raise ValueError(f"Unknown category '{category}'.")
            exp.category = category
        if notes is not None:
            exp.notes = notes
        self.store.save()
        return exp

    def delete_expense(self, expense_id: str) -> bool:
        """Remove an expense by id.  Returns True if removed, False if not found."""
        original_len = len(self.store.expenses)
        self.store.expenses = [
            e for e in self.store.expenses if e.id != expense_id
        ]
        if len(self.store.expenses) < original_len:
            self.store.save()
            return True
        return False

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def list_expenses(
        self,
        category: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> List[Expense]:
        """List expenses, optionally filtered by category and/or date range."""
        results = list(self.store.expenses)
        if category:
            results = filter_by_category(results, category)
        if start_date and end_date:
            results = filter_by_date_range(
                results,
                parse_date(start_date),
                parse_date(end_date),
            )
        return results

    def monthly_expenses(self, year: int, month: int) -> List[Expense]:
        return filter_by_month(self.store.expenses, year, month)

    def monthly_total(self, year: int, month: int) -> float:
        return grand_total(self.monthly_expenses(year, month))

    def category_totals(
        self, year: Optional[int] = None, month: Optional[int] = None
    ) -> Dict[str, float]:
        if year and month:
            exps = self.monthly_expenses(year, month)
        else:
            exps = self.store.expenses
        return total_by_category(exps)

    def top_n(self, n: int = 5) -> List[Expense]:
        return top_expenses(self.store.expenses, n)

    # ------------------------------------------------------------------
    # Budget management
    # ------------------------------------------------------------------

    def set_budget(self, category: str, monthly_limit: float, month: str) -> Budget:
        """
        Set (or replace) a monthly budget for a category.
        month should be in YYYY-MM format.
        """
        if category not in VALID_CATEGORIES:
            raise ValueError(f"Unknown category '{category}'.")
        if monthly_limit <= 0:
            raise ValueError("Budget limit must be positive.")
        # Remove existing budget for same category+month
        self.store.budgets = [
            b for b in self.store.budgets
            if not (b.category == category and b.month == month)
        ]
        budget = Budget(category=category, monthly_limit=monthly_limit, month=month)
        self.store.budgets.append(budget)
        self.store.save()
        return budget

    def get_budget(self, category: str, month: str) -> Optional[Budget]:
        for b in self.store.budgets:
            if b.category == category and b.month == month:
                return b
        return None

    def check_budget(self, category: str, year: int, month: int) -> Optional[dict]:
        """
        Return a budget status dict for the given category and month,
        or None if no budget is configured.
        """
        month_str = f"{year}-{month:02d}"
        budget = self.get_budget(category, month_str)
        if budget is None:
            return None
        return budget_status(
            self.store.expenses,
            budget.monthly_limit,
            category,
            year,
            month,
        )

    def check_all_budgets(self, year: int, month: int) -> List[dict]:
        """Return budget status for every category that has a budget this month."""
        month_str = f"{year}-{month:02d}"
        results = []
        for budget in self.store.budgets:
            if budget.month == month_str:
                status = budget_status(
                    self.store.expenses,
                    budget.monthly_limit,
                    budget.category,
                    year,
                    month,
                )
                results.append(status)
        return results

    def over_budget_categories(self, year: int, month: int) -> List[str]:
        """Return category names where spending exceeds the budget this month."""
        statuses = self.check_all_budgets(year, month)
        return [s["category"] for s in statuses if s["percent_used"] > 100]

    # ------------------------------------------------------------------
    # Reports
    # ------------------------------------------------------------------

    def monthly_report(self, year: int, month: int) -> str:
        exps = self.monthly_expenses(year, month)
        return summary_report(exps, month_label=f"{year}-{month:02d}")

    def export_to_csv(self, filepath: str) -> str:
        """Export all expenses to a CSV file.  Returns the filepath."""
        export_csv(self.store.expenses, filepath)
        return filepath

    # ------------------------------------------------------------------
    # Statistics helpers
    # ------------------------------------------------------------------

    def spending_trend(self, months: int = 3) -> List[Tuple[str, float]]:
        """
        Return (month_str, total) pairs for the last `months` calendar months,
        ordered oldest-first.
        """
        today = date.today()
        result = []
        for i in range(months - 1, -1, -1):
            # Walk backwards from current month
            month_offset = today.month - 1 - i
            year = today.year + month_offset // 12
            month = month_offset % 12 + 1
            label = f"{year}-{month:02d}"
            total = grand_total(filter_by_month(self.store.expenses, year, month))
            result.append((label, round(total, 2)))
        return result
