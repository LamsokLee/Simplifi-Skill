#!/usr/bin/env python3
"""
Analyze net-worth from long-format CSV (date, net_worth or date + category columns).
Use convert_networth.py to create long format from a wide Simplifi export.
"""

import argparse
import csv
import re
import sys
from datetime import datetime
from pathlib import Path


def parse_value(s: str) -> float | None:
    """Parse value like $1,234.56 or (1,234.56) to float. Returns None if empty or invalid."""
    s = (s or "").strip()
    if not s:
        return None
    s = s.replace("$", "").replace(",", "").replace("(", "-").replace(")", "")
    try:
        return float(s)
    except ValueError:
        return None


def parse_date_value(s: str) -> datetime | None:
    """Parse date string YYYY-MM-DD or M/D/YY to datetime."""
    s = (s or "").strip()
    if not s:
        return None
    # YYYY-MM-DD
    m = re.match(r"^(\d{4})-(\d{1,2})-(\d{1,2})$", s)
    if m:
        try:
            return datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            return None
    # M/D/YY or M/D/YYYY
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


def load_networth_long(path: str | Path) -> tuple[list[tuple[datetime, dict[str, float | None]]], list[str]] | None:
    """
    Load long-format CSV: header "date,net_worth" or "date,...,net_worth" (one row per day).
    Returns (rows, category_columns) where each row is (date, {col: value}), or None if not this format.
    category_columns = all columns except date, in file order.
    """
    path = Path(path)
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = [c.strip().lower().replace(" ", "_") for c in next(reader)]
        if len(header) < 2:
            return None
        if "date" not in header[0] and "date" not in header:
            return None
        date_col = 0 if "date" in header[0] else (header.index("date") if "date" in header else 0)
        category_columns = [h for i, h in enumerate(header) if i != date_col]
        rows = []
        for row in reader:
            if len(row) <= date_col:
                continue
            dt = parse_date_value(row[date_col])
            if dt is None:
                continue
            values = {}
            for i, col in enumerate(header):
                if i == date_col:
                    continue
                v = parse_value(row[i]) if i < len(row) else None
                values[col] = v
            rows.append((dt, values))
        if not rows:
            return None
        return (sorted(rows, key=lambda x: x[0]), category_columns)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Analyze net-worth from long-format CSV (date,net_worth or date + category columns). Use convert_networth.py to create long format from a wide Simplifi export.",
    )
    parser.add_argument(
        "csv_file",
        help="Path to long-format net-worth CSV (e.g. net_worth.csv)",
    )
    parser.add_argument(
        "--from",
        dest="from_date",
        metavar="YYYY-MM-DD",
        help="Start of date range",
    )
    parser.add_argument(
        "--to",
        dest="to_date",
        metavar="YYYY-MM-DD",
        help="End of date range",
    )
    parser.add_argument(
        "--monthly",
        action="store_true",
        help="Show monthly summary (last value per month)",
    )
    parser.add_argument(
        "--quarterly",
        action="store_true",
        help="Show quarterly summary (last value per quarter)",
    )
    parser.add_argument(
        "--yearly",
        action="store_true",
        help="Show yearly summary (last value per year)",
    )
    args = parser.parse_args()

    path = Path(args.csv_file)
    if not path.exists():
        print(f"Error: file not found: {path}", file=sys.stderr)
        sys.exit(1)

    from_dt = datetime.strptime(args.from_date, "%Y-%m-%d") if args.from_date else None
    to_dt = datetime.strptime(args.to_date, "%Y-%m-%d") if args.to_date else None

    # Analysis only supports long-format CSV (header: date,net_worth or date,...,net_worth)
    loaded = load_networth_long(path)
    if loaded is None:
        print("Error: file is not long format. Expected CSV with header 'date,net_worth' (or date plus category columns). Use convert_networth.py to create long format from a wide Simplifi export.", file=sys.stderr)
        sys.exit(1)
    rows_long, category_columns = loaded
    filtered_rows = [(d, row) for d, row in rows_long if (from_dt is None or d.date() >= from_dt.date()) and (to_dt is None or d.date() <= to_dt.date())]
    if not filtered_rows:
        print("No data in the specified date range.", file=sys.stderr)
        sys.exit(0)

    net_worth_col = "net_worth" if "net_worth" in category_columns else (category_columns[-1] if category_columns else None)
    series = [(d, row.get(net_worth_col)) for d, row in filtered_rows if row.get(net_worth_col) is not None]
    if not series:
        print("No net worth values in the specified date range.", file=sys.stderr)
        sys.exit(0)

    values_only = [v for _, v in series]
    last_row = filtered_rows[-1][1]
    current = values_only[-1]
    min_val = min(values_only)
    max_val = max(values_only)
    first_val = values_only[0]
    growth = current - first_val if first_val is not None and first_val != 0 else None
    growth_pct = (growth / first_val * 100) if growth is not None and first_val else None

    print("=" * 60)
    print("Net Worth Summary")
    print("=" * 60)
    if args.from_date or args.to_date:
        dr = []
        if args.from_date:
            dr.append(f"from {args.from_date}")
        if args.to_date:
            dr.append(f"to {args.to_date}")
        print(f"  Date range: {' '.join(dr)}")
    print(f"  Data points: {len(series)}")
    print(f"  Current (last): {current:,.2f}")
    print(f"  Min:            {min_val:,.2f}")
    print(f"  Max:            {max_val:,.2f}")
    if growth is not None:
        print(f"  Growth (period): {growth:+,.2f}" + (f" ({growth_pct:+.1f}%)" if growth_pct is not None else ""))

    print()
    print("  By category (current):")
    print(f"  {'Category':<22} {'Value':>14}")
    print("  " + "-" * 38)
    for col in category_columns:
        v = last_row.get(col)
        if v is not None:
            print(f"  {col:<22} {v:>14,.2f}")
        else:
            print(f"  {col:<22} {'—':>14}")

    period_mode = args.monthly or args.quarterly or args.yearly
    if not period_mode:
        print()
        print("  By category at each point in time:")
        date_width = 12
        col_width = 14
        sep = " "
        header = "  " + "date".ljust(date_width) + sep + sep.join(c[:col_width].rjust(col_width) for c in category_columns)
        print(header)
        print("  " + "-" * (date_width + len(category_columns) * (col_width + len(sep))))
        for d, row in filtered_rows:
            parts = [d.strftime("%Y-%m-%d").ljust(date_width)]
            for c in category_columns:
                v = row.get(c)
                parts.append((f"{v:,.2f}" if v is not None else "—").rjust(col_width))
            print("  " + sep.join(parts))

    col_width = 14
    sep = " "

    if args.monthly:
        by_month: dict[tuple[int, int], dict[str, float | None]] = {}
        for d, row in filtered_rows:
            key = (d.year, d.month)
            by_month[key] = row
        print()
        print("  Monthly (last value per month, by category):")
        period_width = 10
        header = "  " + "Year-Mon".ljust(period_width) + sep + sep.join(c[:col_width].rjust(col_width) for c in category_columns)
        print(header)
        print("  " + "-" * (period_width + len(category_columns) * (col_width + len(sep))))
        for (yr, mo), row in sorted(by_month.items()):
            parts = [f"{yr}-{mo:02d}".ljust(period_width)]
            for c in category_columns:
                v = row.get(c)
                parts.append((f"{v:,.2f}" if v is not None else "—").rjust(col_width))
            print("  " + sep.join(parts))

    if args.quarterly:
        by_quarter: dict[tuple[int, int], dict[str, float | None]] = {}
        for d, row in filtered_rows:
            q = (d.month - 1) // 3 + 1
            key = (d.year, q)
            by_quarter[key] = row
        print()
        print("  Quarterly (last value per quarter, by category):")
        period_width = 10
        header = "  " + "Year-Q".ljust(period_width) + sep + sep.join(c[:col_width].rjust(col_width) for c in category_columns)
        print(header)
        print("  " + "-" * (period_width + len(category_columns) * (col_width + len(sep))))
        for (yr, q), row in sorted(by_quarter.items()):
            parts = [f"{yr}-Q{q}".ljust(period_width)]
            for c in category_columns:
                v = row.get(c)
                parts.append((f"{v:,.2f}" if v is not None else "—").rjust(col_width))
            print("  " + sep.join(parts))

    if args.yearly:
        by_year: dict[int, dict[str, float | None]] = {}
        for d, row in filtered_rows:
            by_year[d.year] = row
        print()
        print("  Yearly (last value per year, by category):")
        period_width = 10
        header = "  " + "Year".ljust(period_width) + sep + sep.join(c[:col_width].rjust(col_width) for c in category_columns)
        print(header)
        print("  " + "-" * (period_width + len(category_columns) * (col_width + len(sep))))
        for yr, row in sorted(by_year.items()):
            parts = [str(yr).ljust(period_width)]
            for c in category_columns:
                v = row.get(c)
                parts.append((f"{v:,.2f}" if v is not None else "—").rjust(col_width))
            print("  " + sep.join(parts))


if __name__ == "__main__":
    main()
