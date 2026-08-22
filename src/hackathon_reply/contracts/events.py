"""Strict validation for the versioned battery event contract.

This module is deliberately transport- and vendor-neutral.  It validates plain
mapping values so producers and downstream consumers do not need to share any
vision, tracking, geometry, or PLC implementation objects.
"""

from __future__ import annotations

import json
import math
import re
from collections.abc import Iterable, Iterator, Mapping
from pathlib import Path
from typing import Any, TextIO


SCHEMA_VERSION = 1
EVENT_TYPES = frozenset({"TRACK_UPDATE", "TRACK_OCCLUDED", "BATTERY_COUNTED"})
TRACK_STATES = frozenset(
    {"DETECTED", "TRACKING", "OCCLUDED", "REACQUIRED", "COUNTED", "LOST"}
)
RESOLUTIONS = frozenset({"720p", "1080p"})

COMMON_EVENT_KEYS = frozenset(
    {"event", "schema_version", "timestamp_ms", "video_id", "resolution", "track_id"}
)
TRACK_UPDATE_KEYS = COMMON_EVENT_KEYS | frozenset(
    {
        "state",
        "bbox",
        "mask_confidence",
        "visibility",
        "length_mm",
        "width_mm",
        "geometry_uncertainty_mm",
        "volume_l",
        "volume_ci95_l",
        "volume_confidence",
        "counted",
    }
)
TRACK_OCCLUDED_KEYS = COMMON_EVENT_KEYS | frozenset(
    {"state", "predicted_position", "last_volume_l", "volume_confidence"}
)
BATTERY_COUNTED_KEYS = COMMON_EVENT_KEYS | frozenset(
    {"state", "volume_l", "volume_ci95_l", "volume_confidence", "lot_count", "lot_volume_l"}
)
EVENT_KEYS = {
    "TRACK_UPDATE": TRACK_UPDATE_KEYS,
    "TRACK_OCCLUDED": TRACK_OCCLUDED_KEYS,
    "BATTERY_COUNTED": BATTERY_COUNTED_KEYS,
}

_TRACK_ID = re.compile(r"^battery-[A-Za-z0-9]{4,}$")


class EventValidationError(ValueError):
    """A structured event or JSONL stream validation failure."""

    def __init__(
        self,
        message: str,
        *,
        code: str = "invalid_event",
        line_number: int | None = None,
        event_type: str | None = None,
        track_id: str | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.line_number = line_number
        self.event_type = event_type
        self.track_id = track_id


def _error(
    message: str,
    *,
    code: str,
    line_number: int | None = None,
    event_type: str | None = None,
    track_id: str | None = None,
) -> EventValidationError:
    return EventValidationError(
        message,
        code=code,
        line_number=line_number,
        event_type=event_type,
        track_id=track_id,
    )


def _is_finite_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value))


def _require_string(
    value: Any,
    field: str,
    *,
    line_number: int | None,
    event_type: str | None,
    track_id: str | None,
) -> str:
    if not isinstance(value, str) or not value.strip():
        raise _error(
            f"{field} must be a non-empty string",
            code=f"invalid_{field}",
            line_number=line_number,
            event_type=event_type,
            track_id=track_id,
        )
    return value


def _validate_probability(
    value: Any,
    field: str,
    *,
    nullable: bool,
    line_number: int | None,
    event_type: str | None,
    track_id: str | None,
) -> None:
    if value is None and nullable:
        return
    if not _is_finite_number(value) or not 0.0 <= float(value) <= 1.0:
        raise _error(
            f"{field} must be finite and in [0, 1]",
            code=f"invalid_{field}",
            line_number=line_number,
            event_type=event_type,
            track_id=track_id,
        )


def _validate_nonnegative(
    value: Any,
    field: str,
    *,
    nullable: bool,
    line_number: int | None,
    event_type: str | None,
    track_id: str | None,
    positive: bool = False,
) -> None:
    if value is None and nullable:
        return
    if not _is_finite_number(value):
        raise _error(
            f"{field} must be a finite number",
            code=f"invalid_{field}",
            line_number=line_number,
            event_type=event_type,
            track_id=track_id,
        )
    threshold = 0.0 if positive else -0.0
    if float(value) <= threshold if positive else float(value) < threshold:
        qualifier = "positive" if positive else "non-negative"
        raise _error(
            f"{field} must be {qualifier}",
            code=f"invalid_{field}",
            line_number=line_number,
            event_type=event_type,
            track_id=track_id,
        )


