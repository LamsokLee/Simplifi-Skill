#!/usr/bin/env python3
"""
Income-only analysis from output_transactions.csv.
Uses same data as spending; prints only income-related sections.
Shows both positive (income) and negative (returns/adjustments) values with NET totals.
"""

import argparse
import sys
from pathlib import Path

from simplifi.spending.analyze import (
    load_transactions,
    load_category_info,
    load_investment_account_ids,
    filter_rows,
    analyze_by_category,
    analyze_by_month,
    print_section,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Income-only analysis from output_transactions.csv (with NET values)"
    )
    parser.add_argument(
        "csv_file",
        nargs="?",
        default="data/output_transactions.csv",
        help="Path to transactions CSV (default: data/output_transactions.csv)",
    )
    parser.add_argument("--from", dest="from_date", metavar="YYYY-MM-DD", help="Start of date range")
    parser.add_argument("--to", dest="to_date", metavar="YYYY-MM-DD", help="End of date range")
    parser.add_argument("--state", choices=["PENDING", "CLEARED"], help="Filter by state")
    parser.add_argument("--include-transfers", action="store_true", help="Include transfers")
    parser.add_argument("--min-amount", type=float, default=0, help="Min absolute amount")
    parser.add_argument("--categories", type=int, default=25, help="Max categories to show")
    parser.add_argument("--accounts-file", metavar="FILE", default="data/output_accounts.json", help="Accounts JSON")
    parser.add_argument("--categories-file", metavar="FILE", default="data/output_categories.json", help="Categories JSON")
    args = parser.parse_args()

    path = Path(args.csv_file)
    if not path.exists():
        print(f"Error: file not found: {path}", file=sys.stderr)
        sys.exit(1)

    rows = load_transactions(str(path))
    if not rows:
        print("No rows in CSV.", file=sys.stderr)
        sys.exit(0)

    accounts_path = Path(args.accounts_file)
    if not accounts_path.exists():
        print(f"Error: accounts file not found: {accounts_path}", file=sys.stderr)
        sys.exit(1)
    exclude_account_ids = load_investment_account_ids(args.accounts_file)

    categories_path = Path(args.categories_file)
    if not categories_path.exists():
        print(f"Error: categories file not found: {categories_path}", file=sys.stderr)
        sys.exit(1)
    category_info = load_category_info(args.categories_file)
    category_names = {cid: d["name"] for cid, d in category_info.items()} if category_info else {}
    require_known_category = bool(category_info)

    rows = filter_rows(
        rows,
        from_date=args.from_date,
        to_date=args.to_date,
        state=args.state,
        exclude_transfers=not args.include_transfers,
        exclude_account_ids=exclude_account_ids,
        category_names=category_names,
        require_known_category=require_known_category,
    )

    by_cat = analyze_by_category(
        rows,
        min_amount=args.min_amount,
        category_names=category_names,
        category_info=category_info if category_info else None,
    )
    by_month = analyze_by_month(rows, min_amount=args.min_amount)

    # Income items only - calculate NET values
    income_items = []
    for cid, d in by_cat.items():
        if cid not in category_info or category_info[cid]["type"] != "INCOME":
            continue
        net = d["income"] - d["expense"]
        income_items.append((category_info[cid]["name"], {
            "positive": d["income"],
            "negative": d["expense"],
            "net": net,
            "count": d["count"]
        }))

    total_positive = sum(d["positive"] for _, d in income_items)
    total_negative = sum(d["negative"] for _, d in income_items)
    total_net = total_positive - total_negative

    print_section("Income overview")
    if args.from_date or args.to_date:
        dr = []
        if args.from_date:
            dr.append(f"from {args.from_date}")
        if args.to_date:
            dr.append(f"to {args.to_date}")
        print(f"  Date range: {' '.join(dr)}")
    print(f"  Total transactions: {len(rows)}")
    print(f"  Total positive:  {total_positive:,.2f}")
    print(f"  Total negative:  {total_negative:,.2f}")
    print(f"  NET income:      {total_net:,.2f}")

    print_section("By category (Income)")
    print(f"  {'Category':<40} {'Positive':>12} {'Negative':>12} {'NET':>12} {'Count':>6}")
    print("  " + "-" * 82)
    for name, d in sorted(income_items, key=lambda x: -x[1]["net"])[: args.categories]:
        print(f"  {name:<40} {d['positive']:>12,.2f} {d['negative']:>12,.2f} {d['net']:>12,.2f} {d['count']:>6}")

    print_section("By month (income)")
    print(f"  {'Month':<10} {'Positive':>14} {'Negative':>14} {'NET':>14} {'Count':>8}")
    print("  " + "-" * 60)
    for month, d in by_month.items():
        net = d["income"] - d["expense"]
        print(f"  {month:<10} {d['income']:>14,.2f} {d['expense']:>14,.2f} {net:>14,.2f} {d['count']:>8}")


if __name__ == "__main__":
    main()
