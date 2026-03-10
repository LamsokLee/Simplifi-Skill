#!/usr/bin/env python3
"""
Analyze transactions from output_transactions.csv (Simplifi/Quicken export format).
Reports by category, type, payee, and time period (spending/expense focused).
"""

import argparse
import csv
import json
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path


def load_transactions(path: str) -> list[dict]:
    """Load CSV and return list of row dicts."""
    rows = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows


def parse_amount(s: str) -> float:
    """Parse amount string to float; empty or invalid -> 0."""
    if not s or not s.strip():
        return 0.0
    try:
        return float(s.strip())
    except ValueError:
        return 0.0


def parse_date(s: str):
    """Parse postedOn date; return date or None."""
    if not s or not s.strip():
        return None
    s = s.strip()[:10]
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except ValueError:
        return None


def load_category_names(categories_path: str | Path) -> dict[str, str]:
    """Load output_categories.json and return map of category id -> name."""
    info = load_category_info(categories_path)
    return {cid: data["name"] for cid, data in info.items()}


def load_category_info(categories_path: str | Path) -> dict[str, dict]:
    """Load output_categories.json; return map of category id -> { name, type } (EXPENSE/INCOME)."""
    path = Path(categories_path)
    if not path.exists():
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            categories = json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}
    if not isinstance(categories, list):
        return {}
    out = {}
    for c in categories:
        if not c.get("id"):
            continue
        cid = str(c["id"])
        out[cid] = {
            "name": (c.get("name") or "").strip() or cid,
            "type": (c.get("categoryType") or "EXPENSE").strip().upper() or "EXPENSE",
        }
        if out[cid]["type"] not in ("EXPENSE", "INCOME"):
            out[cid]["type"] = "EXPENSE"
    return out


def get_category_label(row: dict, category_names: dict[str, str] | None = None) -> str:
    """Single label for category."""
    coa_type = (row.get("coa.type") or "").strip() or "UNKNOWN"
    coa_id = (row.get("coa.id") or "").strip()
    cp_cat = (row.get("cpData.cpCategoryId") or "").strip()
    names = category_names or {}
    if coa_type == "CATEGORY" and coa_id:
        if coa_id in names:
            return names[coa_id]
        return f"CATEGORY({coa_id})"
    if cp_cat:
        return f"{coa_type}(cp:{cp_cat})"
    return f"{coa_type}({coa_id or '?'})"


def analyze_by_category(
    rows: list[dict],
    min_amount: float = 0,
    category_names: dict[str, str] | None = None,
    category_info: dict[str, dict] | None = None,
) -> dict[str, dict]:
    """Aggregate by category: income, expense, count."""
    by_cat = defaultdict(lambda: {"income": 0.0, "expense": 0.0, "count": 0})
    for r in rows:
        amt = parse_amount(r.get("amount") or "")
        if abs(amt) < min_amount:
            continue
        coa_type = (r.get("coa.type") or "").strip()
        coa_id = (r.get("coa.id") or "").strip()
        if category_info and coa_type == "CATEGORY" and coa_id in category_info:
            key = coa_id
        else:
            key = get_category_label(r, category_names)
        by_cat[key]["count"] += 1
        if amt > 0:
            by_cat[key]["income"] += amt
        else:
            by_cat[key]["expense"] += abs(amt)
    return dict(by_cat)


def analyze_by_type(rows: list[dict], min_amount: float = 0) -> dict[str, dict]:
    """Aggregate by transaction type."""
    by_type = defaultdict(lambda: {"income": 0.0, "expense": 0.0, "count": 0})
    for r in rows:
        amt = parse_amount(r.get("amount") or "")
        if abs(amt) < min_amount:
            continue
        t = (r.get("type") or "").strip() or "UNKNOWN"
        by_type[t]["count"] += 1
        if amt > 0:
            by_type[t]["income"] += amt
        else:
            by_type[t]["expense"] += abs(amt)
    return dict(by_type)


def analyze_by_coa_type(rows: list[dict], min_amount: float = 0) -> dict[str, dict]:
    """Aggregate by coa.type."""
    by_coa = defaultdict(lambda: {"income": 0.0, "expense": 0.0, "count": 0})
    for r in rows:
        amt = parse_amount(r.get("amount") or "")
        if abs(amt) < min_amount:
            continue
        coa = (r.get("coa.type") or "").strip() or "UNKNOWN"
        by_coa[coa]["count"] += 1
        if amt > 0:
            by_coa[coa]["income"] += amt
        else:
            by_coa[coa]["expense"] += abs(amt)
    return dict(by_coa)


