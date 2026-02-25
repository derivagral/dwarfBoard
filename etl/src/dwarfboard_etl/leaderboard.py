"""Leaderboard-focused ETL transforms for client-ready leaderboard data."""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

TRACKED_BOSSES = ("zul", "archeon", "bridge", "skorch", "dark")
RUPTURE_MILESTONES = (18, 30, 36, 75, 100, 125, 200)


@dataclass(slots=True)
class LeaderboardRecord:
    account: str
    character: str
    class_name: str
    stance: str
    rupture_level: int
    build_score: int
    snapshots_seen: int


def _extract_entries(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]

    if isinstance(payload, dict):
        for key in ("entries", "players", "leaderboard", "data", "scores"):
            candidate = payload.get(key)
            if isinstance(candidate, list):
                return [row for row in candidate if isinstance(row, dict)]
    return []


def _as_int(value: Any) -> int:
    if isinstance(value, bool):
        return int(value)
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _as_str(value: Any, fallback: str = "") -> str:
    if value is None:
        return fallback
    text = str(value).strip()
    return text or fallback


def _first_clear_flags(entry: dict[str, Any]) -> dict[str, bool]:
    normalized = {str(k).lower(): v for k, v in entry.items()}
    flags: dict[str, bool] = {}

    for boss in TRACKED_BOSSES:
        flag_name = f"first_clear_{boss}"
        value = normalized.get(flag_name)
        if value is None:
            value = normalized.get(f"{boss}_first_clear")
        flags[flag_name] = bool(value)
    return flags


def build_leaderboard_rows(snapshot_paths: list[Path], interval_minutes: int = 60) -> list[dict[str, Any]]:
    """Aggregate leaderboard snapshots into player-centric rows.

    interval_minutes controls the seen-time estimate and allows easy migration
    from current hourly scans to future 10-minute scans without changing downstream consumers.
    """

    players: dict[tuple[str, str], LeaderboardRecord] = {}
    clear_flags: dict[tuple[str, str], dict[str, bool]] = {}

    for path in sorted(snapshot_paths):
        payload = json.loads(path.read_text(encoding="utf-8"))
        entries = _extract_entries(payload)
        for entry in entries:
            account = _as_str(entry.get("account") or entry.get("account_name") or entry.get("user"), "unknown")
            character = _as_str(entry.get("character") or entry.get("character_name"), "unknown")
            key = (account, character)

            record = players.get(key)
            if record is None:
                record = LeaderboardRecord(
                    account=account,
                    character=character,
                    class_name=_as_str(entry.get("class") or entry.get("class_name"), "unknown"),
                    stance=_as_str(entry.get("stance"), "unknown"),
                    rupture_level=_as_int(entry.get("rupture") or entry.get("rupture_level")),
                    build_score=_as_int(entry.get("score") or entry.get("build_score") or entry.get("level")),
                    snapshots_seen=0,
                )
                players[key] = record
                clear_flags[key] = _first_clear_flags(entry)

            record.snapshots_seen += 1
            record.rupture_level = max(record.rupture_level, _as_int(entry.get("rupture") or entry.get("rupture_level")))
            record.build_score = max(record.build_score, _as_int(entry.get("score") or entry.get("build_score") or entry.get("level")))
            entry_flags = _first_clear_flags(entry)
            for flag_name, value in entry_flags.items():
                clear_flags[key][flag_name] = clear_flags[key][flag_name] or value

    rows: list[dict[str, Any]] = []
    for key, record in sorted(players.items(), key=lambda item: (-item[1].rupture_level, -item[1].build_score, item[0][0])):
        seen_minutes = record.snapshots_seen * interval_minutes
        seen_time_per_rupture = round(seen_minutes / record.rupture_level, 2) if record.rupture_level > 0 else 0.0
        milestone_flags = {
            f"cleared_r{milestone}": record.rupture_level >= milestone for milestone in RUPTURE_MILESTONES
        }

        rows.append(
            {
                "account": record.account,
                "character": record.character,
                "class_name": record.class_name,
                "stance": record.stance,
                "rupture_level": record.rupture_level,
                "build_score": record.build_score,
                "snapshots_seen": record.snapshots_seen,
                "seen_minutes_estimate": seen_minutes,
                "seen_time_per_rupture": seen_time_per_rupture,
                **clear_flags[key],
                **milestone_flags,
            }
        )

    return rows


def run_leaderboard_pipeline(snapshots_dir: str | Path, output_csv: str | Path, interval_minutes: int = 60) -> list[dict[str, Any]]:
    source_dir = Path(snapshots_dir)
    destination = Path(output_csv)

    snapshot_paths = [
        path
        for path in source_dir.glob("*.json")
        if path.name != "latest.json" and not path.name.endswith(".meta.json")
    ]
    rows = build_leaderboard_rows(snapshot_paths, interval_minutes=interval_minutes)

    destination.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "account",
        "character",
        "class_name",
        "stance",
        "rupture_level",
        "build_score",
        "snapshots_seen",
        "seen_minutes_estimate",
        "seen_time_per_rupture",
        *[f"first_clear_{boss}" for boss in TRACKED_BOSSES],
        *[f"cleared_r{milestone}" for milestone in RUPTURE_MILESTONES],
    ]
    with destination.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    return rows
