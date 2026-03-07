---
name: quicken-simplifi
description: Fetches accounts, transactions, tags, and categories from Quicken Simplifi. Use when the user wants to export Simplifi data, sync transactions, or work with Quicken Simplifi.
---

# Quicken Simplifi skill

Use this skill when the user asks to:
- Export or fetch Quicken Simplifi transactions, accounts, tags, or categories
- Sync or download Simplifi data
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

## Output

Exports are written in the current directory as `{filename}_{accounts|transactions|tags|categories}.{json|csv}`.

## 2FA on macOS

When using email/password, if Quicken sends an SMS like "Your Quicken verification code is 471367", the client can read it from Apple iMessage (`~/Library/Messages/chat.db`) so the user does not need to type the code. Otherwise it falls back to a terminal prompt.
