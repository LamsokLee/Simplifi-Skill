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

Install deps and run the CLI via Python:

```shell
pip install -r requirements.txt
python3 -m simplifiapi --token="..." --transactions
```

## CLI

```shell
usage: python3 -m simplifiapi [-h] [--email [EMAIL]] [--password [PASSWORD]] [--token [TOKEN]] [--accounts] [--transactions] [--tags] [--categories] [--filename FILENAME] [--format {json,csv}]

optional arguments:
  -h, --help            show this help message and exit
  --email [EMAIL]       The e-mail address for your Quicken Simplifi account
  --password [PASSWORD]
                        The password for your Quicken Simplifi account
  --token [TOKEN]       Use existing token to bypass MFA check
  --accounts            Retrieve accounts
  --transactions        Retrieve transactions
  --tags                Retrieve tags
  --categories          Retrieve categories
  --filename FILENAME   Write results to file this prefix
  --format {json,csv}   The format used to return data.

examples:
> python3 -m simplifiapi --token="..." --transactions
> python3 -m simplifiapi --token="..." --transactions --filename=20231125 --format=csv
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