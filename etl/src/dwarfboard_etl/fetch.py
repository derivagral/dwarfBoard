"""Fetch utilities for leaderboard snapshots."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


@dataclass(slots=True)
class FetchResult:
    url: str
    status_code: int
    fetched_at: str
    body_path: Path
    metadata_path: Path


def _safe_suffix(content_type: str | None) -> str:
    if not content_type:
        return ".bin"
    lowered = content_type.lower()
    if "json" in lowered:
        return ".json"
    if "csv" in lowered or "text/plain" in lowered:
        return ".csv"
    if "html" in lowered:
        return ".html"
    return ".bin"


def fetch_snapshot(url: str, output_dir: str | Path) -> FetchResult:
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)

    request = Request(url, headers={"User-Agent": "dwarfboard-etl-fetch/0.1"})
    fetched_at = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    try:
        with urlopen(request, timeout=60) as response:  # noqa: S310 - URL is user configured
            body = response.read()
            status_raw = getattr(response, "status", None)
            status = status_raw if isinstance(status_raw, int) else 200
            content_type = response.headers.get("Content-Type")
            etag = response.headers.get("ETag")
            last_modified = response.headers.get("Last-Modified")
    except HTTPError as exc:  # pragma: no cover - exercised in CI/integration
        raise RuntimeError(f"HTTP error while fetching {url}: {exc.code}") from exc
    except URLError as exc:  # pragma: no cover - exercised in CI/integration
        raise RuntimeError(f"Network error while fetching {url}: {exc.reason}") from exc

    digest = hashlib.sha256(body).hexdigest()
    suffix = _safe_suffix(content_type)
    body_path = destination / f"leaderboard_{fetched_at}_{digest[:12]}{suffix}"
    body_path.write_bytes(body)

    metadata = {
        "url": url,
        "status_code": status,
        "fetched_at": fetched_at,
        "sha256": digest,
        "content_type": content_type,
        "etag": etag,
        "last_modified": last_modified,
        "body_file": body_path.name,
        "body_size": len(body),
    }
    metadata_path = destination / f"leaderboard_{fetched_at}_{digest[:12]}.meta.json"
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    latest_pointer = destination / "latest.json"
    latest_pointer.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    return FetchResult(
        url=url,
        status_code=status,
        fetched_at=fetched_at,
        body_path=body_path,
        metadata_path=metadata_path,
    )
