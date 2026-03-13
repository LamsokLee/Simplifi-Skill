---
name: quicken-simplifi
description: Fetches accounts, transactions, tags, and categories from Quicken Simplifi. Use when the user wants to export Simplifi data, sync transactions, analyze spending (by parent category, net value per category), analyze income (net value per category and month), analyze net worth, or work with Quicken Simplifi.
---

# Quicken Simplifi skill

Use this skill when the user asks to:
- Export or fetch Quicken Simplifi transactions, accounts, tags, or categories
- Sync or download Simplifi data
- Analyze spending (by parent category; one net value per category)
- Analyze income (net value per category and per month; includes returns/adjustments)
- Update net worth (append or overwrite today’s row in net-worth CSV from API)
- Analyze Simplifi net worth (from exported net-worth CSV)
- Use Simplifi data for analysis or backup

## How to run

**Single entry point:** All processes are invoked through one CLI. From repo root (with `PYTHONPATH=.` or deps installed):

```bash
# Using the run script (easiest)
./run login --email you@example.com
./run fetch --transactions
./run spending
./run income
./run networth convert "Simplifi - net-worth.csv" -o data/networth_history.csv
./run networth analyze
./run networth update
```
(Defaults use the **data/** folder: fetch writes transactions as CSV (`data/output_transactions.csv`), accounts/categories/tags as JSON; spending/income read those files; networth → `data/networth_history.csv`.)

Or with Python directly:
```bash
python3 -m simplifi fetch --token="YOUR_TOKEN" --transactions
python3 -m simplifi spending --from 2025-01-01
python3 -m simplifi income
python3 -m simplifi networth convert "Simplifi - net-worth.csv" -o data/networth_history.csv
python3 -m simplifi networth analyze data/networth_history.csv --monthly
python3 -m simplifi networth update
```

**Subcommands:** `login` (log in and cache token), `fetch` (API download), `spending`, `income`, `networth convert|analyze|update`. Run `python3 -m simplifi --help` or `./run --help` for a short guide; run any subcommand with `--help` for its options.

**As OpenClaw skill:** Install the skill and set config (token or email/password). The skill entry point is `skill/run.sh`; OpenClaw runs it with config as environment variables.

**Environment variables** (when run as a skill or by script):
- `SIMPLIFI_TOKEN` – OAuth token (no MFA prompt), or
- `SIMPLIFI_EMAIL` + `SIMPLIFI_PASSWORD` – login (2FA from iMessage on macOS if available)
- `SIMPLIFI_TRANSACTIONS=1`, `SIMPLIFI_ACCOUNTS=1`, `SIMPLIFI_TAGS=1`, `SIMPLIFI_CATEGORIES=1` – which data to fetch (default is transactions)
- `SIMPLIFI_EXPORT_FILENAME` – output file prefix (default `data/output`; transactions→CSV, accounts/categories/tags→JSON)
- `SIMPLIFI_NETWORTH=1` – also run net-worth analysis on the long-format file
- `SIMPLIFI_NETWORTH_FILE` – path to long-format net-worth CSV (default `data/networth_history.csv`)
- `SIMPLIFI_NETWORTH_FROM`, `SIMPLIFI_NETWORTH_TO` – date range for net-worth (YYYY-MM-DD)
- `SIMPLIFI_NETWORTH_MONTHLY=1`, `SIMPLIFI_NETWORTH_QUARTERLY=1`, `SIMPLIFI_NETWORTH_YEARLY=1` – show monthly, quarterly, or yearly net-worth summary (with category breakdown per period; skips daily point-by-point table)
- `SIMPLIFI_NETWORTH_UPDATE=1` – update the net-worth file with latest balances from the API (append a new row for today, or overwrite existing row for today)

## Spending and income analysis

- **Spending** (`./run spending`): Reports by parent category with a single **value** per category (net expense = gross − refunds). Overview shows total gross and total refunds; category table shows net value and count. Also income by parent category. Uses `data/output_transactions.csv`, `data/output_accounts.json`, `data/output_categories.json`.
- **Income** (`./run income`): Overview shows total positive and total negative; category and month tables show a single **value** per row (net = positive − negative). Gives an accurate picture of actual income after refunds, chargebacks, or corrections.

## Output and data folder

All exports and inputs use the **data/** folder by default. Fetch writes transactions as CSV and accounts/categories/tags as JSON (prefix `data/output`). Spending and income read `data/output_transactions.csv`, `data/output_accounts.json`, `data/output_categories.json`. Net-worth uses `data/networth_history.csv`. The directory is created automatically when writing.

## Net-worth analysis

The skill expects a **long-format** net-worth file: one row per day, with header `date` plus category columns (e.g. `date,cash_and_checking,savings,...,net_worth`). The analyzer shows a summary, current value by category, and either a daily table (all dates × categories) or, when using `--monthly`/`--quarterly`/`--yearly`, one row per period with all category values.

**Repo structure:** **simplifi/api/** = Simplifi HTTP client; **simplifi/login/** = auth and token cache; **simplifi/spending/**, **income/**, **networth/** = analysis scripts; **data/** = default exports and net-worth CSV. Invoke via `./run <subcommand>` or `python3 -m simplifi <subcommand>`.

**One-time setup:** Convert a wide Simplifi net-worth export to long format (writes to `data/networth_history.csv` by default):
```bash
./run networth convert "Simplifi - net-worth.csv" -o data/networth_history.csv
```

**Update net-worth from API:** `./run networth update` (default: `data/networth_history.csv`) or set `SIMPLIFI_NETWORTH_UPDATE=1` in the skill.

**As skill:** Set `SIMPLIFI_NETWORTH=1` to run the net-worth analyzer; set `SIMPLIFI_NETWORTH_UPDATE=1` to refresh the file first. Optionally set `SIMPLIFI_NETWORTH_FROM`, `SIMPLIFI_NETWORTH_TO`, `SIMPLIFI_NETWORTH_MONTHLY`, `SIMPLIFI_NETWORTH_QUARTERLY`, `SIMPLIFI_NETWORTH_YEARLY`.

## 2FA on macOS

When using email/password, if Quicken sends an SMS like "Your Quicken verification code is 471367", the client can read it from Apple iMessage (`~/Library/Messages/chat.db`) so the user does not need to type the code. Otherwise it falls back to a terminal prompt.
