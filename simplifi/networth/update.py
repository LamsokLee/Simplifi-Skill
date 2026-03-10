#!/usr/bin/env python3
"""
Update net-worth CSV with latest balances from Simplifi API.
1. Check if the net-worth file exists (create with header if not).
2. Call API to get accounts and aggregate balances by category.
3. Append a new row for today, or overwrite existing row for today with latest data.
"""

import argparse
import csv
import os
import sys
from datetime import datetime
from pathlib import Path

from simplifi.api import Client
from simplifi.login.auth import load_cached_token

AGGREGATE_CATEGORIES = [
    "cash_and_checking", "savings", "other_banking", "brokerage",
    "retirement", "other_investments", "vehicle", "total_assets",
    "credit_cards", "other_liabilities", "total_liabilities", "net_worth",
]


def _account_category(account: dict) -> str | None:
    if account.get("isIgnored"):
        return None
    typ = (account.get("type") or "").strip()
    sub = (account.get("subType") or "").strip()
    if typ == "BANK":
        if sub == "CHECKING":
            return "cash_and_checking"
        if sub == "SAVINGS":
            return "savings"
        if sub == "OTHER_BANK":
            return "other_banking"
        return None
    if typ == "INVESTMENT":
        if sub == "BROKERAGE":
            return "brokerage"
        if sub in ("401K", "IRA", "ROTH_IRA"):
            return "retirement"
        if sub == "OTHER_INVESTMENTS":
            return "other_investments"
        return None
    if typ == "VEHICLE":
        return "vehicle"
    if typ == "CREDIT" and sub == "CREDIT_CARD":
        return "credit_cards"
    if typ == "OTHER_LIABILITY":
        return "other_liabilities"
    return None


def _balance(account: dict) -> float:
    v = account.get("currentBalanceAsOf")
    if v is not None and v != 0:
        return float(v)
    v = account.get("onlineBalance")
    if v is not None:
        return float(v)
    return 0.0


def fetch_networth_from_api(client: Client, dataset_id: str) -> dict[str, float]:
    accounts = client.get_accounts(dataset_id)
    by_cat: dict[str, float] = {k: 0.0 for k in AGGREGATE_CATEGORIES}
    for acc in accounts:
        cat = _account_category(acc)
        if cat is None or cat in ("total_assets", "total_liabilities", "net_worth"):
            continue
        by_cat[cat] += _balance(acc)
    total_assets = (
        by_cat["cash_and_checking"] + by_cat["savings"] + by_cat["other_banking"]
        + by_cat["brokerage"] + by_cat["retirement"] + by_cat["other_investments"] + by_cat["vehicle"]
    )
    total_liabilities = by_cat["credit_cards"] + by_cat["other_liabilities"]
    by_cat["total_assets"] = total_assets
    by_cat["total_liabilities"] = total_liabilities
    by_cat["net_worth"] = total_assets + total_liabilities
    return by_cat


def ensure_file_exists(path: Path) -> None:
    if path.exists():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["date"] + AGGREGATE_CATEGORIES)


def read_rows(path: Path) -> tuple[list[str], list[list[str]]]:
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader)
        rows = list(reader)
    return header, rows


def write_csv(path: Path, header: list[str], rows: list[list[str]]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


def update_networth_file(path: Path, today_str: str, by_cat: dict[str, float]) -> None:
    header, rows = read_rows(path)
    date_col = 0
    category_cols = [c for c in header[1:] if c in by_cat] if len(header) > 1 else AGGREGATE_CATEGORIES
    new_row = [today_str] + [f"{by_cat.get(c, 0):.2f}" for c in category_cols]
    replaced = False
    for i, row in enumerate(rows):
        if len(row) > date_col and row[date_col].strip() == today_str:
            rows[i] = new_row
            replaced = True
            break
    if not replaced:
        rows.append(new_row)
    rows.sort(key=lambda r: r[0] if r else "")
    write_csv(path, header, rows)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Update net-worth CSV with latest balances from Simplifi API.",
    )
    parser.add_argument("networth_file", nargs="?", default="data/net_worth.csv", help="Path to net-worth CSV (default: data/net_worth.csv)")
    parser.add_argument("--token", default=None, help="Simplifi OAuth token")
    parser.add_argument("--email", default=None, help="Simplifi email")
    parser.add_argument("--password", default=None, help="Simplifi password")
    parser.add_argument("--date", default=None, metavar="YYYY-MM-DD", help="Use this date instead of today")
    args = parser.parse_args()

    path = Path(args.networth_file).resolve()
    if not path.parent.exists():
        print(f"Error: directory does not exist: {path.parent}", file=sys.stderr)
        return 1

    token = args.token or os.environ.get("SIMPLIFI_TOKEN") or load_cached_token()
    if not token and args.email and args.password:
        client = Client()
        token = client.get_token(email=args.email, password=args.password)
    if not token:
        print("Error: provide --token or --email/--password, or set SIMPLIFI_TOKEN / cache token.", file=sys.stderr)
        return 1

    client = Client()
    if not client.verify_token(token):
        print("Error: invalid or expired token.", file=sys.stderr)
        return 1

    datasets = client.get_datasets()
    if not datasets:
        print("Error: no datasets returned.", file=sys.stderr)
        return 1
    dataset_id = datasets[0]["id"]

    ensure_file_exists(path)
    by_cat = fetch_networth_from_api(client, dataset_id)
    today_str = args.date or datetime.now().strftime("%Y-%m-%d")
    update_networth_file(path, today_str, by_cat)
    print(f"Updated {path} for {today_str}: net_worth={by_cat['net_worth']:,.2f}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
