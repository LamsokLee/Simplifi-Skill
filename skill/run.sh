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

exec python3 -m simplifiapi "${ARGS[@]}"
