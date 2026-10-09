import argparse
import math
import sys
from datetime import date, datetime
from pathlib import Path

from expense_store import (
    DEFAULT_DATA_FILE,
    CorruptedStoreError,
    Expense,
    add_expense,
    backup_corrupted_file,
    delete_expense,
    load_expenses,
    save_expenses,
)
from summary import (
    filter_expenses,
    monthly_summary,
    text_bar_chart,
    total_by_category,
    total_spent,
)

def positive_amount(text: str) -> float:
    """Convert text to a positive, finite number rounded to 2 decimal places."""
    try:
        value = round(float(text), 2)
    except ValueError:
        raise argparse.ArgumentTypeError(f"amount must be a number, got '{text}'")
    if not math.isfinite(value) or value <= 0:
        raise argparse.ArgumentTypeError("amount must be a positive number")
    return value


def positive_int(text: str) -> int:
    """Convert text to an integer greater than zero (used for expense IDs)."""
    try:
        value = int(text)
    except ValueError:
        raise argparse.ArgumentTypeError(f"ID must be a whole number, got '{text}'")
    if value <= 0:
        raise argparse.ArgumentTypeError("ID must be a positive whole number")
    return value


def iso_date(text: str) -> str:
    """Check that text is a real calendar date and return it as YYYY-MM-DD."""
    try:
        return datetime.strptime(text, "%Y-%m-%d").date().isoformat()
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"'{text}' is not a valid date; use YYYY-MM-DD (e.g. 2026-09-01)"
        )


def year_month(text: str) -> str:
    """Check that text is a valid month and return it as YYYY-MM."""
    try:
        return datetime.strptime(text, "%Y-%m").strftime("%Y-%m")
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"'{text}' is not a valid month; use YYYY-MM (e.g. 2026-09)"
        )


def category_name(text: str) -> str:
    """Normalize a category to trimmed lowercase; reject blank names."""
    cleaned = text.strip().lower()
    if not cleaned:
        raise argparse.ArgumentTypeError("category cannot be blank")
    return cleaned


def money(amount: float) -> str:
    """Format a number as money with thousands separators, e.g. 1,234.50."""
    return f"{amount:,.2f}"


def format_table(
    headers: list[str], rows: list[list[str]], right_aligned: set[int] = frozenset()
) -> str:
    """Return a plain-text table with columns padded to their widest cell.

    `right_aligned` holds the column numbers (starting at 0) to right-align,
    which is what you want for numbers.
    """
    widths = [len(header) for header in headers]
    for row in rows:
        for index, cell in enumerate(row):
            widths[index] = max(widths[index], len(cell))

    def format_row(cells: list[str]) -> str:
        padded = []
        for index, cell in enumerate(cells):
            if index in right_aligned:
                padded.append(cell.rjust(widths[index]))
            else:
                padded.append(cell.ljust(widths[index]))
        return "  ".join(padded).rstrip()

    divider = "  ".join("-" * width for width in widths)
    return "\n".join([format_row(headers), divider] + [format_row(r) for r in rows])


def print_expense_table(expenses: list[Expense]) -> None:
    """Print expenses as an aligned table followed by a count and total."""
    rows = [
        [str(e["id"]), e["date"], e["category"], money(e["amount"]), e["description"]]
        for e in expenses
    ]
    headers = ["ID", "Date", "Category", "Amount", "Description"]
    print(format_table(headers, rows, right_aligned={0, 3}))
    print(f"\n{len(expenses)} expense(s), total {money(total_spent(expenses))}")


def nothing_to_show(all_expenses: list[Expense], selected: list[Expense]) -> bool:
    """Print a friendly message and return True if there is nothing to display."""
    if not all_expenses:
        print("No expenses yet. Add one with:")
        print('  python tracker.py add --amount 450 --category food --description "lunch"')
        return True
    if not selected:
        print("No expenses match those filters.")
        return True
    return False



def handle_add(args: argparse.Namespace) -> int:
    """Handle `add`: save a new expense, defaulting the date to today."""
    expense_date = args.date or date.today().isoformat()
    expense = add_expense(
        args.amount, args.category, args.description.strip(), expense_date, args.file
    )
    print(
        f"Added expense #{expense['id']}: {money(expense['amount'])} "
        f"on {expense['category']} ({expense['date']})"
    )
    return 0


def handle_list(args: argparse.Namespace) -> int:
    """Handle `list`: show expenses, optionally filtered."""
    expenses = load_expenses(args.file)
    selected = filter_expenses(
        expenses, args.category, args.month, args.date_from, args.date_to
    )
    if nothing_to_show(expenses, selected):
        return 0
    print_expense_table(selected)
    return 0


def handle_delete(args: argparse.Namespace) -> int:
    """Handle `delete`: remove one expense by ID."""
    removed = delete_expense(args.id, args.file)
    if removed is None:
        print(f"No expense with ID {args.id}.")
        return 1
    print(
        f"Deleted expense #{removed['id']}: {money(removed['amount'])} "
        f"on {removed['category']} ({removed['date']})"
    )
    return 0