def _validate_interval(
    value: Any,
    field: str,
    *,
    nullable: bool,
    line_number: int | None,
    event_type: str | None,
    track_id: str | None,
    contains: float | None = None,
) -> None:
    if value is None and nullable:
        return
    if not isinstance(value, list) or len(value) != 2:
        raise _error(
            f"{field} must contain two finite values",
            code=f"invalid_{field}",
            line_number=line_number,
            event_type=event_type,
            track_id=track_id,
        )
    low, high = value
    if not _is_finite_number(low) or not _is_finite_number(high) or float(low) > float(high):
        raise _error(
            f"{field} must be an ordered finite interval",
            code=f"invalid_{field}",
            line_number=line_number,
            event_type=event_type,
            track_id=track_id,
        )
    if contains is not None and not float(low) <= contains <= float(high):
        raise _error(
            f"{field} must contain volume_l",
            code=f"invalid_{field}",
            line_number=line_number,
            event_type=event_type,
            track_id=track_id,
        )


def _validate_point(
    value: Any,
    field: str,
    length: int,
    *,
    nullable: bool,
    line_number: int | None,
    event_type: str | None,
    track_id: str | None,
) -> None:
    if value is None and nullable:
        return
    if not isinstance(value, list) or len(value) != length or not all(_is_finite_number(item) for item in value):
        raise _error(
            f"{field} must contain {length} finite coordinates",
            code=f"invalid_{field}",
            line_number=line_number,
            event_type=event_type,
            track_id=track_id,
        )


