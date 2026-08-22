from __future__ import annotations

import json

import pytest

from hackathon_reply.contracts import events


def test_event_contract_exports_envelope_and_three_event_builders() -> None:
    assert hasattr(events, "EventEnvelope")
    assert hasattr(events, "build_track_update")
    assert hasattr(events, "build_track_occluded")
    assert hasattr(events, "build_battery_counted")


def test_event_envelope_contains_replay_stable_identity_and_order() -> None:
    envelope = events.EventEnvelope(
        event="TRACK_UPDATE",
        run_id="run-1",
        event_id="run-1:0",
        sequence=0,
        schema_version="1.0",
        video_id="video_01",
        resolution="1080p",
        timestamp_ms=0,
        payload={"track_id": "battery-0001", "state": "TRACKING"},
    )
    serialized = envelope.to_dict()
    assert serialized["run_id"] == "run-1"
    assert serialized["event_id"] == "run-1:0"
    assert serialized["sequence"] == 0
    assert serialized["schema_version"] == "1.0"
    assert json.loads(envelope.to_json())["event"] == "TRACK_UPDATE"


def test_event_contract_rejects_control_state_and_invalid_count_interval() -> None:
    with pytest.raises(events.EventContractError):
        events.EventEnvelope(
            event="TRACK_UPDATE",
            run_id="run-1",
            event_id="run-1:0",
            sequence=0,
            schema_version="1.0",
            video_id="video_01",
            resolution="1080p",
            timestamp_ms=0,
            payload={"PLC_STATE": "ON"},
        )
    with pytest.raises(events.EventContractError):
        events.build_battery_counted(
            run_id="run-1",
            sequence=0,
            video_id="video_01",
            resolution="1080p",
            timestamp_ms=0,
            track_id="battery-0001",
            volume_l=1.0,
            uncertainty_interval_l=(1.2, 1.0),
            volume_confidence=0.8,
            lot_count=1,
            lot_volume_l=1.0,
        )
