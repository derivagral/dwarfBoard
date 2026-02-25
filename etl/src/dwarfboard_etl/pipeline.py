"""Core ETL steps for dwarfBoard analytics."""

from __future__ import annotations

import csv
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


@dataclass(slots=True)
class EventRecord:
    user_id: str
    timestamp: str
    event_type: str


def _read_events(events_csv: Path) -> list[EventRecord]:
    rows: list[EventRecord] = []
    with events_csv.open("r", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        required = {"user_id", "timestamp", "event_type"}
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"Missing required columns: {sorted(missing)}")

        for row in reader:
            rows.append(
                EventRecord(
                    user_id=(row.get("user_id") or "").strip(),
                    timestamp=(row.get("timestamp") or "").strip(),
                    event_type=(row.get("event_type") or "").strip() or "unknown",
                )
            )
    return rows


def _to_utc_date(timestamp_text: str) -> str:
    normalized = timestamp_text.strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"

    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).date().isoformat()


def transform_events(events: Iterable[EventRecord]) -> list[dict[str, str | int]]:
    aggregates: dict[tuple[str, str], set[str]] = defaultdict(set)
    counts: dict[tuple[str, str], int] = defaultdict(int)

    for event in events:
        event_date = _to_utc_date(event.timestamp)
        key = (event_date, event.event_type)
        counts[key] += 1
        if event.user_id:
            aggregates[key].add(event.user_id)

    output: list[dict[str, str | int]] = []
    for key in sorted(counts):
        date_value, event_type = key
        output.append(
            {
                "event_date": date_value,
                "event_type": event_type,
                "event_count": counts[key],
                "unique_users": len(aggregates[key]),
            }
        )
    return output


def _write_summary(rows: list[dict[str, str | int]], output_csv: Path) -> None:
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    with output_csv.open("w", newline="", encoding="utf-8") as handle:
        fieldnames = ["event_date", "event_type", "event_count", "unique_users"]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def run_pipeline(events_csv: str | Path, output_csv: str | Path) -> list[dict[str, str | int]]:
    """Run the extract-transform-load flow and return transformed rows."""
    source = Path(events_csv)
    destination = Path(output_csv)
    records = _read_events(source)
    transformed = transform_events(records)
    _write_summary(transformed, destination)
    return transformed