def validate_event(
    event: Mapping[str, Any],
    *,
    line_number: int | None = None,
) -> dict[str, Any]:
    """Validate one event and return a plain dictionary copy.

    Stream-level ordering and exactly-once invariants are handled by
    :func:`validate_event_stream` and :func:`iter_validated_jsonl`.
    """

    if not isinstance(event, Mapping):
        raise _error("event must be a JSON object", code="invalid_object", line_number=line_number)
    raw_event_type = event.get("event")
    event_type = raw_event_type if isinstance(raw_event_type, str) else None
    if event_type not in EVENT_TYPES:
        raise _error(
            "event must be one of TRACK_UPDATE, TRACK_OCCLUDED, BATTERY_COUNTED",
            code="unknown_event",
            line_number=line_number,
            event_type=event_type,
        )
    expected_keys = EVENT_KEYS[event_type]
    actual_keys = set(event)
    missing = expected_keys - actual_keys
    extra = actual_keys - expected_keys
    if missing:
        raise _error(
            f"missing keys: {', '.join(sorted(missing))}",
            code="missing_keys",
            line_number=line_number,
            event_type=event_type,
        )
    if extra:
        raise _error(
            f"undeclared keys: {', '.join(sorted(extra))}",
            code="undeclared_keys",
            line_number=line_number,
            event_type=event_type,
            track_id=event.get("track_id") if isinstance(event.get("track_id"), str) else None,
        )

    schema_version = event["schema_version"]
    if not isinstance(schema_version, int) or isinstance(schema_version, bool) or schema_version != SCHEMA_VERSION:
        raise _error(
            f"schema_version must be {SCHEMA_VERSION}",
            code="schema_version",
            line_number=line_number,
            event_type=event_type,
        )

    timestamp_ms = event["timestamp_ms"]
    if not isinstance(timestamp_ms, int) or isinstance(timestamp_ms, bool) or timestamp_ms < 0:
        raise _error(
            "timestamp_ms must be a non-negative integer",
            code="invalid_timestamp",
            line_number=line_number,
            event_type=event_type,
        )

    video_id = _require_string(
        event["video_id"],
        "video_id",
        line_number=line_number,
        event_type=event_type,
        track_id=None,
    )
    if event["resolution"] not in RESOLUTIONS:
        raise _error(
            "resolution must be 720p or 1080p",
            code="invalid_resolution",
            line_number=line_number,
            event_type=event_type,
        )
    track_id = _require_string(
        event["track_id"],
        "track_id",
        line_number=line_number,
        event_type=event_type,
        track_id=None,
    )
    if not _TRACK_ID.fullmatch(track_id):
        raise _error(
            "track_id must match battery-xxxx",
            code="invalid_track_id",
            line_number=line_number,
            event_type=event_type,
            track_id=track_id,
        )

    state = event["state"]
    if state not in TRACK_STATES:
        raise _error(
            "state must be a published track state",
            code="invalid_state",
            line_number=line_number,
            event_type=event_type,
            track_id=track_id,
        )

    if event_type == "TRACK_UPDATE":
        _validate_point(
            event["bbox"],
            "bbox",
            4,
            nullable=True,
            line_number=line_number,
            event_type=event_type,
            track_id=track_id,
        )
        bbox = event["bbox"]
        if bbox is not None and (bbox[0] > bbox[2] or bbox[1] > bbox[3]):
            raise _error(
                "bbox coordinates must be ordered",
                code="invalid_bbox",
                line_number=line_number,
                event_type=event_type,
                track_id=track_id,
            )
        _validate_probability(
            event["mask_confidence"],
            "mask_confidence",
            nullable=True,
            line_number=line_number,
            event_type=event_type,
            track_id=track_id,
        )
        _validate_probability(
            event["visibility"],
            "visibility",
            nullable=False,
            line_number=line_number,
            event_type=event_type,
            track_id=track_id,
        )
        _validate_nonnegative(
            event["length_mm"],
            "length_mm",
            nullable=True,
            line_number=line_number,
            event_type=event_type,
            track_id=track_id,
        )
        _validate_nonnegative(
            event["width_mm"],
            "width_mm",
            nullable=True,
            line_number=line_number,
            event_type=event_type,
            track_id=track_id,
        )
        _validate_nonnegative(
            event["geometry_uncertainty_mm"],
            "geometry_uncertainty_mm",
            nullable=True,
            line_number=line_number,
            event_type=event_type,
            track_id=track_id,
        )
        _validate_nonnegative(
            event["volume_l"],
            "volume_l",
            nullable=True,
            line_number=line_number,
            event_type=event_type,
            track_id=track_id,
        )
        _validate_interval(
            event["volume_ci95_l"],
            "volume_ci95_l",
            nullable=True,
            line_number=line_number,
            event_type=event_type,
            track_id=track_id,
            contains=float(event["volume_l"]) if event["volume_l"] is not None else None,
        )
        _validate_probability(
            event["volume_confidence"],
            "volume_confidence",
            nullable=False,
            line_number=line_number,
            event_type=event_type,
            track_id=track_id,
        )
        if not isinstance(event["counted"], bool):
            raise _error(
                "counted must be boolean",
                code="invalid_counted",
                line_number=line_number,
                event_type=event_type,
                track_id=track_id,
            )
    elif event_type == "TRACK_OCCLUDED":
        if state != "OCCLUDED":
            raise _error(
                "TRACK_OCCLUDED state must be OCCLUDED",
                code="invalid_state",
                line_number=line_number,
                event_type=event_type,
                track_id=track_id,
            )
        _validate_point(
            event["predicted_position"],
            "predicted_position",
            2,
            nullable=True,
            line_number=line_number,
            event_type=event_type,
            track_id=track_id,
        )
        _validate_nonnegative(
            event["last_volume_l"],
            "last_volume_l",
            nullable=True,
            line_number=line_number,
            event_type=event_type,
            track_id=track_id,
        )
        _validate_probability(
            event["volume_confidence"],
            "volume_confidence",
            nullable=False,
            line_number=line_number,
            event_type=event_type,
            track_id=track_id,
        )
    else:
        if state != "COUNTED":
            raise _error(
                "BATTERY_COUNTED state must be COUNTED",
                code="invalid_state",
                line_number=line_number,
                event_type=event_type,
                track_id=track_id,
            )
        volume_l = event["volume_l"]
        _validate_nonnegative(
            volume_l,
            "volume_l",
            nullable=False,
            line_number=line_number,
            event_type=event_type,
            track_id=track_id,
            positive=True,
        )
        _validate_interval(
            event["volume_ci95_l"],
            "volume_ci95_l",
            nullable=False,
            line_number=line_number,
            event_type=event_type,
            track_id=track_id,
            contains=float(volume_l),
        )
        _validate_probability(
            event["volume_confidence"],
            "volume_confidence",
            nullable=False,
            line_number=line_number,
            event_type=event_type,
            track_id=track_id,
        )
        lot_count = event["lot_count"]
        if not isinstance(lot_count, int) or isinstance(lot_count, bool) or lot_count < 1:
            raise _error(
                "lot_count must be a positive integer",
                code="invalid_lot_count",
                line_number=line_number,
                event_type=event_type,
                track_id=track_id,
            )
        _validate_nonnegative(
            event["lot_volume_l"],
            "lot_volume_l",
            nullable=False,
            line_number=line_number,
            event_type=event_type,
            track_id=track_id,
            positive=True,
        )

    return dict(event)


