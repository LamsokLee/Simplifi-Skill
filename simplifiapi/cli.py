import json
import logging
import os
import sys

import configargparse
from pandas import json_normalize

from simplifiapi.client import Client, load_cached_token

logger = logging.getLogger("simplifiapi")

JSON_FORMAT = "json"
CSV_FORMAT = "csv"

_SUBCOMMANDS = ("fetch", "spending", "income", "networth")
_NETWORTH_CMDS = ("convert", "analyze", "update")


def _print_usage():
    print("Usage: python3 -m simplifiapi <subcommand> [options]")
    print()
    print("Subcommands:")
    print("  fetch       Fetch data from Simplifi API (accounts, transactions, tags, categories)")
    print("  spending    Analyze transactions (expense/spending reports)")
    print("  income      Analyze transactions (income-only reports)")
    print("  networth    Net worth: use 'networth convert', 'networth analyze', 'networth update'")
    print()
    print("Examples:")
    print("  python3 -m simplifiapi fetch --transactions --format=csv")
    print("  python3 -m simplifiapi spending --from 2025-01-01")
    print("  python3 -m simplifiapi income")
    print("  python3 -m simplifiapi networth convert 'Simplifi - net-worth.csv' -o net_worth.csv")
    print("  python3 -m simplifiapi networth analyze net_worth.csv --monthly")
    print("  python3 -m simplifiapi networth update net_worth.csv")
    print()
    print("Run a subcommand with --help for its options, e.g. simplifiapi fetch --help")


def parse_arguments(args):
    parser = configargparse.ArgumentParser()

    # Credential
    parser.add_argument('--email',
                        nargs="?",
                        default=None,
                        help="The e-mail address for your Quicken Simplifi account")
    parser.add_argument('--password',
                        nargs="?",
                        default=None,
                        help="The password for your Quicken Simplifi account")
    parser.add_argument('--token',
                        nargs="?",
                        default=None,
                        help="Use existing token to bypass MFA check")

    # Datasets
    parser.add_argument('--accounts',
                        action="store_true",
                        default=False,
                        help="Retrieve accounts")
    parser.add_argument('--transactions',
                        action="store_true",
                        default=False,
                        help="Retrieve transactions")
    parser.add_argument('--tags',
                        action="store_true",
                        default=False,
                        help="Retrieve tags")
    parser.add_argument('--categories',
                        action="store_true",
                        default=False,
                        help="Retrieve categories")

    # Export
    parser.add_argument('--filename',
                        default="data/output",
                        help="Write results to this path prefix (default: data/output -> data/output_*.json|csv)")
    parser.add_argument('--format',
                        choices=[JSON_FORMAT, CSV_FORMAT],
                        default=JSON_FORMAT,
                        help="The format used to return data.")

    return parser.parse_args(args)


def write_data(options, data, name):
    filename = "{}_{}.{}".format(options.filename, name, options.format)
    logger.warn("Saving {} to {}".format(name, filename))
    dirname = os.path.dirname(filename)
    if dirname:
        os.makedirs(dirname, exist_ok=True)
    if options.format == CSV_FORMAT:
        json_normalize(data).to_csv(filename, index=False)
    elif options.format == JSON_FORMAT:
        with open(filename, "w+") as f:
            json.dump(data, f, indent=2)


def _run_fetch(argv):
    options = parse_arguments(argv)
    client = Client()

    token = options.token
    if not token:
        token = load_cached_token()
    if token and client.verify_token(token):
        pass
    else:
        token = None
        if options.email and options.password:
            token = client.get_token(
                email=options.email, password=options.password
            )
        if not token or not client.verify_token(token):
            logger.error("Unable to log in simplifi.")
            return

    # Retrieve first dataset
    # TODO: Support multiple datasets
    datasets = client.get_datasets()
    datasetId = datasets[0]["id"]

    if (options.accounts):
        accounts = client.get_accounts(datasetId)
        write_data(options, accounts, "accounts")

    if (options.transactions):
        transactions = client.get_transactions(datasetId)
        write_data(options, transactions, "transactions")

    if (options.tags):
        tags = client.get_tags(datasetId)
        write_data(options, tags, "tags")

    if (options.categories):
        categories = client.get_categories(datasetId)
        write_data(options, categories, "categories")


def main():
    argv = sys.argv[1:]
    # No args or first arg is a flag (e.g. --help, --token): legacy fetch
    if not argv or argv[0].startswith("-"):
        if argv and argv[0] in ("-h", "--help"):
            _print_usage()
            return
        _run_fetch(argv)
        return
    sub = argv[0].lower()
    if sub in ("-h", "--help"):
        _print_usage()
        return
    if sub == "fetch":
        _run_fetch(argv[1:])
        return
    if sub == "spending":
        sys.argv = [sys.argv[0]] + argv[1:]
        from simplifiapi.spending.analyze import main as spending_main
        spending_main()
        return
    if sub == "income":
        sys.argv = [sys.argv[0]] + argv[1:]
        from simplifiapi.income.analyze import main as income_main
        income_main()
        return
    if sub == "networth":
        if len(argv) < 2:
            print("Usage: python3 -m simplifiapi networth {convert|analyze|update} [options]", file=sys.stderr)
            print("  convert   Wide CSV -> long CSV    analyze   Report on long CSV    update   API -> append/overwrite today", file=sys.stderr)
            sys.exit(1)
        nw_cmd = argv[1].lower()
        if nw_cmd not in _NETWORTH_CMDS:
            print(f"Unknown networth command: {nw_cmd}. Use convert, analyze, or update.", file=sys.stderr)
            sys.exit(1)
        sys.argv = [sys.argv[0]] + argv[2:]
        if nw_cmd == "convert":
            from simplifiapi.networth.convert import main as convert_main
            convert_main()
        elif nw_cmd == "analyze":
            from simplifiapi.networth.analyze import main as analyze_main
            analyze_main()
        else:
            from simplifiapi.networth.update import main as update_main
            sys.exit(update_main())
        return
    if sub in ("help", "h"):
        _print_usage()
        return
    # Unknown subcommand: treat as fetch for backward compat (e.g. someone passed a file)
    _run_fetch(argv)
