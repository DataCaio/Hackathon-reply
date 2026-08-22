"""External JSON event contract and validation for the replay path."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from hackathon_reply.contracts import TrackObservation, TrackState, VolumeEstimate
from hackathon_reply.counting.counter import CountDecision

EVENT_NAMES = {"TRACK_UPDATE", "TRACK_OCCLUDED", "BATTERY_COUNTED"}


def track_update_event(observation: TrackObservation, estimate: VolumeEstimate | None) -> dict[str, Any]:
    estimate = estimate if estimate is not None and estimate.is_valid else None
    volume_interval = estimate.volume_ci95_l if estimate is not None else None
    return {
        "event": "TRACK_UPDATE",
        "timestamp_ms": observation.meta.timestamp_ms,
        "video_id": observation.meta.video_id,
        "resolution": observation.meta.resolution,
        "track_id": observation.track_id,
        "state": observation.state.value,
        "bbox": list(observation.bbox_xyxy),
        "mask_confidence": observation.mask_confidence,
        "visibility": observation.visibility,
        "length_mm": None,
        "width_mm": None,
        "volume_l": estimate.volume_l if estimate else None,
        "volume_ci95_l": list(volume_interval) if volume_interval is not None else None,
        "volume_confidence": estimate.volume_confidence if estimate else 0.0,
        "counted": observation.counted,
    }


def track_occluded_event(
    observation: TrackObservation,
    last_estimate: VolumeEstimate | None,
) -> dict[str, Any]:
    last_estimate = last_estimate if last_estimate is not None and last_estimate.is_valid else None
    predicted = observation.predicted_centroid or observation.centroid
    return {
        "event": "TRACK_OCCLUDED",
        "timestamp_ms": observation.meta.timestamp_ms,
        "video_id": observation.meta.video_id,
        "resolution": observation.meta.resolution,
        "track_id": observation.track_id,
        "predicted_position": list(predicted),
        "last_volume_l": last_estimate.volume_l if last_estimate else None,
        "volume_confidence": last_estimate.volume_confidence if last_estimate else 0.0,
    }


def battery_counted_event(decision: CountDecision) -> dict[str, Any]:
    estimate = decision.estimate
    return {
        "event": "BATTERY_COUNTED",
        "timestamp_ms": decision.meta.timestamp_ms,
        "video_id": decision.meta.video_id,
        "resolution": decision.meta.resolution,
        "track_id": decision.track_id,
        "volume_l": estimate.volume_l,
        "volume_ci95_l": list(estimate.volume_ci95_l or ()),
        "lot_count": decision.lot_count,
        "lot_volume_l": decision.lot_volume_l,
    }


def validate_event(event: dict[str, Any]) -> None:
    if event.get("event") not in EVENT_NAMES:
        raise ValueError("unknown external event")
    track_id = event.get("track_id")
    if not isinstance(track_id, str) or not track_id.startswith("battery-"):
        raise ValueError("event track_id must be a non-empty operational ID")
    if not isinstance(event.get("timestamp_ms"), int) or event["timestamp_ms"] < 0:
        raise ValueError("event timestamp_ms must be a non-negative integer")
    _validate_json_values(event)
    if event["event"] == "TRACK_UPDATE":
        if event.get("state") not in {state.value for state in TrackState}:
            raise ValueError("invalid track state")
        if not isinstance(event.get("bbox"), list) or len(event["bbox"]) != 4:
            raise ValueError("TRACK_UPDATE bbox must contain four original-frame values")
        _validate_interval(event.get("volume_ci95_l"))
    elif event["event"] == "TRACK_OCCLUDED":
        if not isinstance(event.get("predicted_position"), list) or len(event["predicted_position"]) != 2:
            raise ValueError("TRACK_OCCLUDED predicted_position must contain x/y")
    else:
        volume = event.get("volume_l")
        if not isinstance(volume, (int, float)) or volume <= 0:
            raise ValueError("BATTERY_COUNTED volume_l must be positive")
        _validate_interval(event.get("volume_ci95_l"))
        if not isinstance(event.get("lot_count"), int) or event["lot_count"] <= 0:
            raise ValueError("BATTERY_COUNTED lot_count must be positive")
        if not isinstance(event.get("lot_volume_l"), (int, float)) or event["lot_volume_l"] <= 0:
            raise ValueError("BATTERY_COUNTED lot_volume_l must be positive")


def _validate_interval(interval: Any) -> None:
    if interval is None:
        return
    if not isinstance(interval, list) or len(interval) != 2:
        raise ValueError("uncertainty interval must be null or [low, high]")
    if interval[0] < 0 or interval[1] < interval[0]:
        raise ValueError("uncertainty interval must be ordered and non-negative")


def _validate_json_values(value: Any) -> None:
    if isinstance(value, dict):
        for item in value.values():
            _validate_json_values(item)
    elif isinstance(value, list):
        for item in value:
            _validate_json_values(item)
    elif isinstance(value, float):
        if value != value or value in {float("inf"), float("-inf")}:
            raise ValueError("event numbers must be finite")


class JsonlEventSink:
    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path) if path is not None else None
        self.events: list[dict[str, Any]] = []
        self._last_timestamp: int | None = None

    def write(self, event: dict[str, Any]) -> None:
        validate_event(event)
        timestamp = event["timestamp_ms"]
        if self._last_timestamp is not None and timestamp < self._last_timestamp:
            raise ValueError("event timestamps must be monotonic")
        self._last_timestamp = timestamp
        json.dumps(event, allow_nan=False)
        self.events.append(event)
        if self.path is not None:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8") as output:
                output.write(json.dumps(event, allow_nan=False, separators=(",", ":")) + "\n")