def analyze_by_month(rows: list[dict], min_amount: float = 0) -> dict[str, dict]:
    """Aggregate by year-month."""
    by_month = defaultdict(lambda: {"income": 0.0, "expense": 0.0, "count": 0})
    for r in rows:
        amt = parse_amount(r.get("amount") or "")
        if abs(amt) < min_amount:
            continue
        d = parse_date(r.get("postedOn") or "")
        if not d:
            continue
        key = d.strftime("%Y-%m")
        by_month[key]["count"] += 1
        if amt > 0:
            by_month[key]["income"] += amt
        else:
            by_month[key]["expense"] += abs(amt)
    return dict(sorted(by_month.items()))


def analyze_top_payees(
    rows: list[dict], n: int = 20, expense_only: bool = True, min_amount: float = 0
) -> list[tuple[str, float, int]]:
    """Top N payees by absolute amount."""
    by_payee = defaultdict(lambda: {"total": 0.0, "count": 0})
    for r in rows:
        amt = parse_amount(r.get("amount") or "")
        if abs(amt) < min_amount:
            continue
        if expense_only and amt >= 0:
            continue
        payee = (r.get("payee") or "").strip() or "(no payee)"
        by_payee[payee]["total"] += abs(amt)
        by_payee[payee]["count"] += 1
    sorted_payees = sorted(
        by_payee.items(), key=lambda x: x[1]["total"], reverse=True
    )[:n]
    return [(p, d["total"], d["count"]) for p, d in sorted_payees]


def analyze_by_state(rows: list[dict]) -> dict[str, int]:
    """Count by state."""
    by_state = defaultdict(int)
    for r in rows:
        s = (r.get("state") or "").strip() or "UNKNOWN"
        by_state[s] += 1
    return dict(by_state)


def load_investment_account_ids(accounts_path: str | Path) -> set[str]:
    """Load output_accounts.json and return set of INVESTMENT account IDs."""
    path = Path(accounts_path)
    if not path.exists():
        return set()
    try:
        with open(path, encoding="utf-8") as f:
            accounts = json.load(f)
    except (json.JSONDecodeError, OSError):
        return set()
    if not isinstance(accounts, list):
        return set()
    return {str(a["id"]) for a in accounts if (a.get("type") or "").strip() == "INVESTMENT"}


def filter_rows(
    rows: list[dict],
    from_date: str | None = None,
    to_date: str | None = None,
    state: str | None = None,
    txn_type: str | None = None,
    coa_type: str | None = None,
    exclude_transfers: bool = False,
    exclude_account_ids: set[str] | None = None,
    category_names: dict[str, str] | None = None,
    require_known_category: bool = False,
) -> list[dict]:
    """Filter rows by date, state, type, etc."""
    exclude_account_ids = exclude_account_ids or set()
    out = []
    for r in rows:
        if state and (r.get("state") or "").strip() != state:
            continue
        if txn_type and (r.get("type") or "").strip() != txn_type:
            continue
        if coa_type and (r.get("coa.type") or "").strip() != coa_type:
            continue
        account_id = (r.get("accountId") or "").strip()
        if account_id and account_id in exclude_account_ids:
            continue
        if exclude_transfers:
            coa = (r.get("coa.type") or "").strip()
            if coa in ("BALANCE_ADJUSTMENT", "ACCOUNT"):
                continue
        if require_known_category and category_names:
            coa = (r.get("coa.type") or "").strip()
            coa_id = (r.get("coa.id") or "").strip()
            if coa != "CATEGORY" or coa_id not in category_names:
                continue
        d = parse_date(r.get("postedOn") or "")
        if d is not None:
            if from_date and d < datetime.strptime(from_date, "%Y-%m-%d").date():
                continue
            if to_date and d > datetime.strptime(to_date, "%Y-%m-%d").date():
                continue
        out.append(r)
    return out


def print_section(title: str) -> None:
    print()
    print("=" * 60)
    print(title)
    print("=" * 60)


def print_category_summary(by_cat: dict, limit: int = 25) -> None:
    total_income = sum(d["income"] for d in by_cat.values())
    total_expense = sum(d["expense"] for d in by_cat.values())
    print(f"  Total income:  {total_income:,.2f}")
    print(f"  Total expense: {total_expense:,.2f}")
    print(f"  Net:           {total_income - total_expense:,.2f}")
    print()
    sorted_cats = sorted(
        by_cat.items(),
        key=lambda x: (x[1]["expense"], x[1]["income"]),
        reverse=True,
    )[:limit]
    print(f"  {'Category':<45} {'Expense':>12} {'Income':>12} {'Count':>6}")
    print("  " + "-" * 75)
    for cat, d in sorted_cats:
        print(f"  {cat:<45} {d['expense']:>12,.2f} {d['income']:>12,.2f} {d['count']:>6}")


