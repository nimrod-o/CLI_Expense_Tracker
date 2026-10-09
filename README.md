# CLI Expense Tracker

A small command-line app for logging, listing, deleting and summarizing personal
expenses. Data is stored in a local JSON file, and it uses **only the Python
standard library** (Python 3.10+).

## Features

- Log an expense: amount, category, description, and date (defaults to today)
- List expenses, optionally filtered by category, month, or date range
- Delete an expense by ID
- Summarize spending: total, by category, and by month
- Draw a text bar chart of spending per category
- Friendly error messages instead of stack traces

## Project layout

| File                   | Job                                                                 |
| ---------------------- | ------------------------------------------------------------------- |
| `tracker.py`           | Entry point: argparse setup, input validation, printing, dispatching |
| `expense_store.py`     | All file I/O: load, save, add, delete, next ID                      |
| `summary.py`           | Calculations: filtering, totals, monthly summary, text bar chart    |
| `sample_expenses.json` | 14 sample expenses (Aug and Sept 2026, 5 categories)                |
| `requirements.txt`     | Empty on purpose: no third-party packages                           |

## How to run

```bash
# Try it with the sample data first (does not touch your real expenses.json):
python tracker.py --file sample_expenses.json summary

# Or copy the sample data in as your starting point:
cp sample_expenses.json expenses.json

# Or just start adding. expenses.json is created automatically on first use.
python tracker.py add --amount 450 --category food --description "lunch"
```

Amounts have no currency symbol; use whatever currency you like (I use KES).

## Commands

```bash
python tracker.py add --amount 450 --category food --description "lunch"
python tracker.py add --amount 2000 --category rent --date 2026-09-01
python tracker.py list
python tracker.py list --category food
python tracker.py list --month 2026-09
python tracker.py list --from 2026-08-10 --to 2026-08-31
python tracker.py delete --id 3
python tracker.py summary
python tracker.py summary --month 2026-09
python tracker.py chart
```

`--file PATH` (before the command) points the app at a different JSON file.
`summary` and `chart` also accept `--month`.

## Sample output

`python tracker.py --file sample_expenses.json list --month 2026-09`

```
ID  Date        Category         Amount  Description
--  ----------  -------------  --------  -------------------
 8  2026-09-02  food             380.00  lunch
 9  2026-09-04  transport        250.00  matatu fare
10  2026-09-06  utilities        500.00  internet bundle
11  2026-09-10  food           1,600.00  weekly groceries
12  2026-09-14  entertainment    600.00  movie night
13  2026-09-18  transport        400.00  boda rides
14  2026-09-21  food             520.00  dinner with friends

7 expense(s), total 4,250.00
```

`python tracker.py --file sample_expenses.json summary`

```
Total spent: 15,050.00 (14 expenses)

By category
Category         Amount  Share
-------------  --------  -----
rent           6,500.00  43.2%
food           4,300.00  28.6%
utilities      1,700.00  11.3%
entertainment  1,400.00   9.3%
transport      1,150.00   7.6%

By month
Month       Amount
-------  ---------
2026-08  10,800.00
2026-09   4,250.00
```

`python tracker.py --file sample_expenses.json chart`

```
Spending by category

Rent:          **************************************** (6,500.00)
Food:          ************************** (4,300.00)
Utilities:     ********** (1,700.00)
Entertainment: ********* (1,400.00)
Transport:     ******* (1,150.00)
```

## Error handling

| Situation                             | What happens                                                        |
| ------------------------------------- | ------------------------------------------------------------------- |
| `expenses.json` doesn't exist yet     | Created automatically with an empty list                            |
| File is empty, corrupted, or wrong shape | Warns, then asks whether to start fresh; old file is kept as `.bak` |
| Delete an ID that doesn't exist       | `No expense with ID 99.`                                            |
| Bad `--amount` (text, zero, negative, nan) | argparse-style error, exit code 2                              |
| Bad `--date` / `--month` (e.g. `2026-02-30`) | argparse-style error with the expected format                |
| `summary` / `chart` with no expenses  | `No expenses yet.` plus an example command                          |
| Can't write the file (permissions etc.) | One-line error, no traceback                                      |

## What I learned

- **Separating responsibilities makes each piece simple.** Because only
  `expense_store.py` touches the file and `summary.py` only does math, I could
  test the calculations without worrying about disk or the command line.
- **argparse can do the validating.** Writing small `type=` functions
  (`positive_amount`, `iso_date`, ...) meant bad input gets rejected before my
  real code ever runs, with clean error messages for free.
- **Errors are part of the design.** The first-run case, the corrupted-file
  case and the "empty list" case each needed a decision about what the user
  should see, and thinking about them up front made the code better.
- **Write files safely.** Saving to a temp file and then swapping it into
  place means a crash mid-save can't leave me with a half-written
  `expenses.json`.
- **ISO dates sort as text.** Storing dates as `YYYY-MM-DD` means filtering by
  month or range is just string comparison, with no date parsing in the loop.
- **Small things bite.** Dividing by the largest bar for the chart would crash
  on an empty list, and a tiny amount could round to zero stars. Guarding both
  taught me to ask "what if this is empty, or zero?" for every calculation.
