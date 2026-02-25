"""CLI entrypoint for dwarfBoard ETL and data-fetch workflows."""

from __future__ import annotations

import argparse

from .fetch import fetch_snapshot
from .pipeline import run_pipeline


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run dwarfBoard ETL utilities.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    aggregate_parser = subparsers.add_parser("aggregate", help="Aggregate event CSV into daily metrics")
    aggregate_parser.add_argument("--events", required=True, help="Path to source events CSV")
    aggregate_parser.add_argument("--output", required=True, help="Path for aggregated output CSV")

    fetch_parser = subparsers.add_parser("fetch", help="Fetch leaderboard snapshot")
    fetch_parser.add_argument("--url", required=True, help="Leaderboard endpoint URL")
    fetch_parser.add_argument(
        "--output-dir",
        default="etl/data/raw",
        help="Directory to write fetched snapshots and metadata",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()

    if args.command == "aggregate":
        rows = run_pipeline(args.events, args.output)
        print(f"Wrote {len(rows)} rows to {args.output}")
        return

    if args.command == "fetch":
        result = fetch_snapshot(args.url, args.output_dir)
        print(
            "Fetched snapshot "
            f"status={result.status_code} "
            f"at={result.fetched_at} "
            f"body={result.body_path} "
            f"meta={result.metadata_path}"
        )
        return

    raise ValueError(f"Unsupported command: {args.command}")


if __name__ == "__main__":
    main()
