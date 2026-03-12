"""Leaderboard-focused ETL transforms for client-ready leaderboard data."""

from __future__ import annotations

import csv
import json
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

RUPTURE_MILESTONES = (18, 30, 36, 75, 100, 125, 200)

SKILL_MOD_SLOTS = ("goblet", "weapon", "horn", "belt", "trinket")


@dataclass(slots=True)
class LeaderboardRecord:
    account: str
    character: str
    class_name: str
    stance: str
    rupture_level: int
    build_score: int
    snapshots_seen: int
    dominant_skill: str
    dominant_skill_count: int
    zone: str
    last_seen_at: str
    dungeons: dict[str, int]
    dungeon_first_seen: dict[str, str]


def _extract_entries(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]

    if isinstance(payload, dict):
        for key in ("entries", "players", "leaderboard", "leaderboards", "data", "scores"):
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


def _extract_dungeons(entry: dict[str, Any]) -> dict[str, int]:
    """Extract dungeon name → clear count from an entry.

    Handles both the ``dungeons`` dict (preferred) and legacy
    ``first_clear_<name>`` boolean flat flags.
    """
    result: dict[str, int] = {}
    normalized = {str(k).lower(): v for k, v in entry.items()}

    # Primary: full dungeons dict with counts
    dungeons_raw = normalized.get("dungeons")
    if isinstance(dungeons_raw, dict):
        for name, count in dungeons_raw.items():
            key = str(name).strip().lower()
            val = _as_int(count)
            if key and val > 0:
                result[key] = val

    # Fallback: legacy first_clear_<name> boolean flags
    for key, value in normalized.items():
        if key.startswith("first_clear_") and value:
            dungeon_name = key[len("first_clear_"):].replace("_", " ")
            if dungeon_name and dungeon_name not in result:
                result[dungeon_name] = 1

    return result


def _split_name(value: Any) -> tuple[str, str]:
    text = _as_str(value, "unknown")
    if "(" in text and text.endswith(")"):
        account, character = text.rsplit("(", 1)
        return _as_str(account, "unknown").rstrip(), _as_str(character[:-1], "unknown")
    return text, "unknown"


def _skill_from_modifier(value: str) -> str:
    if ":" not in value:
        return ""
    return value.split(":", 1)[0].strip()


def _extract_build_profile(entry: dict[str, Any]) -> tuple[str, int, dict[str, str]]:
    build_raw = entry.get("build")
    equipment_mods: dict[str, Any] = {}
    if isinstance(build_raw, dict):
        mods_raw = build_raw.get("equipmentMods")
        if isinstance(mods_raw, dict):
            equipment_mods = mods_raw

    slot_values: dict[str, str] = {
        slot: _as_str(equipment_mods.get(slot), "")
        for slot in SKILL_MOD_SLOTS
    }
    skill_counter: Counter[str] = Counter(
        skill for skill in (_skill_from_modifier(text) for text in slot_values.values()) if skill
    )

    if not skill_counter:
        return "unknown", 0, slot_values

    highest = skill_counter.most_common()
    top_count = highest[0][1]
    top_skills = sorted(skill for skill, count in highest if count == top_count)
    if len(top_skills) > 1:
        return "2+", top_count, slot_values
    return top_skills[0], top_count, slot_values


