"""expense_store.py -- everything that touches the expenses JSON file.

No other module reads or writes files. Keeping all file I/O here means the
rest of the program never has to think about paths, encodings or JSON errors.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

Expense = dict[str, Any]

DEFAULT_DATA_FILE = Path(__file__).resolve().parent / "expenses.json"

REQUIRED_FIELDS = ("id", "amount", "category", "description", "date")


class CorruptedStoreError(Exception):
    """Raised when the data file exists but its contents can't be understood."""


def _is_valid_expense(entry: Any) -> bool:
    """Return True if `entry` looks like a well-formed expense record."""
    if not isinstance(entry, dict):
        return False
    if any(field not in entry for field in REQUIRED_FIELDS):
        return False

    types_ok = (
        isinstance(entry["id"], int)
        and isinstance(entry["amount"], (int, float))
        and isinstance(entry["category"], str)
        and isinstance(entry["description"], str)
        and isinstance(entry["date"], str)
    )
    if not types_ok:
        return False

    try:
        datetime.strptime(entry["date"], "%Y-%m-%d")
    except ValueError:
        return False
    return True


def save_expenses(expenses: list[Expense], path: Path = DEFAULT_DATA_FILE) -> None:
    """Write the full list of expenses to disk as pretty-printed JSON.

    We write to a temporary file first and then swap it into place. If the
    program is interrupted mid-write, the original file is left untouched
    instead of ending up half-written (i.e. corrupted).
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(path.name + ".tmp")
    temp_path.write_text(json.dumps(expenses, indent=2) + "\n", encoding="utf-8")
    temp_path.replace(path)


def load_expenses(path: Path = DEFAULT_DATA_FILE) -> list[Expense]:
    """Read all expenses from disk.

    - Missing file (first run): create it containing an empty list, return [].
    - Empty, invalid or wrongly-shaped file: raise CorruptedStoreError so the
      caller can decide what to do (we never silently throw data away here).
    """
    if not path.exists():
        save_expenses([], path)
        return []

    try:
        with path.open(encoding="utf-8") as file:
            data = json.load(file)
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise CorruptedStoreError(
            f"{path.name} is empty or is not valid JSON ({error})."
        ) from error

    if not isinstance(data, list) or not all(_is_valid_expense(e) for e in data):
        raise CorruptedStoreError(
            f"{path.name} is valid JSON but is not a list of expense records."
        )
    return data


def backup_corrupted_file(path: Path = DEFAULT_DATA_FILE) -> Path:
    """Move a corrupted data file aside (to <name>.bak) and return the new path.

    This lets the user "start fresh" without permanently destroying the old
    file, in case they want to repair it by hand.
    """
    backup_path = path.with_name(path.name + ".bak")
    path.replace(backup_path)
    return backup_path


def get_next_id(expenses: list[Expense]) -> int:
    """Return the next unused ID: one more than the largest existing ID."""
    if not expenses:
        return 1
    return max(expense["id"] for expense in expenses) + 1


def add_expense(
    amount: float,
    category: str,
    description: str,
    date: str,
    path: Path = DEFAULT_DATA_FILE,
) -> Expense:
    """Append a new expense to the file and return the record that was saved."""
    expenses = load_expenses(path)
    new_expense: Expense = {
        "id": get_next_id(expenses),
        "amount": amount,
        "category": category,
        "description": description,
        "date": date,
    }
    expenses.append(new_expense)
    save_expenses(expenses, path)
    return new_expense


def delete_expense(expense_id: int, path: Path = DEFAULT_DATA_FILE) -> Expense | None:
    """Delete the expense with the given ID.

    Returns the deleted record, or None if no expense has that ID.
    """
    expenses = load_expenses(path)
    for index, expense in enumerate(expenses):
        if expense["id"] == expense_id:
            removed = expenses.pop(index)
            save_expenses(expenses, path)
            return removed
    return None
