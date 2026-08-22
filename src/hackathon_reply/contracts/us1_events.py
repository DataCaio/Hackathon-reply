"""Strict JSON event contracts for the US1 external boundary.

US3 owns the canonical event-stream validator in :mod:`contracts.events`.
US1 predates that stream format and exposes a replay-stable envelope with the
same three event names.  Keeping this compatibility layer separate allows
both public contracts to coexist while the pipeline is migrated incrementally.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from math import isfinite
from typing import Any, Mapping, Sequence

EVENT_TYPES = {"TRACK_UPDATE", "TRACK_OCCLUDED", "BATTERY_COUNTED"}
RESOLUTIONS = {"720p", "1080p"}
TRACK_STATES = {"DETECTED", "TRACKING", "OCCLUDED", "REACQUIRED", "COUNTED", "LOST"}
RESERVED_PAYLOAD_KEYS = {
    "event",
    "run_id",
    "event_id",
    "sequence",
    "schema_version",
    "video_id",
    "resolution",
    "timestamp_ms",
}


class EventContractError(ValueError):
    """Raised when an event cannot be represented by the US1 contract."""


def _ensure_finite(value: Any, name: str) -> Any:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)) and not isfinite(float(value)):
        raise EventContractError(f"{name} must be finite")
    if isinstance(value, list):
        return [_ensure_finite(item, name) for item in value]
    if isinstance(value, tuple):
        return [_ensure_finite(item, name) for item in value]
    if isinstance(value, dict):
        return {key: _ensure_finite(item, f"{name}.{key}") for key, item in value.items()}
    return value


def _finite_number(value: Any, name: str, *, positive: bool = False) -> None:
    if not isinstance(value, (int, float)) or isinstance(value, bool) or not isfinite(float(value)):
        raise EventContractError(f"{name} must be finite numeric")
    if positive and float(value) <= 0:
        raise EventContractError(f"{name} must be positive")


def _optional_confidence(value: Any, name: str) -> None:
    if value is not None:
        _finite_number(value, name)
        if not 0 <= float(value) <= 1:
            raise EventContractError(f"{name} must be between zero and one")


def _interval(value: Any, name: str) -> None:
    if value is None:
        return
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        raise EventContractError(f"{name} must be null or an ordered two-value interval")
    _finite_number(value[0], f"{name}.lower", positive=True)
    _finite_number(value[1], f"{name}.upper", positive=True)
    if value[1] < value[0]:
        raise EventContractError(f"{name} must be ordered")


def _track_id(value: Any) -> None:
    if not isinstance(value, str) or not value.startswith("battery-"):
        raise EventContractError("track_id must be a non-empty operational identity")


def _validate_payload(event: str, payload: Mapping[str, Any]) -> None:
    if "PLC_STATE" in payload:
        raise EventContractError("Model Core events cannot contain PLC_STATE")
    if event == "TRACK_UPDATE":
        required = {
            "track_id",
            "state",
            "bbox",
            "visibility",
            "mask_confidence",
            "length_mm",
            "width_mm",
            "volume_l",
            "uncertainty_interval_l",
            "volume_confidence",
            "counted",
            "catalog_candidates",
        }
        missing = required - set(payload)
        if missing:
            raise EventContractError(f"TRACK_UPDATE is missing fields: {sorted(missing)}")
        _track_id(payload["track_id"])
        if payload["state"] not in TRACK_STATES:
            raise EventContractError("TRACK_UPDATE state is invalid")
        bbox = payload["bbox"]
        if not isinstance(bbox, (list, tuple)) or len(bbox) != 4:
            raise EventContractError("TRACK_UPDATE bbox must contain four coordinates")
        for index, coordinate in enumerate(bbox):
            _finite_number(coordinate, f"bbox[{index}]")
        if bbox[2] <= bbox[0] or bbox[3] <= bbox[1]:
            raise EventContractError("TRACK_UPDATE bbox must have positive dimensions")
        _finite_number(payload["visibility"], "visibility")
        if not 0 <= float(payload["visibility"]) <= 1:
            raise EventContractError("visibility must be between zero and one")
        _optional_confidence(payload["mask_confidence"], "mask_confidence")
        lengths = (payload["length_mm"], payload["width_mm"])
        if (lengths[0] is None) != (lengths[1] is None):
            raise EventContractError("length_mm and width_mm must be null together")
        if lengths[0] is not None:
            _finite_number(lengths[0], "length_mm", positive=True)
            _finite_number(lengths[1], "width_mm", positive=True)
        volume = payload["volume_l"]
        interval = payload["uncertainty_interval_l"]
        if volume is None:
            if interval is not None or payload["volume_confidence"] != 0:
                raise EventContractError("unavailable volume must use null interval and zero confidence")
        else:
            _finite_number(volume, "volume_l", positive=True)
            _interval(interval, "uncertainty_interval_l")
            if interval is None:
                raise EventContractError("available volume requires an uncertainty interval")
        _optional_confidence(payload["volume_confidence"], "volume_confidence")
        if not isinstance(payload["counted"], bool):
            raise EventContractError("counted must be boolean")
        if not isinstance(payload["catalog_candidates"], list):
            raise EventContractError("catalog_candidates must be a list")
    elif event == "TRACK_OCCLUDED":
        required = {"track_id", "predicted_position", "last_volume_l", "volume_confidence"}
        missing = required - set(payload)
        if missing:
            raise EventContractError(f"TRACK_OCCLUDED is missing fields: {sorted(missing)}")
        _track_id(payload["track_id"])
        position = payload["predicted_position"]
        if position is not None:
            if not isinstance(position, (list, tuple)) or len(position) != 2:
                raise EventContractError("predicted_position must be null or a two-value point")
            for index, coordinate in enumerate(position):
                _finite_number(coordinate, f"predicted_position[{index}]")
        if payload["last_volume_l"] is not None:
            _finite_number(payload["last_volume_l"], "last_volume_l", positive=True)
        _optional_confidence(payload["volume_confidence"], "volume_confidence")
    elif event == "BATTERY_COUNTED":
        required = {
            "track_id",
            "volume_l",
            "uncertainty_interval_l",
            "volume_confidence",
            "lot_count",
            "lot_volume_l",
            "catalog_candidates",
        }
        missing = required - set(payload)
        if missing:
            raise EventContractError(f"BATTERY_COUNTED is missing fields: {sorted(missing)}")
        _track_id(payload["track_id"])
        _finite_number(payload["volume_l"], "volume_l", positive=True)
        _interval(payload["uncertainty_interval_l"], "uncertainty_interval_l")
        _optional_confidence(payload["volume_confidence"], "volume_confidence")
        if (
            not isinstance(payload["lot_count"], int)
            or isinstance(payload["lot_count"], bool)
            or payload["lot_count"] <= 0
        ):
            raise EventContractError("lot_count must be a positive integer")
        _finite_number(payload["lot_volume_l"], "lot_volume_l", positive=True)
        if not isinstance(payload["catalog_candidates"], list):
            raise EventContractError("catalog_candidates must be a list")
    else:
        raise EventContractError(f"unsupported event: {event}")


@dataclass(frozen=True, slots=True)
class EventEnvelope:
    event: str
    run_id: str
    event_id: str
    sequence: int
    schema_version: str
    video_id: str
    resolution: str
    timestamp_ms: int
    payload: Mapping[str, Any]

    def __post_init__(self) -> None:
        if self.event not in EVENT_TYPES:
            raise EventContractError(f"unsupported event: {self.event}")
        if not self.run_id or not self.event_id or not self.schema_version or not self.video_id:
            raise EventContractError("event identity and schema fields are required")
        if self.sequence < 0 or self.timestamp_ms < 0:
            raise EventContractError("sequence and timestamp_ms must be non-negative")
        if self.resolution not in RESOLUTIONS:
            raise EventContractError(f"unsupported resolution: {self.resolution}")
        if any(key in RESERVED_PAYLOAD_KEYS for key in self.payload):
            raise EventContractError("payload contains an envelope field")
        if "PLC_STATE" in self.payload:
            raise EventContractError("Model Core events cannot contain PLC_STATE")
        _ensure_finite(dict(self.payload), "payload")

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "event": self.event,
            "run_id": self.run_id,
            "event_id": self.event_id,
            "sequence": self.sequence,
            "schema_version": self.schema_version,
            "video_id": self.video_id,
            "resolution": self.resolution,
            "timestamp_ms": self.timestamp_ms,
        }
        result.update(_ensure_finite(dict(self.payload), "payload"))
        return result

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, sort_keys=True, allow_nan=False)


def _envelope(
    *,
    event: str,
    run_id: str,
    event_id: str | None,
    sequence: int,
    schema_version: str,
    video_id: str,
    resolution: str,
    timestamp_ms: int,
    payload: Mapping[str, Any],
) -> EventEnvelope:
    _validate_payload(event, payload)
    return EventEnvelope(
        event=event,
        run_id=run_id,
        event_id=event_id or f"{run_id}:{sequence}",
        sequence=sequence,
        schema_version=schema_version,
        video_id=video_id,
        resolution=resolution,
        timestamp_ms=timestamp_ms,
        payload=payload,
    )


def build_track_update(
    *,
    run_id: str,
    sequence: int,
    video_id: str,
    resolution: str,
    timestamp_ms: int,
    track_id: str,
    state: str,
    bbox: tuple[float, float, float, float] | list[float],
    visibility: float,
    mask_confidence: float | None = None,
    length_mm: float | None = None,
    width_mm: float | None = None,
    volume_l: float | None = None,
    uncertainty_interval_l: tuple[float, float] | list[float] | None = None,
    volume_confidence: float = 0.0,
    counted: bool = False,
    catalog_candidates: Sequence[Mapping[str, Any]] | None = None,
    schema_version: str = "1.0",
    event_id: str | None = None,
) -> EventEnvelope:
    return _envelope(
        event="TRACK_UPDATE",
        run_id=run_id,
        event_id=event_id,
        sequence=sequence,
        schema_version=schema_version,
        video_id=video_id,
        resolution=resolution,
        timestamp_ms=timestamp_ms,
        payload={
            "track_id": track_id,
            "state": state,
            "bbox": list(bbox),
            "visibility": visibility,
            "mask_confidence": mask_confidence,
            "length_mm": length_mm,
            "width_mm": width_mm,
            "volume_l": volume_l,
            "uncertainty_interval_l": list(uncertainty_interval_l) if uncertainty_interval_l is not None else None,
            "volume_confidence": volume_confidence,
            "counted": counted,
            "catalog_candidates": list(catalog_candidates or ()),
        },
    )


def build_track_occluded(
    *,
    run_id: str,
    sequence: int,
    video_id: str,
    resolution: str,
    timestamp_ms: int,
    track_id: str,
    predicted_position: tuple[float, float] | list[float] | None,
    last_volume_l: float | None,
    volume_confidence: float,
    schema_version: str = "1.0",
    event_id: str | None = None,
) -> EventEnvelope:
    return _envelope(
        event="TRACK_OCCLUDED",
        run_id=run_id,
        event_id=event_id,
        sequence=sequence,
        schema_version=schema_version,
        video_id=video_id,
        resolution=resolution,
        timestamp_ms=timestamp_ms,
        payload={
            "track_id": track_id,
            "predicted_position": list(predicted_position) if predicted_position is not None else None,
            "last_volume_l": last_volume_l,
            "volume_confidence": volume_confidence,
        },
    )


def build_battery_counted(
    *,
    run_id: str,
    sequence: int,
    video_id: str,
    resolution: str,
    timestamp_ms: int,
    track_id: str,
    volume_l: float,
    uncertainty_interval_l: tuple[float, float] | list[float],
    volume_confidence: float,
    lot_count: int,
    lot_volume_l: float,
    catalog_candidates: Sequence[Mapping[str, Any]] | None = None,
    schema_version: str = "1.0",
    event_id: str | None = None,
) -> EventEnvelope:
    return _envelope(
        event="BATTERY_COUNTED",
        run_id=run_id,
        event_id=event_id,
        sequence=sequence,
        schema_version=schema_version,
        video_id=video_id,
        resolution=resolution,
        timestamp_ms=timestamp_ms,
        payload={
            "track_id": track_id,
            "volume_l": volume_l,
            "uncertainty_interval_l": list(uncertainty_interval_l),
            "volume_confidence": volume_confidence,
            "lot_count": lot_count,
            "lot_volume_l": lot_volume_l,
            "catalog_candidates": list(catalog_candidates or ()),
        },
    )


def validate_event_dict(record: Mapping[str, Any]) -> None:
    """Validate a decoded US1 event without requiring a transport object."""

    required = {
        "event",
        "run_id",
        "event_id",
        "sequence",
        "schema_version",
        "video_id",
        "resolution",
        "timestamp_ms",
    }
    missing = required - set(record)
    if missing:
        raise EventContractError(f"missing event fields: {sorted(missing)}")
    payload = {key: value for key, value in record.items() if key not in required}
    _validate_payload(str(record["event"]), payload)
    EventEnvelope(
        event=str(record["event"]),
        run_id=str(record["run_id"]),
        event_id=str(record["event_id"]),
        sequence=int(record["sequence"]),
        schema_version=str(record["schema_version"]),
        video_id=str(record["video_id"]),
        resolution=str(record["resolution"]),
        timestamp_ms=int(record["timestamp_ms"]),
        payload=payload,
    )
