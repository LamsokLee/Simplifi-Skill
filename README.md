# simplifiapi
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
./run fetch --token="..." --transactions
./run spending
./run income
./run networth convert "Simplifi - net-worth.csv" -o data/net_worth.csv
./run networth analyze
./run networth update
```
(Defaults use the **data/** folder for exports and net-worth CSV.)

Or: `python3 -m simplifiapi <subcommand> [options]`. Run `./run --help` or `python3 -m simplifiapi --help` for subcommands.

## Repo layout

- **simplifiapi/** — Single Python package (client, cli, login, spending, income, networth)
- **data/** — Default location for exports and net-worth CSV (`data/output_*.json|csv`, `data/net_worth.csv`); created automatically
- **skill/** — OpenClaw skill entry script
- **run** — Convenience script: `./run <subcommand> [options]`
- **README.md**, **SKILL.md**, **skill.yaml**, **requirements.txt**

## CLI

```shell
# Subcommands: fetch (default), spending, income, networth convert|analyze|update
python3 -m simplifiapi --help
python3 -m simplifiapi fetch --help
python3 -m simplifiapi fetch --token="..." --transactions --format=csv
python3 -m simplifiapi networth analyze net_worth.csv --monthly
```

## Python API

The `Client` class allows accessing from python script and making custom analysis.

```python
from simplifiapi.client import Client

client = Client()

# Provide either token or email/password
token = "..."
token = client.get_token(email=options.email, password=options.password)

assert client.verify_token(token)

# Datasets own transactions and accounts
datasets = client.get_datasets()
datasetId = datasets[0]["id"]

# Access transactions
transactions = client.get_transactions(datasetId)
```

## Thanks

This library is heavily inspired by [mintapi](https://github.com/mintapi/mintapi).