def print_category_expense_income_sections(
    by_cat: dict[str, dict],
    category_info: dict[str, dict],
    limit: int = 25,
) -> None:
    """Print By category (Expense) and By category (Income) sections."""
    expense_items = []
    income_items = []
    for cid, d in by_cat.items():
        if cid not in category_info:
            continue
        info = category_info[cid]
        if info["type"] == "EXPENSE":
            expense_items.append((info["name"], d))
        else:
            income_items.append((info["name"], d))

    print_section("By category (Expense)")
    total_exp = sum(d["expense"] for _, d in expense_items)
    print(f"  Total expense: {total_exp:,.2f}")
    print()
    print(f"  {'Category':<45} {'Expense':>12} {'Count':>6}")
    print("  " + "-" * 65)
    for name, d in sorted(expense_items, key=lambda x: -x[1]["expense"])[:limit]:
        print(f"  {name:<45} {d['expense']:>12,.2f} {d['count']:>6}")

    print_section("By category (Income)")
    total_inc = sum(d["income"] for _, d in income_items)
    print(f"  Total income:  {total_inc:,.2f}")
    print()
    print(f"  {'Category':<45} {'Income':>12} {'Count':>6}")
    print("  " + "-" * 65)
    for name, d in sorted(income_items, key=lambda x: -x[1]["income"])[:limit]:
        print(f"  {name:<45} {d['income']:>12,.2f} {d['count']:>6}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Analyze transactions from output_transactions.csv"
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
    parser.add_argument("--top", type=int, default=20, help="Top N payees")
    parser.add_argument("--categories", type=int, default=25, help="Max categories to show")
    parser.add_argument("--output-csv", metavar="FILE", help="Write category summary to CSV")
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
    if exclude_account_ids:
        print(f"Excluding {len(exclude_account_ids)} investment account(s)", file=sys.stderr)

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
        txn_type=None,
        exclude_transfers=not args.include_transfers,
        exclude_account_ids=exclude_account_ids,
        category_names=category_names,
        require_known_category=require_known_category,
    )

    print_section("Overview")
    if args.from_date or args.to_date:
        dr = []
        if args.from_date:
            dr.append(f"from {args.from_date}")
        if args.to_date:
            dr.append(f"to {args.to_date}")
        print(f"  Date range: {' '.join(dr)}")
    print(f"  Total transactions: {len(rows)}")
    by_state = analyze_by_state(rows)
    for s, c in sorted(by_state.items(), key=lambda x: -x[1]):
        print(f"  State {s}: {c}")

    print_section("By transaction type (type)")
    by_type = analyze_by_type(rows, min_amount=args.min_amount)
    print_category_summary(by_type, limit=10)

    print_section("By COA type (coa.type)")
    by_coa = analyze_by_coa_type(rows, min_amount=args.min_amount)
    print_category_summary(by_coa, limit=10)

    by_cat = analyze_by_category(
        rows,
        min_amount=args.min_amount,
        category_names=category_names,
        category_info=category_info if category_info else None,
    )
    if category_info:
        print_category_expense_income_sections(by_cat, category_info, limit=args.categories)
    else:
        print_section("By category")
        print_category_summary(by_cat, limit=args.categories)

    print_section("By month")
    by_month = analyze_by_month(rows, min_amount=args.min_amount)
    print(f"  {'Month':<10} {'Expense':>14} {'Income':>14} {'Count':>8}")
    print("  " + "-" * 48)
    for month, d in by_month.items():
        print(f"  {month:<10} {d['expense']:>14,.2f} {d['income']:>14,.2f} {d['count']:>8}")

    print_section(f"Top {args.top} payees (expenses)")
    top = analyze_top_payees(rows, n=args.top, expense_only=True, min_amount=args.min_amount)
    print(f"  {'Payee':<40} {'Total':>12} {'Count':>6}")
    print("  " + "-" * 60)
    for payee, total, count in top:
        short = (payee[:37] + "...") if len(payee) > 40 else payee
        print(f"  {short:<40} {total:>12,.2f} {count:>6}")

    if args.output_csv:
        out_path = Path(args.output_csv)
        with open(out_path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["category", "type", "expense", "income", "count"])
            for cid, d in by_cat.items():
                name = category_info.get(cid, {}).get("name", cid) if category_info else cid
                ctype = category_info.get(cid, {}).get("type", "") if category_info else ""
                w.writerow([name, ctype, f"{d['expense']:.2f}", f"{d['income']:.2f}", d["count"]])
        print()
        print(f"Category summary written to {out_path}")


if __name__ == "__main__":
    main()