def handle_summary(args: argparse.Namespace) -> int:
    """Handle `summary`: total, per-category breakdown and monthly totals."""
    expenses = load_expenses(args.file)
    selected = filter_expenses(expenses, month=args.month)
    if nothing_to_show(expenses, selected):
        return 0

    total = total_spent(selected)
    scope = f" for {args.month}" if args.month else ""
    print(f"Total spent{scope}: {money(total)} ({len(selected)} expenses)\n")

    print("By category")
    category_rows = [
        [category, money(amount), f"{amount / total * 100:.1f}%" if total else "-"]
        for category, amount in total_by_category(selected).items()
    ]
    print(format_table(["Category", "Amount", "Share"], category_rows, {1, 2}))

    if not args.month:  # a single-month view would make this table redundant
        print("\nBy month")
        month_rows = [[m, money(a)] for m, a in monthly_summary(selected).items()]
        print(format_table(["Month", "Amount"], month_rows, {1}))
    return 0


def handle_chart(args: argparse.Namespace) -> int:
    """Handle `chart`: draw spending per category as a text bar chart."""
    expenses = load_expenses(args.file)
    selected = filter_expenses(expenses, month=args.month)
    if nothing_to_show(expenses, selected):
        return 0

    scope = f" ({args.month})" if args.month else ""
    print(f"Spending by category{scope}\n")
    print(text_bar_chart(total_by_category(selected)))
    return 0


COMMANDS = {
    "add": handle_add,
    "list": handle_list,
    "delete": handle_delete,
    "summary": handle_summary,
    "chart": handle_chart,
}


def build_parser() -> argparse.ArgumentParser:
    """Create the argparse parser with all subcommands and their options."""
    parser = argparse.ArgumentParser(description="A simple command-line expense tracker.")
    parser.add_argument(
        "--file",
        type=Path,
        default=DEFAULT_DATA_FILE,
        help="JSON data file to use (default: expenses.json next to this script)",
    )
    subparsers = parser.add_subparsers(dest="command", required=True, metavar="command")

    add = subparsers.add_parser("add", help="log a new expense")
    add.add_argument("--amount", type=positive_amount, required=True)
    add.add_argument("--category", type=category_name, required=True)
    add.add_argument("--description", default="", help="what the money was for")
    add.add_argument("--date", type=iso_date, help="YYYY-MM-DD (default: today)")

    list_cmd = subparsers.add_parser("list", help="show expenses")
    list_cmd.add_argument("--category", type=category_name)
    list_cmd.add_argument("--month", type=year_month, help="YYYY-MM")
    list_cmd.add_argument("--from", dest="date_from", type=iso_date, help="YYYY-MM-DD")
    list_cmd.add_argument("--to", dest="date_to", type=iso_date, help="YYYY-MM-DD")

    delete = subparsers.add_parser("delete", help="delete an expense by ID")
    delete.add_argument("--id", type=positive_int, required=True)

    summary = subparsers.add_parser("summary", help="totals by category and month")
    summary.add_argument("--month", type=year_month, help="YYYY-MM")

    chart = subparsers.add_parser("chart", help="text bar chart per category")
    chart.add_argument("--month", type=year_month, help="YYYY-MM")

    return parser


def confirm(question: str) -> bool:
    """Ask a yes/no question; anything but y/yes (or no input at all) means no."""
    try:
        answer = input(question)
    except EOFError:  # e.g. input is piped or there is no terminal
        return False
    return answer.strip().lower() in ("y", "yes")


def ensure_store_is_readable(path: Path) -> bool:
    """Make sure the data file can be loaded, offering to reset it if corrupted.

    Returns True if it's safe to continue, False if the user declined.
    """
    try:
        load_expenses(path)  # also creates the file on first run
        return True
    except CorruptedStoreError as error:
        print(f"Warning: {error}")
        if not confirm("Start fresh with an empty expense list? (old file kept as .bak) [y/N] "):
            print("Nothing was changed. Fix or delete the file, then try again.")
            return False
        backup_path = backup_corrupted_file(path)
        save_expenses([], path)
        print(f"Started fresh. The old file was saved as {backup_path.name}.")
        return True


def main(argv: list[str] | None = None) -> int:
    """Parse the command line, check the data file, run the chosen command."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "list" and args.date_from and args.date_to:
        if args.date_from > args.date_to:
            parser.error("--from date must not be later than --to date")

    try:
        if not ensure_store_is_readable(args.file):
            return 1
        return COMMANDS[args.command](args)
    except OSError as error:  # permissions, disk full, bad path...
        print(f"Error: could not read or write {args.file}: {error}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nCancelled.")
        return 130


if __name__ == "__main__":
    sys.exit(main())
