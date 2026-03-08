#!/usr/bin/env bash
# OpenClaw skill entry: run simplifiapi with config from environment.
# Config (from OpenClaw vault/config) is typically passed as env vars:
#   SIMPLIFI_TOKEN, or SIMPLIFI_EMAIL + SIMPLIFI_PASSWORD
#   SIMPLIFI_EXPORT_FORMAT, SIMPLIFI_EXPORT_FILENAME
#   SIMPLIFI_ACCOUNTS, SIMPLIFI_TRANSACTIONS, SIMPLIFI_TAGS, SIMPLIFI_CATEGORIES (set to 1 to enable)

set -e

# Run from repo root; PYTHONPATH so "python3 -m simplifiapi" works without pip install
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"
export PYTHONPATH="$REPO_ROOT${PYTHONPATH:+:$PYTHONPATH}"

ARGS=()
if [[ -n "${SIMPLIFI_TOKEN:-}" ]]; then
  ARGS+=(--token="$SIMPLIFI_TOKEN")
elif [[ -n "${SIMPLIFI_EMAIL:-}" && -n "${SIMPLIFI_PASSWORD:-}" ]]; then
  ARGS+=(--email="$SIMPLIFI_EMAIL" --password="$SIMPLIFI_PASSWORD")
else
  echo "Set SIMPLIFI_TOKEN or SIMPLIFI_EMAIL and SIMPLIFI_PASSWORD." >&2
  exit 1
fi

# Data to fetch (default: transactions)
HAVE_DATA=0
[[ -n "${SIMPLIFI_ACCOUNTS:-}" ]]    && { ARGS+=(--accounts);    HAVE_DATA=1; }
[[ -n "${SIMPLIFI_TRANSACTIONS:-}" ]] && { ARGS+=(--transactions); HAVE_DATA=1; }
[[ -n "${SIMPLIFI_TAGS:-}" ]]         && { ARGS+=(--tags);         HAVE_DATA=1; }
[[ -n "${SIMPLIFI_CATEGORIES:-}" ]]   && { ARGS+=(--categories);   HAVE_DATA=1; }
[[ "$HAVE_DATA" -eq 0 ]] && ARGS+=(--transactions)

ARGS+=(--filename="${SIMPLIFI_EXPORT_FILENAME:-simplifi_export}")
ARGS+=(--format="${SIMPLIFI_EXPORT_FORMAT:-json}")

# Run Simplifi API (fetch accounts, transactions, etc.)
python3 -m simplifiapi "${ARGS[@]}"

# Optional: run net-worth analysis if requested and file exists
NETWORTH_FILE="${SIMPLIFI_NETWORTH_FILE:-net_worth.csv}"
if [[ -n "${SIMPLIFI_NETWORTH:-}" ]]; then
  if [[ -f "$REPO_ROOT/$NETWORTH_FILE" ]]; then
    echo "--- Net Worth Analysis ---" >&2
    NW_ARGS=("$REPO_ROOT/$NETWORTH_FILE")
    [[ -n "${SIMPLIFI_NETWORTH_FROM:-}" ]] && NW_ARGS+=(--from "$SIMPLIFI_NETWORTH_FROM")
    [[ -n "${SIMPLIFI_NETWORTH_TO:-}" ]] && NW_ARGS+=(--to "$SIMPLIFI_NETWORTH_TO")
    [[ -n "${SIMPLIFI_NETWORTH_MONTHLY:-}" ]] && NW_ARGS+=(--monthly)
    [[ -n "${SIMPLIFI_NETWORTH_QUARTERLY:-}" ]] && NW_ARGS+=(--quarterly)
    [[ -n "${SIMPLIFI_NETWORTH_YEARLY:-}" ]] && NW_ARGS+=(--yearly)
    python3 "$REPO_ROOT/analyze_networth.py" "${NW_ARGS[@]}"
  else
    echo "Net worth file not found: $NETWORTH_FILE (set SIMPLIFI_NETWORTH_FILE to override)." >&2
  fi
fi
