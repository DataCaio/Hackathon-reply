from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

from hackathon_reply.contracts.events import (
    BATTERY_COUNTED_KEYS,
    COMMON_EVENT_KEYS,
    EVENT_KEYS,
    EVENT_TYPES,
    EventValidationError,
    TRACK_OCCLUDED_KEYS,
    TRACK_UPDATE_KEYS,
    validate_event,
    validate_event_stream,
)


def update_event(
    *,
    timestamp_ms: int = 1000,
    track_id: str = "battery-0001",
    state: str = "TRACKING",
    counted: bool = False,
) -> dict[str, object]:
    return {
        "event": "TRACK_UPDATE",
        "schema_version": 1,
        "timestamp_ms": timestamp_ms,
        "video_id": "video_03",
        "resolution": "720p",
        "track_id": track_id,
        "state": state,
        "bbox": [10.0, 20.0, 100.0, 120.0],
        "mask_confidence": 0.9,
        "visibility": 0.8,
        "length_mm": None,
        "width_mm": None,
        "geometry_uncertainty_mm": None,
        "volume_l": None,
        "volume_ci95_l": None,
        "volume_confidence": 0.0,
        "counted": counted,
    }


def counted_event(
    *, timestamp_ms: int = 2000, track_id: str = "battery-0001"
) -> dict[str, object]:
    return {
        "event": "BATTERY_COUNTED",
        "schema_version": 1,
        "timestamp_ms": timestamp_ms,
        "video_id": "video_03",
        "resolution": "720p",
        "track_id": track_id,
        "state": "COUNTED",
        "volume_l": 7.94,
        "volume_ci95_l": [7.4, 8.2],
        "volume_confidence": 0.83,
        "lot_count": 1,
        "lot_volume_l": 7.94,
    }


def occluded_event(*, timestamp_ms: int = 1500) -> dict[str, object]:
    return {
        "event": "TRACK_OCCLUDED",
        "schema_version": 1,
        "timestamp_ms": timestamp_ms,
        "video_id": "video_03",
        "resolution": "720p",
        "track_id": "battery-0001",
        "state": "OCCLUDED",
        "predicted_position": [50.0, 60.0],
        "last_volume_l": None,
        "volume_confidence": 0.0,
    }


def test_contract_freezes_three_event_types_and_key_sets() -> None:
    assert EVENT_TYPES == {
        "TRACK_UPDATE",
        "TRACK_OCCLUDED",
        "BATTERY_COUNTED",
    }
    assert COMMON_EVENT_KEYS <= TRACK_UPDATE_KEYS
    assert COMMON_EVENT_KEYS <= TRACK_OCCLUDED_KEYS
    assert COMMON_EVENT_KEYS <= BATTERY_COUNTED_KEYS
    assert set(EVENT_KEYS) == set(EVENT_TYPES)
    assert "PLC_STATE" not in set().union(*EVENT_KEYS.values())


def test_update_preserves_fixed_keys_and_null_semantics() -> None:
    event = update_event()
    assert set(validate_event(event)) == TRACK_UPDATE_KEYS
    assert event["length_mm"] is None
    assert event["width_mm"] is None
    assert event["volume_l"] is None
    assert event["volume_confidence"] == 0.0


def test_rejects_undeclared_keys_nonfinite_numbers_and_invalid_states() -> None:
    extra = update_event()
    extra["private_tracker_object"] = object()
    with pytest.raises(EventValidationError, match="undeclared"):
        validate_event(extra)

    nonfinite = update_event()
    nonfinite["visibility"] = math.nan
    with pytest.raises(EventValidationError, match="finite"):
        validate_event(nonfinite)

    invalid_state = update_event(state="PLC_STATE")
    with pytest.raises(EventValidationError, match="state"):
        validate_event(invalid_state)


def test_occlusion_requires_transition_and_fixed_state() -> None:
    validate_event(occluded_event())
    invalid = occluded_event()
    invalid["state"] = "TRACKING"
    with pytest.raises(EventValidationError, match="OCCLUDED"):
        validate_event(invalid)


def test_stream_enforces_timestamp_order_and_exactly_once_counts() -> None:
    events = [
        update_event(),
        occluded_event(),
        update_event(timestamp_ms=1600, state="OCCLUDED"),
        counted_event(timestamp_ms=2000),
    ]
    validated = validate_event_stream(events)
    assert len(validated) == len(events)

    with pytest.raises(EventValidationError, match="timestamp"):
        validate_event_stream([update_event(timestamp_ms=2), update_event(timestamp_ms=1, track_id="battery-0002")])

    duplicate = counted_event(timestamp_ms=2100)
    with pytest.raises(EventValidationError, match="duplicate"):
        validate_event_stream(events + [duplicate])


def test_counted_event_requires_positive_frozen_volume_and_lot_tally() -> None:
    invalid = counted_event()
    invalid["volume_l"] = 0.0
    with pytest.raises(EventValidationError, match="positive"):
        validate_event(invalid)

    invalid_lot = counted_event()
    invalid_lot["lot_count"] = 2
    with pytest.raises(EventValidationError, match="lot"):
        validate_event_stream([update_event(), invalid_lot])


def test_compatibility_examples_keep_v1_strict_until_approved_contract_update() -> None:
    root = Path(__file__).resolve().parents[1] / "fixtures" / "user_story3" / "compat"
    additive = json.loads((root / "v1_additive_approved.json").read_text(encoding="utf-8"))
    breaking = json.loads((root / "v2_breaking_required.json").read_text(encoding="utf-8"))
    assert additive["approval_status"] == "approved"
    assert additive["delivery"] == "future_contract_update"
    assert breaking["proposed_event_schema_version"] == 2
    assert breaking["delivery"] == "version_bump_required"

    proposed = update_event()
    proposed["consumer_note"] = "approved only in a future fixed-key revision"
    with pytest.raises(EventValidationError, match="undeclared"):
        validate_event(proposed)

    breaking_event = update_event()
    breaking_event["schema_version"] = 2
    with pytest.raises(EventValidationError, match="schema"):
        validate_event(breaking_event)
