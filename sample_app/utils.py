"""
utils.py — Utility helpers for the expense tracker.

Includes date helpers, filtering, aggregation, and report formatting.
"""

from __future__ import annotations

import calendar
from datetime import date, datetime, timezone, timedelta
from typing import Dict, List, Optional

from models import Expense


# ---------------------------------------------------------------------------
# Date helpers
# ---------------------------------------------------------------------------

def parse_date(date_str: str) -> date:
    """Parse an ISO-8601 date string into a date object."""
    return datetime.strptime(date_str, "%Y-%m-%d").date()


def current_month_str() -> str:
    """Return the current month as YYYY-MM."""
    return date.today().strftime("%Y-%m")


def month_date_range(year: int, month: int):
    """
    Return the (start, end) date objects for a given calendar month.
    Both start and end are inclusive.
    """
    start = date(year, month, 1)
    last_day = calendar.monthrange(year, month)[1]
    end = date(year, month, last_day)
    return start, end


def days_until_month_end() -> int:
    """Return how many days are left in the current month (including today)."""
    today = date.today()
    last_day = calendar.monthrange(today.year, today.month)[1]
    return last_day - today.day


# ---------------------------------------------------------------------------
# Filtering
# ---------------------------------------------------------------------------

def filter_by_date_range(
    expenses: List[Expense],
    start: date,
    end: date,
) -> List[Expense]:
    """Return expenses whose date falls within [start, end] inclusive."""
    result = []
    for exp in expenses:
        exp_date = parse_date(exp.date)
        if start <= exp_date <= end:
            result.append(exp)
    return result


def filter_by_category(
    expenses: List[Expense],
    category: str,
) -> List[Expense]:
    return [e for e in expenses if e.category == category]


def filter_by_month(expenses: List[Expense], year: int, month: int) -> List[Expense]:
    """Return all expenses that fall within the given calendar month."""
    start, end = month_date_range(year, month)
    return filter_by_date_range(expenses, start, end)


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------

def total_by_category(expenses: List[Expense]) -> Dict[str, float]:
    """Sum expense amounts grouped by category."""
    totals: Dict[str, float] = {}
    for exp in expenses:
        totals[exp.category] = totals.get(exp.category, 0.0) + exp.amount
    return totals


def grand_total(expenses: List[Expense]) -> float:
    return sum(e.amount for e in expenses)


def average_expense(expenses: List[Expense]) -> float:
    if not expenses:
        return 0.0
    return grand_total(expenses) / len(expenses)


# ---------------------------------------------------------------------------
# Budget checking
# ---------------------------------------------------------------------------

def budget_status(
    expenses: List[Expense],
    monthly_limit: float,
    category: str,
    year: int,
    month: int,
) -> dict:
    """
    Return a dict describing spending vs budget for a category/month.
    """
    monthly_expenses = filter_by_month(expenses, year, month)
    cat_expenses = filter_by_category(monthly_expenses, category)
    spent = grand_total(cat_expenses)
    remaining = monthly_limit - spent
    pct = (spent / monthly_limit * 100) if monthly_limit > 0 else 0.0
    return {
        "category": category,
        "month": f"{year}-{month:02d}",
        "limit": monthly_limit,
        "spent": round(spent, 2),
        "remaining": round(remaining, 2),
        "percent_used": round(pct, 1),
        "over_budget": remaining < 0,
    }


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

def top_expenses(expenses: List[Expense], n: int = 5) -> List[Expense]:
    """Return the n most expensive items, sorted descending by amount."""
    sorted_exp = sorted(expenses, key=lambda e: e.amount, reverse=True)
    return sorted_exp[:n]


def summary_report(expenses: List[Expense], month_label: str = "") -> str:
    """Return a human-readable summary string."""
    if not expenses:
        return "No expenses recorded."

    lines = []
    if month_label:
        lines.append(f"=== Expense Summary: {month_label} ===")
    else:
        lines.append("=== Expense Summary ===")

    lines.append(f"Total expenses : {len(expenses)}")
    lines.append(f"Grand total    : ${grand_total(expenses):.2f}")
    lines.append(f"Average        : ${average_expense(expenses):.2f}")
    lines.append("")
    lines.append("By category:")
    for cat, total in sorted(total_by_category(expenses).items()):
        lines.append(f"  {cat:<14} ${total:.2f}")

    lines.append("")
    lines.append(f"Top {min(3, len(expenses))} expenses:")
    for exp in top_expenses(expenses, 3):
        lines.append(f"  [{exp.date}] {exp.title:<25} ${exp.amount:.2f}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Export helpers
# ---------------------------------------------------------------------------

def to_csv_rows(expenses: List[Expense], headers: Optional[List[str]] = None) -> List[str]:
    """
    Convert a list of expenses to CSV-formatted strings.
    Optionally prepend a header row.
    """
    default_headers = ["id", "title", "amount", "category", "date", "notes"]
    row_headers = headers if headers is not None else default_headers
    rows = [",".join(row_headers)]
    for exp in expenses:
        row = [
            exp.id,
            f'"{exp.title}"',
            str(exp.amount),
            exp.category,
            exp.date,
            f'"{exp.notes or ""}"',
        ]
        rows.append(",".join(row))
    return rows


def export_csv(expenses: List[Expense], filepath: str) -> None:
    rows = to_csv_rows(expenses)
    with open(filepath, "w") as fh:
        fh.write("\n".join(rows))
