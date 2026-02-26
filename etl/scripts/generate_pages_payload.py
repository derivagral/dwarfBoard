from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import urlencode

from dwarfboard_etl.fetch import fetch_snapshot
from dwarfboard_etl.leaderboard import run_leaderboard_pipeline


BASE_URL = "http://loadbalancer-prod-1ac6c83-453346156.us-east-1.elb.amazonaws.com/leaderboards/scores/?"
VARIANTS = {
    "solo": {"fellowship": "false", "hardcore": "false"},
    "fellowship": {"fellowship": "true", "hardcore": "false"},
    "hardcore_solo": {"fellowship": "false", "hardcore": "true"},
    "hardcore_fellowship": {"fellowship": "true", "hardcore": "true"},
}


def main() -> None:
    Path("client/public").mkdir(parents=True, exist_ok=True)
    Path("etl/data").mkdir(parents=True, exist_ok=True)

    payload: dict[str, dict[str, list[dict[str, object]]]] = {"variants": {}}

    for key, query in VARIANTS.items():
        url = f"{BASE_URL}{urlencode(query)}"
        out_dir = Path("etl/data/raw") / key
        fetch_snapshot(url, out_dir)
        rows = run_leaderboard_pipeline(
            out_dir,
            Path("etl/data") / f"leaderboard_{key}.csv",
            interval_minutes=10,
        )
        payload["variants"][key] = rows

    Path("client/public/leaderboard.json").write_text(
        json.dumps(payload, indent=2), encoding="utf-8"
    )
    print("Wrote leaderboard payload variants to client/public/leaderboard.json")


if __name__ == "__main__":
    main()
