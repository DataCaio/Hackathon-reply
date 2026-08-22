from __future__ import annotations

import json
from pathlib import Path

import pytest

from hackathon_reply.contracts.events import EventValidationError, load_event_stream
from hackathon_reply.contracts.serialization import SerializationError, load_summary
from hackathon_reply.replay import ReplayError, replay_to_files


def test_replay_preserves_canonical_order_and_is_deterministic(
    fixture_root: Path, tmp_path: Path
) -> None:
    events_path = fixture_root / "events.jsonl"
    summary_path = fixture_root / "summary.json"
    first_events = tmp_path / "first.jsonl"
    first_result = tmp_path / "first.json"
    second_events = tmp_path / "second.jsonl"
    second_result = tmp_path / "second.json"

    first = replay_to_files(events_path, summary_path, first_events, first_result)
    second = replay_to_files(events_path, summary_path, second_events, second_result)

    assert first.event_count >= 20
    assert first.events == second.events
    assert first.semantic_summary == second.semantic_summary
    assert first_events.read_text(encoding="utf-8") == second_events.read_text(encoding="utf-8")
    assert json.loads(first_result.read_text(encoding="utf-8")) == json.loads(
        second_result.read_text(encoding="utf-8")
    )


def test_replay_reports_first_invalid_line(tmp_path: Path) -> None:
    events_path = tmp_path / "invalid.jsonl"
    summary_path = tmp_path / "summary.json"
    events_path.write_text(
        '{"event":"TRACK_UPDATE","schema_version":1,"timestamp_ms":1,'
        '"video_id":"video_03","resolution":"720p","track_id":"battery-0001",'
        '"state":"TRACKING","bbox":null,"mask_confidence":null,"visibility":0.5,'
        '"length_mm":null,"width_mm":null,"geometry_uncertainty_mm":null,'
        '"volume_l":null,"volume_ci95_l":null,"volume_confidence":0.0,"counted":false}\n'
        '{"event":"PLC_STATE","schema_version":1}\n',
        encoding="utf-8",
    )
    summary_path.write_text(
        json.dumps(
            {
                "summary_schema_version": 1,
                "video_id": "video_03",
                "resolution": "720p",
                "frames_processed": 1,
                "lot_count": 0,
                "lot_volume_l": None,
                "unique_tracks": 1,
                "counted_track_ids": [],
                "processing_fps": None,
                "health_status": "DEGRADED",
                "run_status": "PARTIAL",
                "warnings": [],
                "errors": [],
                "replayable": True,
                "replay_evidence_refs": [],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ReplayError) as exc_info:
        replay_to_files(events_path, summary_path, tmp_path / "out.jsonl", tmp_path / "out.json")
    assert exc_info.value.line_number == 2
    assert exc_info.value.code in {"unknown_event", "missing_keys"}


def test_fixture_contains_per_frame_updates_and_transition_occlusion(
    fixture_root: Path,
) -> None:
    lines = [
        json.loads(line)
        for line in (fixture_root / "events.jsonl").read_text(encoding="utf-8").splitlines()
        if line
    ]
    updates = [item for item in lines if item["event"] == "TRACK_UPDATE"]
    occlusions = [item for item in lines if item["event"] == "TRACK_OCCLUDED"]
    counts = [item for item in lines if item["event"] == "BATTERY_COUNTED"]

    timestamps = [item["timestamp_ms"] for item in updates if item["track_id"] == "battery-0001"]
    assert timestamps == sorted(set(timestamps))
    assert len(occlusions) == 1
    assert any(item["state"] == "OCCLUDED" for item in updates)
    assert any(item["state"] == "REACQUIRED" for item in updates)
    assert len(counts) == 1
    assert any(item["counted"] for item in updates if item["timestamp_ms"] > counts[0]["timestamp_ms"])


def test_invalid_fixture_corpus_fails_closed(fixture_root: Path) -> None:
    invalid_root = fixture_root / "invalid"
    for path in sorted(invalid_root.glob("*.jsonl")):
        with pytest.raises(EventValidationError):
            load_event_stream(path)
    with pytest.raises(SerializationError):
        load_summary(invalid_root / "interrupted_complete" / "summary.json")
