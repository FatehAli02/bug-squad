"""
models.py — Data models for the expense tracker.

Provides the core Expense and Budget dataclasses, plus a simple
in-memory ExpenseStore that persists to JSON on disk.
"""

from __future__ import annotations

import json
import os
import uuid
from dataclasses import dataclass, field, asdict
from datetime import date, datetime
from typing import List, Optional


# ---------------------------------------------------------------------------
# Expense
# ---------------------------------------------------------------------------

VALID_CATEGORIES = {
    "food",
    "transport",
    "utilities",
    "entertainment",
    "health",
    "shopping",
    "other",
}


@dataclass
class Expense:
    """A single expense record."""

    id: str
    title: str
    amount: float
    category: str
    date: str          # ISO-8601 string: YYYY-MM-DD
    notes: Optional[str] = None

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def create(
        cls,
        title: str,
        amount: float,
        category: str,
        expense_date: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> "Expense":
        if category not in VALID_CATEGORIES:
            raise ValueError(f"Unknown category '{category}'. Valid: {VALID_CATEGORIES}")
        if amount <= 0:
            raise ValueError("Amount must be positive.")
        date_str = expense_date or date.today().isoformat()
        return cls(
            id=str(uuid.uuid4()),
            title=title.strip(),
            amount=round(amount, 2),
            category=category,
            date=date_str,
            notes=notes,
        )

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Expense":
        return cls(**data)


# ---------------------------------------------------------------------------
# Budget
# ---------------------------------------------------------------------------

@dataclass
class Budget:
    """Monthly budget limit per category."""

    category: str
    monthly_limit: float
    month: str  # YYYY-MM

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Budget":
        return cls(**data)


# ---------------------------------------------------------------------------
# ExpenseStore
# ---------------------------------------------------------------------------

@dataclass
class ExpenseStore:
    """Simple JSON-backed store for expenses and budgets."""

    filepath: str
    expenses: List[Expense] = field(default_factory=list)
    budgets: List[Budget] = field(default_factory=list)

    def load(self) -> None:
        if not os.path.exists(self.filepath):
            return
        with open(self.filepath, "r") as fh:
            raw = json.load(fh)
        self.expenses = [Expense.from_dict(e) for e in raw.get("expenses", [])]
        self.budgets = [Budget.from_dict(b) for b in raw.get("budgets", [])]

    def save(self) -> None:
        with open(self.filepath, "w") as fh:
            json.dump(
                {
                    "expenses": [e.to_dict() for e in self.expenses],
                    "budgets": [b.to_dict() for b in self.budgets],
                },
                fh,
                indent=2,
            )
