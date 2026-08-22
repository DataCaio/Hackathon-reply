"""Canonical JSONL framing and run-level validation."""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .diagnostics import normalize_summary, validate_summary
from .events import (
    EventValidationError,
    iter_validated_jsonl,
    validate_event,
)
from .events import (
    load_event_stream as _load_event_stream,
)


class SerializationError(ValueError):
    """A canonical JSON/JSONL serialization or cross-record validation failure."""


@dataclass(frozen=True)
class RunValidationResult:
    event_count: int
    event_types: frozenset[str]
    track_ids: frozenset[str]
    counted_track_ids: frozenset[str]
    summary: dict[str, Any]


def canonical_json(value: Any) -> str:
    """Encode JSON deterministically and reject non-finite numbers."""

    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
            sort_keys=True,
        )
    except (TypeError, ValueError) as exc:
        raise SerializationError(f"value cannot be represented as canonical JSON: {exc}") from exc


def serialize_event(event: Mapping[str, Any]) -> str:
    return canonical_json(validate_event(event))


def serialize_summary(summary: Mapping[str, Any]) -> str:
    return canonical_json(validate_summary(summary))


def write_event_stream(events: Iterable[Mapping[str, Any]], path: str | Path) -> int:
    """Write a validated iterable as one canonical object per UTF-8 line."""

    event_list = list(events)
    from .events import validate_event_stream

    validated = validate_event_stream(event_list)
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", encoding="utf-8", newline="\n") as handle:
        for event in validated:
            handle.write(serialize_event(event))
            handle.write("\n")
    return len(validated)


def load_event_stream(path: str | Path) -> list[dict[str, Any]]:
    return _load_event_stream(path)


def load_summary(path: str | Path) -> dict[str, Any]:
    source = Path(path)
    try:
        value = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SerializationError(f"cannot read summary {source}: {exc}") from exc
    try:
        return validate_summary(value)
    except ValueError as exc:
        raise SerializationError(str(exc)) from exc


def validate_run(events_path: str | Path, summary_path: str | Path) -> RunValidationResult:
    """Validate a canonical stream and its companion summary together."""

    summary = load_summary(summary_path)
    event_count = 0
    event_types: set[str] = set()
    track_ids: set[str] = set()
    counted_track_ids: set[str] = set()
    counted_volume_l = 0.0
    try:
        with Path(events_path).open("r", encoding="utf-8") as handle:
            for event in iter_validated_jsonl(handle):
                event_count += 1
                event_types.add(event["event"])
                track_ids.add(event["track_id"])
                if event["event"] == "BATTERY_COUNTED":
                    counted_track_ids.add(event["track_id"])
                    counted_volume_l += float(event["volume_l"])
    except (OSError, EventValidationError) as exc:
        raise SerializationError(str(exc)) from exc

    summary_ids = set(summary["counted_track_ids"])
    if summary_ids != counted_track_ids:
        raise SerializationError("summary counted_track_ids do not match BATTERY_COUNTED events")
    if summary["lot_count"] != len(counted_track_ids):
        raise SerializationError("summary lot_count does not match BATTERY_COUNTED events")
    if summary["unique_tracks"] != len(track_ids):
        raise SerializationError("summary unique_tracks does not match event track identities")
    if counted_track_ids and summary["lot_volume_l"] is None:
        raise SerializationError("summary lot_volume_l cannot be null when a counted volume exists")
    if summary["lot_volume_l"] is not None and summary["lot_volume_l"] < 0:
        raise SerializationError("summary lot_volume_l must be non-negative")
    if summary["lot_volume_l"] is not None and counted_track_ids:
        if abs(float(summary["lot_volume_l"]) - counted_volume_l) > 1e-6:
            raise SerializationError("summary lot_volume_l does not match frozen counted volumes")

    return RunValidationResult(
        event_count=event_count,
        event_types=frozenset(event_types),
        track_ids=frozenset(track_ids),
        counted_track_ids=frozenset(counted_track_ids),
        summary=normalize_summary(summary),
    )
