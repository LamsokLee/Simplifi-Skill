---
name: quicken-simplifi
description: Fetches accounts, transactions, tags, and categories from Quicken Simplifi. Use when the user wants to export Simplifi data, sync transactions, analyze net worth, or work with Quicken Simplifi.
---

# Quicken Simplifi skill

Use this skill when the user asks to:
- Export or fetch Quicken Simplifi transactions, accounts, tags, or categories
- Sync or download Simplifi data
- Analyze Simplifi net worth (from exported net-worth CSV)
- Use Simplifi data for analysis or backup

## How to run

**As OpenClaw skill** (recommended): Install the skill and set config (token or email/password). The skill entry point is `skill/run.sh`; OpenClaw runs it with config as environment variables.

**Standalone:** Install deps with `pip install -r requirements.txt`, then:
```bash
python3 -m simplifiapi --token="YOUR_TOKEN" --transactions --filename=export --format=csv
python3 -m simplifiapi --email="user@example.com" --password="..." --transactions
```

**Environment variables** (when run as a skill or by script):
- `SIMPLIFI_TOKEN` – OAuth token (no MFA prompt), or
- `SIMPLIFI_EMAIL` + `SIMPLIFI_PASSWORD` – login (2FA from iMessage on macOS if available)
- `SIMPLIFI_TRANSACTIONS=1`, `SIMPLIFI_ACCOUNTS=1`, `SIMPLIFI_TAGS=1`, `SIMPLIFI_CATEGORIES=1` – which data to fetch (default is transactions)
- `SIMPLIFI_EXPORT_FILENAME` – output file prefix (default `simplifi_export`)
- `SIMPLIFI_EXPORT_FORMAT` – `json` or `csv` (default `json`)
- `SIMPLIFI_NETWORTH=1` – also run net-worth analysis on the long-format file
- `SIMPLIFI_NETWORTH_FILE` – path to long-format net-worth CSV (default `net_worth.csv`)
- `SIMPLIFI_NETWORTH_FROM`, `SIMPLIFI_NETWORTH_TO` – date range for net-worth (YYYY-MM-DD)
- `SIMPLIFI_NETWORTH_MONTHLY=1`, `SIMPLIFI_NETWORTH_QUARTERLY=1`, `SIMPLIFI_NETWORTH_YEARLY=1` – show monthly, quarterly, or yearly net-worth summary (with category breakdown per period; skips daily point-by-point table)

## Output

Exports are written in the current directory as `{filename}_{accounts|transactions|tags|categories}.{json|csv}`.

## Net-worth analysis

The skill expects a **long-format** net-worth file: one row per day, with header `date` plus category columns (e.g. `date,cash_and_checking,savings,...,net_worth`). The analyzer shows a summary, current value by category, and either a daily table (all dates × categories) or, when using `--monthly`/`--quarterly`/`--yearly`, one row per period with all category values.

**One-time setup:** If you have a wide Simplifi net-worth export, convert it once to long format (not part of the skill):
```bash
python3 convert_networth.py "Simplifi - net-worth.csv" -o net_worth.csv
```
Then use `net_worth.csv` as your source; daily sync from Simplifi should append new rows to it.

**As skill:** Set `SIMPLIFI_NETWORTH=1` so the skill runs the net-worth analyzer on `net_worth.csv` (or `SIMPLIFI_NETWORTH_FILE`). Optionally set `SIMPLIFI_NETWORTH_FROM`, `SIMPLIFI_NETWORTH_TO`, `SIMPLIFI_NETWORTH_MONTHLY`, `SIMPLIFI_NETWORTH_QUARTERLY`, `SIMPLIFI_NETWORTH_YEARLY`.

**Standalone:** Default output includes summary + current-by-category + daily table. With period flags you get one row per period with all categories (no daily table):
```bash
python3 analyze_networth.py net_worth.csv --from 2026-01-01 --monthly
python3 analyze_networth.py net_worth.csv --quarterly --yearly
```

## 2FA on macOS

When using email/password, if Quicken sends an SMS like "Your Quicken verification code is 471367", the client can read it from Apple iMessage (`~/Library/Messages/chat.db`) so the user does not need to type the code. Otherwise it falls back to a terminal prompt.