def build_leaderboard_rows(snapshot_paths: list[Path], interval_minutes: int = 60) -> list[dict[str, Any]]:
    """Aggregate leaderboard snapshots into player-centric rows."""

    players: dict[tuple[str, str], LeaderboardRecord] = {}
    build_profiles: dict[tuple[str, str], dict[str, str]] = {}

    ts_pattern = re.compile(r"leaderboard_(\d{8}T\d{6}Z)")

    for path in sorted(snapshot_paths):
        ts_match = ts_pattern.search(path.stem)
        snapshot_ts = ts_match.group(1) if ts_match else ""
        payload = json.loads(path.read_text(encoding="utf-8"))
        entries = _extract_entries(payload)
        for entry in entries:
            account = _as_str(entry.get("account") or entry.get("account_name") or entry.get("user"), "")
            character = _as_str(entry.get("character") or entry.get("character_name"), "")
            if not account and not character:
                account, character = _split_name(entry.get("name"))
            account = account or "unknown"
            character = character or "unknown"
            key = (account, character)

            dominant_skill, dominant_skill_count, slot_values = _extract_build_profile(entry)

            entry_zone = _as_str(entry.get("zone") or entry.get("current_zone"), "")
            entry_dungeons = _extract_dungeons(entry)

            record = players.get(key)
            if record is None:
                record = LeaderboardRecord(
                    account=account,
                    character=character,
                    class_name=_as_str(entry.get("class") or entry.get("class_name"), "unknown"),
                    stance=_as_str(entry.get("stance") or (entry.get("build") or {}).get("stance"), "unknown"),
                    rupture_level=_as_int(
                        entry.get("rupture") or entry.get("rupture_level") or entry.get("raptureLevel")
                    ),
                    build_score=_as_int(entry.get("score") or entry.get("build_score") or entry.get("level")),
                    snapshots_seen=0,
                    dominant_skill=dominant_skill,
                    dominant_skill_count=dominant_skill_count,
                    zone=entry_zone,
                    last_seen_at=snapshot_ts,
                    dungeons={},
                    dungeon_first_seen={},
                )
                players[key] = record
                build_profiles[key] = slot_values

            record.snapshots_seen += 1
            record.rupture_level = max(
                record.rupture_level,
                _as_int(entry.get("rupture") or entry.get("rupture_level") or entry.get("raptureLevel")),
            )
            record.build_score = max(record.build_score, _as_int(entry.get("score") or entry.get("build_score") or entry.get("level")))
            if record.class_name == "unknown":
                record.class_name = _as_str(entry.get("class") or entry.get("class_name"), "unknown")
            if record.stance == "unknown":
                record.stance = _as_str(entry.get("stance") or (entry.get("build") or {}).get("stance"), "unknown")

            if entry_zone:
                record.zone = entry_zone
            if snapshot_ts:
                record.last_seen_at = snapshot_ts

            if dominant_skill_count > record.dominant_skill_count:
                record.dominant_skill = dominant_skill
                record.dominant_skill_count = dominant_skill_count
                build_profiles[key] = slot_values

            # Merge dungeon data: max count, earliest first-seen timestamp
            for dname, dcount in entry_dungeons.items():
                record.dungeons[dname] = max(record.dungeons.get(dname, 0), dcount)
                if dname not in record.dungeon_first_seen and snapshot_ts:
                    record.dungeon_first_seen[dname] = snapshot_ts

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
                "skill_name": record.dominant_skill,
                "skill_modifier_count": record.dominant_skill_count,
                "skill_mods": build_profiles.get(key, {}),
                "zone": record.zone,
                "last_seen_at": record.last_seen_at,
                "dungeons": dict(sorted(
                    record.dungeons.items(),
                    key=lambda item: record.dungeon_first_seen.get(item[0], ""),
                )),
                "dungeon_first_seen": dict(sorted(
                    record.dungeon_first_seen.items(),
                    key=lambda item: item[1],
                )),
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
        "skill_name",
        "skill_modifier_count",
        "skill_mods",
        "zone",
        "last_seen_at",
        "dungeons",
        "dungeon_first_seen",
        *[f"cleared_r{milestone}" for milestone in RUPTURE_MILESTONES],
    ]
    with destination.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    return rows


def reconcile_variant_transitions(
    variant_rows: dict[str, list[dict[str, Any]]],
) -> dict[str, list[dict[str, Any]]]:
    """Detect players who appear across variants and annotate with history.

    When a player appears in both solo and fellowship, they are kept only in
    the fellowship variant (the most recent / "promoted" board) and their
    variant_history records both appearances.  The same applies for
    hardcore_solo → hardcore_fellowship.
    """
    # Build a lookup: (account, character) → set of variant keys
    player_variants: dict[tuple[str, str], set[str]] = {}
    for variant_key, rows in variant_rows.items():
        for row in rows:
            pk = (row["account"], row["character"])
            player_variants.setdefault(pk, set()).add(variant_key)

    # Promotion pairs: solo → fellowship, hardcore_solo → hardcore_fellowship
    promotions = [("solo", "fellowship"), ("hardcore_solo", "hardcore_fellowship")]

    for solo_key, fellowship_key in promotions:
        solo_rows = variant_rows.get(solo_key, [])
        variant_rows[solo_key] = [
            row for row in solo_rows
            if fellowship_key not in player_variants.get((row["account"], row["character"]), set())
        ]

    # Annotate all remaining rows with their full variant history
    for variant_key, rows in variant_rows.items():
        for row in rows:
            pk = (row["account"], row["character"])
            history = sorted(player_variants.get(pk, {variant_key}))
            row["variant_history"] = history

    return variant_rows
