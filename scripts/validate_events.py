#!/usr/bin/env python3
"""Validate a canonical Story 3 JSONL stream and its run summary."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from hackathon_reply.contracts.events import EventContractError, validate_event_dict
from hackathon_reply.contracts.serialization import SerializationError, validate_run


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path, help="canonical UTF-8 JSONL event stream")
    parser.add_argument("--summary", required=True, type=Path, help="versioned run-summary JSON")
    return parser


def validate(path: str | Path) -> dict[str, object]:
    """Validate a US1 flattened JSONL stream and its completion marker.

    The Story 3 CLI below validates the canonical event-stream-plus-summary
    format.  US1's replay sink writes an envelope flattened into each JSONL
    record, so this small API keeps that earlier integration contract usable.
    """

    event_path = Path(path)
    completion_path = Path(str(event_path) + ".complete")
    if not completion_path.exists():
        raise EventContractError("event stream is incomplete; completion marker is missing")
    try:
        marker = json.loads(completion_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise EventContractError("event stream is incomplete; completion marker is invalid") from exc
    if not isinstance(marker, dict) or not isinstance(marker.get("run_id"), str):
        raise EventContractError("event stream is incomplete; completion marker is invalid")
    if not isinstance(marker.get("event_count"), int) or isinstance(marker["event_count"], bool):
        raise EventContractError("event stream is incomplete; completion count is invalid")

    seen_ids: set[str] = set()
    expected_sequence = 0
    previous_timestamp = -1
    event_count = 0
    run_id = marker["run_id"]
    try:
        handle = event_path.open("r", encoding="utf-8")
    except OSError as exc:
        raise EventContractError("event stream is incomplete; event file is unavailable") from exc
    with handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                raise EventContractError(f"blank event line at {line_number}")
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise EventContractError(f"invalid JSON at line {line_number}") from exc
            if not isinstance(record, dict):
                raise EventContractError(f"event at line {line_number} must be an object")
            validate_event_dict(record)
            if record["run_id"] != run_id:
                raise EventContractError(f"event run_id mismatch at line {line_number}")
            if record["sequence"] != expected_sequence:
                raise EventContractError(f"event sequence is not contiguous at line {line_number}")
            if record["event_id"] in seen_ids:
                raise EventContractError(f"duplicate event_id at line {line_number}")
            if record["timestamp_ms"] < previous_timestamp:
                raise EventContractError(f"event timestamp regressed at line {line_number}")
            seen_ids.add(record["event_id"])
            expected_sequence += 1
            previous_timestamp = record["timestamp_ms"]
            event_count += 1
    if marker["event_count"] != event_count:
        raise EventContractError("completion marker event_count does not match the event stream")
    return {"status": "valid", "run_id": run_id, "event_count": event_count}


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = validate_run(args.input, args.summary)
    except (OSError, SerializationError, ValueError) as exc:
        print(f"validation failed: {exc}", file=sys.stderr)
        return 1
    print(
        f"validated {result.event_count} events; "
        f"types={','.join(sorted(result.event_types))}; "
        f"counted={len(result.counted_track_ids)}; "
        f"run_status={result.summary['run_status']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
