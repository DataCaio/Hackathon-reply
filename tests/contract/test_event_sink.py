from __future__ import annotations

import json

import pytest

from hackathon_reply.contracts.events import EventContractError, EventEnvelope
from hackathon_reply.io import event_sink
from scripts.validate_events import validate


def _event(sequence: int = 0, event_id: str | None = None) -> EventEnvelope:
    return EventEnvelope(
        event="TRACK_UPDATE",
        run_id="run-1",
        event_id=event_id or f"run-1:{sequence}",
        sequence=sequence,
        schema_version="1.0",
        video_id="video_01",
        resolution="1080p",
        timestamp_ms=sequence * 40,
        payload={"track_id": "battery-0001", "state": "TRACKING"},
    )


def test_event_sink_writes_one_json_record_per_event_and_rejects_duplicates(tmp_path) -> None:
    assert hasattr(event_sink, "ExactlyOnceEventSink")
    output = tmp_path / "events.jsonl"
    sink = event_sink.ExactlyOnceEventSink(output, run_id="run-1")
    sink.write(_event())
    with pytest.raises(event_sink.EventDeliveryError, match="duplicate"):
        sink.write(_event(event_id="run-1:0"))
    sink.write(_event(sequence=1))
    sink.close()

    records = [json.loads(line) for line in output.read_text(encoding="utf-8").splitlines()]
    assert [record["sequence"] for record in records] == [0, 1]


def test_event_sink_rejects_wrong_run_and_non_monotonic_sequence(tmp_path) -> None:
    output = tmp_path / "events.jsonl"
    sink = event_sink.ExactlyOnceEventSink(output, run_id="run-1")
    with pytest.raises(event_sink.EventDeliveryError, match="run_id"):
        sink.write(EventEnvelope(
            event="TRACK_UPDATE",
            run_id="run-2",
            event_id="run-2:0",
            sequence=0,
            schema_version="1.0",
            video_id="video_01",
            resolution="1080p",
            timestamp_ms=0,
            payload={},
        ))
    sink.write(_event(sequence=0))
    with pytest.raises(event_sink.EventDeliveryError, match="sequence"):
        sink.write(_event(sequence=0, event_id="run-1:0b"))


def test_event_sink_marks_only_a_clean_context_complete(tmp_path) -> None:
    output = tmp_path / "events.jsonl"
    with pytest.raises(RuntimeError):
        with event_sink.ExactlyOnceEventSink(output, run_id="run-1") as sink:
            sink.write(_event())
            raise RuntimeError("interrupted")
    assert not output.with_name(output.name + ".complete").exists()
    with pytest.raises(EventContractError, match="incomplete"):
        validate(output)

    clean_output = tmp_path / "clean-events.jsonl"
    with event_sink.ExactlyOnceEventSink(clean_output, run_id="run-1") as sink:
        sink.write(_event())
    assert clean_output.with_name(clean_output.name + ".complete").exists()
