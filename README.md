# simplifi
An unofficial API for Quicken Simplifi. Usable as a **standalone Python package** or as an **OpenClaw skill**.

## OpenClaw skill

This repo is an [OpenClaw](https://docs.openclaw.ai/) skill. Use it when you want Simplifi data from an OpenClaw agent.

- **Manifest:** `skill.yaml` (name, permissions, config, shell entry point)
- **Entry script:** `skill/run.sh` — runs the CLI using env config (`SIMPLIFI_TOKEN` or `SIMPLIFI_EMAIL`/`SIMPLIFI_PASSWORD`, plus optional export options)
- **Agent instructions:** `SKILL.md` — when and how to use the skill

Install the skill in your OpenClaw workspace (e.g. clone into `~/.openclaw/workspace/skills/quicken-simplifi`), install deps and set config:

```bash
pip install -r requirements.txt
openclaw skills validate .
```

Set config (token or email/password), then trigger with keywords like *simplifi*, *quicken*, *transactions*.

## Run locally (no OpenClaw)

Install deps and run everything through one CLI:

```shell
pip install -r requirements.txt
./run login --email you@example.com
./run fetch --transactions
./run spending
./run income
./run networth convert "Simplifi - net-worth.csv" -o data/net_worth.csv
./run networth analyze
./run networth update
```
(Defaults use the **data/** folder for exports and net-worth CSV.)

Or: `python3 -m simplifi <subcommand> [options]`. Run `./run --help` or `python3 -m simplifi --help` for subcommands.

## Repo layout

- **simplifi/** — Python package: **api/** (Simplifi HTTP client), **login/** (auth, token cache), **spending/**, **income/**, **networth/** (analysis scripts), **cli.py** (entry)
- **data/** — Default location for exports and net-worth CSV (`data/output_*.json|csv`, `data/net_worth.csv`); created automatically
- **skill/** — OpenClaw skill entry script
- **run** — Convenience script: `./run <subcommand> [options]`
- **README.md**, **SKILL.md**, **skill.yaml**, **requirements.txt**

## CLI

```shell
# Subcommands: login, fetch (default), spending, income, networth convert|analyze|update
python3 -m simplifi --help
python3 -m simplifi login --email you@example.com
python3 -m simplifi fetch --help
python3 -m simplifi fetch --transactions --format=csv
python3 -m simplifi networth analyze --monthly
```

## Python API

The **api** module holds the Simplifi HTTP client; analysis lives in spending/income/networth. Use the client from your own scripts:

```python
from simplifi.api import Client

client = Client()

# Use cached token (e.g. after running: simplifi login) or get one:
token = client.get_token(email="you@example.com", password="...")

assert client.verify_token(token)

# Datasets own transactions and accounts
datasets = client.get_datasets()
datasetId = datasets[0]["id"]

# Access transactions
transactions = client.get_transactions(datasetId)
```

## Thanks

This library is heavily inspired by [mintapi](https://github.com/mintapi/mintapi).