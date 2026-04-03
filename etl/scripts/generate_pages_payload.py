"""Generate the leaderboard JSON payload consumed by the Pages client.

Supports two modes:
  1. If pre-fetched snapshots exist (e.g. from the fetch workflow artifact),
     aggregate those directly — no network calls.
  2. Otherwise, fetch live from the load balancer for each variant.

Per-variant errors are caught so a single failed variant doesn't block
the entire deploy.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from urllib.parse import urlencode

from dwarfboard_etl.fetch import fetch_snapshot
from dwarfboard_etl.leaderboard import reconcile_variant_transitions, run_leaderboard_pipeline

BASE_URL = "http://loadbalancer-prod-1ac6c83-453346156.us-east-1.elb.amazonaws.com/leaderboards/scores/?"
VARIANTS: dict[str, dict[str, str]] = {
    "solo": {"fellowship": "false", "hardcore": "false"},
    "fellowship": {"fellowship": "true", "hardcore": "false"},
    "hardcore_solo": {"fellowship": "false", "hardcore": "true"},
    "hardcore_fellowship": {"fellowship": "true", "hardcore": "true"},
}


def _has_snapshots(directory: Path) -> bool:
    """Check whether a directory has any non-meta JSON snapshots."""
    if not directory.is_dir():
        return False
    return any(
        p.suffix == ".json" and p.name != "latest.json" and not p.name.endswith(".meta.json")
        for p in directory.iterdir()
    )


def _build_variant(key: str, query: dict[str, str], snapshots_base: Path) -> tuple[str, list[dict[str, object]]]:
    """Build rows for a single variant, fetching live only if no local snapshots exist."""
    variant_dir = snapshots_base / key
    csv_path = Path("etl/data") / f"leaderboard_{key}.csv"

    if not _has_snapshots(variant_dir):
        url = f"{BASE_URL}{urlencode(query)}"
        print(f"  [{key}] No local snapshots, fetching live from {url}")
        fetch_snapshot(url, variant_dir)
    else:
        print(f"  [{key}] Using {sum(1 for _ in variant_dir.glob('*.json'))} existing snapshots")

    return run_leaderboard_pipeline(variant_dir, csv_path, interval_minutes=10)


def main() -> None:
    Path("client/public").mkdir(parents=True, exist_ok=True)
    Path("etl/data").mkdir(parents=True, exist_ok=True)

    snapshots_base = Path("etl/data/raw")
    payload: dict[str, object] = {"variants": {}}
    errors: list[str] = []
    detected_season: str | None = None

    for key, query in VARIANTS.items():
        try:
            season_id, rows = _build_variant(key, query, snapshots_base)
            payload["variants"][key] = rows  # type: ignore[index]
            if detected_season is None and season_id != "unknown":
                detected_season = season_id
            print(f"  [{key}] {len(rows)} rows (season={season_id})")
        except Exception as exc:
            print(f"  [{key}] FAILED: {exc}", file=sys.stderr)
            errors.append(key)
            payload["variants"][key] = []  # type: ignore[index]

    reconcile_variant_transitions(payload["variants"])  # type: ignore[arg-type]

    if detected_season:
        payload["seasonId"] = detected_season

    out_path = Path("client/public/leaderboard.json")
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    total = sum(len(v) for v in payload["variants"].values())
    print(f"Wrote {total} total rows across {len(VARIANTS)} variants to {out_path}")

    if errors:
        print(f"WARNING: {len(errors)} variant(s) failed: {', '.join(errors)}", file=sys.stderr)


if __name__ == "__main__":
    main()
