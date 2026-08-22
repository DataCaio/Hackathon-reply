from __future__ import annotations

from hackathon_reply.counting.counter import CounterConfig
from hackathon_reply.counting.gate import CountGate
from hackathon_reply.replay import ReplayRunner
from hackathon_reply.vision.tracker import IoUTracker, TrackerConfig
from tests.fixtures.story2 import acceptance_fixture, reverse_crossing_fixture


def runner() -> ReplayRunner:
    return ReplayRunner(
        tracker=IoUTracker(
            TrackerConfig(
                min_confirmed_hits=3,
                max_age_frames=4,
                max_match_distance_px=100,
                size_similarity_threshold=0.45,
            )
        ),
        gate=CountGate.vertical(normalized_x=0.5, flow_direction="positive"),
        counter_config=CounterConfig(),
    )


def test_story2_fixture_counts_only_the_confirmed_forward_crossing() -> None:
    result = runner().run(acceptance_fixture())

    counted = [event for event in result.events if event["event"] == "BATTERY_COUNTED"]
    assert len(counted) == 1
    assert counted[0]["track_id"] == "battery-0001"
    assert counted[0]["volume_l"] == 5.0
    assert counted[0]["lot_count"] == 1
    assert counted[0]["lot_volume_l"] == 5.0

    updates = [event for event in result.events if event["event"] == "TRACK_UPDATE"]
    states = {event["state"] for event in updates if event["track_id"] == "battery-0001"}
    assert {"TRACKING", "REACQUIRED", "COUNTED"}.issubset(states)
    assert any(event["event"] == "TRACK_OCCLUDED" and event["track_id"] == "battery-0001" for event in result.events)
    assert result.summary["lot_count"] == len(set(result.summary["counted_track_ids"]))
    assert result.summary["lot_volume_l"] == sum(event["volume_l"] for event in counted)
    assert result.summary["unique_tracks"] == 2
    assert all(event["track_id"] != "battery-0002" for event in counted)
    assert all(event["track_id"] != "battery-0003" for event in counted)


def test_reverse_crossing_does_not_count() -> None:
    result = runner().run(reverse_crossing_fixture())

    assert [event for event in result.events if event["event"] == "BATTERY_COUNTED"] == []
    assert result.summary["lot_count"] == 0
    assert result.summary["lot_volume_l"] == 0.0


def test_replay_is_deterministic_and_events_are_contract_safe() -> None:
    first = runner().run(acceptance_fixture())
    second = runner().run(acceptance_fixture())

    assert first.events == second.events
    assert first.summary == second.summary
    assert len(first.events) >= 20
    timestamps = [event["timestamp_ms"] for event in first.events]
    assert timestamps == sorted(timestamps)
    for event in first.events:
        assert "PLC_STATE" not in event
        assert event["track_id"].startswith("battery-")
        if event["event"] == "TRACK_UPDATE":
            assert len(event["bbox"]) == 4
            assert event["volume_ci95_l"] is None or len(event["volume_ci95_l"]) == 2
        elif event["event"] == "BATTERY_COUNTED":
            assert event["volume_l"] > 0
            assert event["volume_ci95_l"][0] <= event["volume_ci95_l"][1]