class _EventStreamValidator:
    def __init__(self) -> None:
        self.previous_timestamp: int | None = None
        self.seen_counted: set[str] = set()
        self.last_update_timestamp: dict[str, int] = {}
        self.states: dict[str, str] = {}
        self.terminal_tracks: set[str] = set()
        self.lot_volume = 0.0

    def accept(self, event: Mapping[str, Any], *, line_number: int) -> dict[str, Any]:
        validated = validate_event(event, line_number=line_number)
        event_type = validated["event"]
        track_id = validated["track_id"]
        timestamp = validated["timestamp_ms"]

        if self.previous_timestamp is not None and timestamp < self.previous_timestamp:
            raise _error(
                "timestamp_ms regressed in canonical line order",
                code="timestamp_regression",
                line_number=line_number,
                event_type=event_type,
                track_id=track_id,
            )
        self.previous_timestamp = timestamp

        if track_id in self.terminal_tracks:
            raise _error(
                "event appears after terminal LOST state",
                code="event_after_lost",
                line_number=line_number,
                event_type=event_type,
                track_id=track_id,
            )
        previous_state = self.states.get(track_id)
        if event_type == "TRACK_OCCLUDED" and previous_state == "OCCLUDED":
            raise _error(
                "TRACK_OCCLUDED must be transition-only",
                code="duplicate_occlusion_transition",
                line_number=line_number,
                event_type=event_type,
                track_id=track_id,
            )
        if event_type == "TRACK_UPDATE":
            if self.last_update_timestamp.get(track_id) == timestamp:
                raise _error(
                    "more than one TRACK_UPDATE for a track at one processed timestamp",
                    code="duplicate_frame_update",
                    line_number=line_number,
                    event_type=event_type,
                    track_id=track_id,
                )
            self.last_update_timestamp[track_id] = timestamp
            if previous_state == "COUNTED" and not validated["counted"]:
                raise _error(
                    "counted track updates must retain counted=true",
                    code="count_state_regression",
                    line_number=line_number,
                    event_type=event_type,
                    track_id=track_id,
                )
            if validated["state"] == "COUNTED" and not validated["counted"]:
                raise _error(
                    "COUNTED track updates must have counted=true",
                    code="count_state_mismatch",
                    line_number=line_number,
                    event_type=event_type,
                    track_id=track_id,
                )
        elif event_type == "BATTERY_COUNTED":
            if track_id in self.seen_counted:
                raise _error(
                    "duplicate BATTERY_COUNTED identity",
                    code="duplicate_count",
                    line_number=line_number,
                    event_type=event_type,
                    track_id=track_id,
                )
            self.seen_counted.add(track_id)
            self.lot_volume += float(validated["volume_l"])
            expected_count = len(self.seen_counted)
            if validated["lot_count"] != expected_count:
                raise _error(
                    "lot_count does not match counted identities",
                    code="lot_count_mismatch",
                    line_number=line_number,
                    event_type=event_type,
                    track_id=track_id,
                )
            if not math.isclose(float(validated["lot_volume_l"]), self.lot_volume, rel_tol=1e-6, abs_tol=1e-6):
                raise _error(
                    "lot_volume_l does not match frozen counted volumes",
                    code="lot_volume_mismatch",
                    line_number=line_number,
                    event_type=event_type,
                    track_id=track_id,
                )

        self.states[track_id] = validated["state"]
        if validated["state"] == "LOST":
            self.terminal_tracks.add(track_id)
        return validated


def validate_event_stream(events: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Validate an iterable of decoded event objects in canonical order."""

    validator = _EventStreamValidator()
    return [validator.accept(event, line_number=index) for index, event in enumerate(events, start=1)]


def iter_validated_jsonl(source: TextIO) -> Iterator[dict[str, Any]]:
    """Yield validated events from a JSONL text stream without buffering it."""

    validator = _EventStreamValidator()
    for line_number, raw_line in enumerate(source, start=1):
        if not raw_line.strip():
            raise _error("blank JSONL lines are not allowed", code="blank_line", line_number=line_number)
        try:
            decoded = json.loads(raw_line)
        except json.JSONDecodeError as exc:
            raise _error(
                f"malformed JSON at line {line_number}: {exc.msg}",
                code="malformed_json",
                line_number=line_number,
            ) from exc
        yield validator.accept(decoded, line_number=line_number)


def load_event_stream(path: str | Path) -> list[dict[str, Any]]:
    """Load and validate a JSONL stream for small consumer fixtures."""

    with Path(path).open("r", encoding="utf-8") as handle:
        return list(iter_validated_jsonl(handle))
