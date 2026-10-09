from expense_store import Expense


def filter_expenses(
    expenses: list[Expense],
    category: str | None = None,
    month: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
) -> list[Expense]:
    """Return a list of expenses matching the given filters, sorted by date then id."""
    matches = []
    for expense in expenses:
        if category and expense["category"] != category:
            continue
        if month and not expense["date"].startswith(month):
            continue
        if date_from and expense["date"] < date_from:
            continue
        if date_to and expense["date"] > date_to:
            continue
        matches.append(expense)
    return sorted(matches, key=lambda e: (e["date"], e["id"]))


def total_spent(expenses: list[Expense]) -> float:
    """Return the sum of all expense amounts (0.0 for an empty list)."""
    return sum(expense["amount"] for expense in expenses)


def total_by_category(expenses: list[Expense]) -> dict[str, float]:
    """Return {category: total}, ordered from biggest spend to smallest."""
    totals: dict[str, float] = {}
    for expense in expenses:
        category = expense["category"]
        totals[category] = totals.get(category, 0.0) + expense["amount"]
    return dict(sorted(totals.items(), key=lambda item: item[1], reverse=True))


def monthly_summary(expenses: list[Expense]) -> dict[str, float]:
    """Return {"YYYY-MM": total}, ordered from the earliest month to the latest."""
    totals: dict[str, float] = {}
    for expense in expenses:
        month = expense["date"][:7]  # "2026-09-14" -> "2026-09"
        totals[month] = totals.get(month, 0.0) + expense["amount"]
    return dict(sorted(totals.items()))


def text_bar_chart(totals: dict[str, float], width: int = 40) -> str:
    """Build a text bar chart with one line per category.

    The largest category gets `width` stars; every other bar is scaled
    proportionally. Any non-zero amount gets at least one star so small
    categories don't vanish. Returns "" if there is nothing to draw.
    """
    if not totals:
        return ""
    largest = max(totals.values())
    if largest <= 0:  # guard against dividing by zero
        return ""

    label_width = max(len(category) for category in totals) + 1  # +1 for the colon
    lines = []
    for category, amount in totals.items():
        stars = max(1, round(amount / largest * width))
        label = f"{category.capitalize()}:"
        lines.append(f"{label:<{label_width}} {'*' * stars} ({amount:,.2f})")
    return "\n".join(lines)
