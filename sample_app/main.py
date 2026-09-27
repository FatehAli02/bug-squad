"""
main.py — Command-line interface for the expense tracker.

Usage:
    python main.py add    --title "Coffee" --amount 3.50 --category food
    python main.py list   [--category food] [--month 2024-05]
    python main.py delete --id <uuid>
    python main.py budget --set food 200 2024-05
    python main.py budget --check food 2024-05
    python main.py report --month 2024-05
    python main.py export --out expenses.csv
    python main.py trend  [--months 3]
"""

from __future__ import annotations

import argparse
import sys
from datetime import date, datetime

from api import ExpenseTracker


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _today_utc() -> str:
    """Return today's date as an ISO-8601 string, based on the local clock."""
    return date.today().isoformat()


def _print_expenses(expenses) -> None:
    if not expenses:
        print("  (no expenses found)")
        return
    print(f"  {'Date':<12} {'Category':<14} {'Amount':>8}  Title")
    print("  " + "-" * 58)
    for e in expenses:
        print(f"  {e.date:<12} {e.category:<14} ${e.amount:>7.2f}  {e.title}")


def _print_budget(status: dict) -> None:
    bar_filled = int(status["percent_used"] / 5)
    bar = "#" * bar_filled + "-" * (20 - bar_filled)
    flag = "  *** OVER BUDGET ***" if status["over_budget"] else ""
    print(f"  {status['category']:<14}  [{bar}] {status['percent_used']:>5.1f}%"
          f"  spent=${status['spent']:.2f} / limit=${status['limit']:.2f}{flag}")


# ---------------------------------------------------------------------------
# Sub-commands
# ---------------------------------------------------------------------------

def cmd_add(tracker: ExpenseTracker, args: argparse.Namespace) -> None:
    expense_date = args.date or _today_utc()
    exp = tracker.add_expense(
        title=args.title,
        amount=args.amount,
        category=args.category,
        expense_date=expense_date,
        notes=args.notes,
    )
    print(f"Added expense [{exp.id}]: {exp.title}  ${exp.amount:.2f}  ({exp.date})")


def cmd_list(tracker: ExpenseTracker, args: argparse.Namespace) -> None:
    category = args.category or None
    start = end = None
    if args.month:
        year, month = map(int, args.month.split("-"))
        from utils import month_date_range
        s, e = month_date_range(year, month)
        start = s.isoformat()
        end = e.isoformat()
    expenses = tracker.list_expenses(category=category, start_date=start, end_date=end)
    print(f"\nFound {len(expenses)} expense(s):")
    _print_expenses(expenses)


def cmd_update(tracker: ExpenseTracker, args: argparse.Namespace) -> None:
    exp = tracker.update_expense(
        expense_id=args.id,
        title=args.title,
        amount=args.amount,
        category=args.category,
        notes=args.notes,
    )
    print(f"Updated expense [{exp.id}]: {exp.title}  ${exp.amount:.2f}")


def cmd_delete(tracker: ExpenseTracker, args: argparse.Namespace) -> None:
    removed = tracker.delete_expense(args.id)
    if removed:
        print(f"Deleted expense {args.id}.")
    else:
        print(f"No expense with id {args.id}.", file=sys.stderr)


def cmd_budget(tracker: ExpenseTracker, args: argparse.Namespace) -> None:
    if args.set:
        category, limit_str, month_str = args.set
        budget = tracker.set_budget(category, float(limit_str), month_str)
        print(f"Budget set: {budget.category} = ${budget.monthly_limit:.2f} for {budget.month}")
    elif args.check:
        category, month_str = args.check
        year, month = map(int, month_str.split("-"))
        status = tracker.check_budget(category, year, month)
        if status is None:
            print(f"No budget configured for {category} in {month_str}.")
        else:
            _print_budget(status)
    elif args.all:
        month_str = args.all
        year, month = map(int, month_str.split("-"))
        statuses = tracker.check_all_budgets(year, month)
        if not statuses:
            print(f"No budgets configured for {month_str}.")
        else:
            for s in statuses:
                _print_budget(s)


def cmd_report(tracker: ExpenseTracker, args: argparse.Namespace) -> None:
    if args.month:
        year, month = map(int, args.month.split("-"))
    else:
        from datetime import date
        today = date.today()
        year, month = today.year, today.month
    print(tracker.monthly_report(year, month))


def cmd_export(tracker: ExpenseTracker, args: argparse.Namespace) -> None:
    path = tracker.export_to_csv(args.out)
    print(f"Exported {len(tracker.store.expenses)} expenses to {path}")


def cmd_trend(tracker: ExpenseTracker, args: argparse.Namespace) -> None:
    months = args.months or 3
    trend = tracker.spending_trend(months=months)
    print("\nSpending trend:")
    for label, total in trend:
        print(f"  {label}  ${total:.2f}")


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Expense Tracker CLI",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument("--store", default="expenses.json",
                        help="Path to the JSON data file (default: expenses.json)")
    sub = parser.add_subparsers(dest="command")

    # add
    p_add = sub.add_parser("add", help="Add a new expense")
    p_add.add_argument("--title", required=True)
    p_add.add_argument("--amount", required=True, type=float)
    p_add.add_argument("--category", required=True)
    p_add.add_argument("--date", default=None)
    p_add.add_argument("--notes", default=None)

    # list
    p_list = sub.add_parser("list", help="List expenses")
    p_list.add_argument("--category", default=None)
    p_list.add_argument("--month", default=None, help="YYYY-MM")

    # update
    p_upd = sub.add_parser("update", help="Update an expense")
    p_upd.add_argument("--id", required=True)
    p_upd.add_argument("--title", default=None)
    p_upd.add_argument("--amount", type=float, default=None)
    p_upd.add_argument("--category", default=None)
    p_upd.add_argument("--notes", default=None)

    # delete
    p_del = sub.add_parser("delete", help="Delete an expense by id")
    p_del.add_argument("--id", required=True)

    # budget
    p_bud = sub.add_parser("budget", help="Manage budgets")
    bud_grp = p_bud.add_mutually_exclusive_group(required=True)
    bud_grp.add_argument("--set", nargs=3, metavar=("CATEGORY", "LIMIT", "MONTH"))
    bud_grp.add_argument("--check", nargs=2, metavar=("CATEGORY", "MONTH"))
    bud_grp.add_argument("--all", metavar="MONTH")

    # report
    p_rep = sub.add_parser("report", help="Print monthly report")
    p_rep.add_argument("--month", default=None, help="YYYY-MM (default: current month)")

    # export
    p_exp = sub.add_parser("export", help="Export expenses to CSV")
    p_exp.add_argument("--out", required=True, metavar="FILEPATH")

    # trend
    p_trend = sub.add_parser("trend", help="Show spending trend")
    p_trend.add_argument("--months", type=int, default=3)

    return parser


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

COMMANDS = {
    "add": cmd_add,
    "list": cmd_list,
    "update": cmd_update,
    "delete": cmd_delete,
    "budget": cmd_budget,
    "report": cmd_report,
    "export": cmd_export,
    "trend": cmd_trend,
}


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.command:
        parser.print_help()
        return 1

    tracker = ExpenseTracker(store_path=args.store)
    handler = COMMANDS.get(args.command)
    if handler is None:
        print(f"Unknown command: {args.command}", file=sys.stderr)
        return 1

    try:
        handler(tracker, args)
        return 0
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
