#!/usr/bin/env python3
"""
Convert wide Simplifi net-worth CSV (Account/Time, Subaccount, Concept, date columns)
to long format: one row per day with columns date + category aggregates.
Run once to create net_worth.csv; then use simplifi networth analyze on the long file.
"""

import argparse
import csv
import re
import sys
from datetime import datetime
from pathlib import Path


def parse_date_col(s: str) -> datetime | None:
    """Parse date column header M/D/YY or M/D/YYYY to date."""
    s = (s or "").strip()
    if not s or s in ("Account/Time", "Subaccount", "Concept"):
        return None
    m = re.match(r"^(\d{1,2})/(\d{1,2})/(\d{2,4})$", s)
    if m:
        mo, day, yr = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if yr < 100:
            yr += 2000 if yr < 50 else 1900
        try:
            return datetime(yr, mo, day)
        except ValueError:
            return None
    return None


def parse_value(s: str) -> float | None:
    """Parse value like $1,234.56 or (1,234.56) to float."""
    s = (s or "").strip()
    if not s:
        return None
    s = s.replace("$", "").replace(",", "").replace("(", "-").replace(")", "")
    try:
        return float(s)
    except ValueError:
        return None


def load_networth_csv(path: str | Path) -> tuple[list[datetime], list[dict]]:
    """Load wide net-worth CSV. Returns (dates, row dicts)."""
    path = Path(path)
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader)
        dates = []
        date_indices = []
        for i, col in enumerate(header):
            dt = parse_date_col(col)
            if dt is not None:
                dates.append(dt)
                date_indices.append(i)
        rows = []
        for row in reader:
            account = (row[0] if len(row) > 0 else "").strip()
            subaccount = (row[1] if len(row) > 1 else "").strip()
            concept = (row[2] if len(row) > 2 else "").strip()
            values = []
            for i in date_indices:
                v = parse_value(row[i]) if len(row) > i else None
                values.append(v)
            rows.append({
                "account": account,
                "subaccount": subaccount,
                "concept": concept,
                "values": values,
            })
    return dates, rows


AGGREGATE_CATEGORIES = [
    "cash_and_checking", "savings", "other_banking", "brokerage",
    "retirement", "other_investments", "vehicle", "total_assets",
    "credit_cards", "other_liabilities", "total_liabilities", "net_worth",
]


def _category_key(account: str, subaccount: str, concept: str) -> str | None:
    a, b, c = account.strip(), subaccount.strip(), concept.strip()
    if a == "Total Assets":
        return "total_assets"
    if a == "Total Liabilities":
        return "total_liabilities"
    if a == "Total Net Worth":
        return "net_worth"
    if a == "Assets":
        if b == "Cash & Checking" and c:
            return "cash_and_checking"
        if b == "Savings" and c:
            return "savings"
        if b == "Other Banking" and c:
            return "other_banking"
        if b == "Brokerage" and c:
            return "brokerage"
        if b == "Retirement" and c:
            return "retirement"
        if b == "Other Investments" and c:
            return "other_investments"
        if b == "Vehicle" and c:
            return "vehicle"
    if a == "Liabilities":
        if b == "Credit Cards" and c:
            return "credit_cards"
        if b == "Other Liabilities" and c:
            return "other_liabilities"
    return None


def aggregate_by_category(dates: list[datetime], rows: list[dict]) -> dict[str, list[float | None]]:
    current_account = ""
    current_subaccount = ""
    n = len(dates)
    by_cat: dict[str, list[float | None]] = {}
    for k in AGGREGATE_CATEGORIES:
        by_cat[k] = [0.0] * n if k not in ("total_assets", "total_liabilities", "net_worth") else [None] * n
    for row in rows:
        a, b, c = row["account"], row["subaccount"], row["concept"]
        if a:
            current_account = a
        if b:
            current_subaccount = b
        key = _category_key(row["account"] or current_account, row["subaccount"] or current_subaccount, c)
        if key is None:
            continue
        values = row["values"]
        for j, v in enumerate(values):
            if j >= n:
                break
            if v is None:
                continue
            if key in ("total_assets", "total_liabilities", "net_worth"):
                by_cat[key][j] = v
            else:
                by_cat[key][j] = (by_cat[key][j] or 0) + v
    return by_cat


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert wide Simplifi net-worth CSV to long format (one row per day, columns per category).",
    )
    parser.add_argument("csv_file", help="Path to wide-format net-worth CSV (e.g. Simplifi - net-worth.csv)")
    parser.add_argument("-o", "--output", default="data/net_worth.csv", help="Output path (default: data/net_worth.csv)")
    args = parser.parse_args()

    path = Path(args.csv_file)
    if not path.exists():
        print(f"Error: file not found: {path}", file=sys.stderr)
        sys.exit(1)

    dates, rows = load_networth_csv(path)
    if not dates or not rows:
        print("Error: no date columns or rows in CSV.", file=sys.stderr)
        sys.exit(1)

    by_cat = aggregate_by_category(dates, rows)
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["date"] + AGGREGATE_CATEGORIES)
        for j, d in enumerate(dates):
            out_row = [d.strftime("%Y-%m-%d")]
            for k in AGGREGATE_CATEGORIES:
                v = by_cat[k][j] if j < len(by_cat[k]) else None
                out_row.append(f"{v:.2f}" if v is not None else "")
            w.writerow(out_row)

    print(f"Wrote {len(dates)} rows to {out_path}", file=sys.stderr)
    print("To add a new day, append one row with date and values for each category.", file=sys.stderr)


if __name__ == "__main__":
    main()
