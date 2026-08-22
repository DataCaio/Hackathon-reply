from __future__ import annotations

from hackathon_reply.vision.tracker import IoUTracker, TrackerConfig
from tests.fixtures.story2 import detection, meta


def test_occlusion_and_reacquisition_preserve_operational_identity() -> None:
    tracker = IoUTracker(
        TrackerConfig(
            min_confirmed_hits=2,
            max_age_frames=3,
            max_match_distance_px=90,
            size_similarity_threshold=0.45,
        )
    )

    first = tracker.update(meta(0), [detection(1, 40, 50)])[0]
    confirmed = tracker.update(meta(1), [detection(2, 70, 50)])[0]
    occluded = tracker.update(meta(2), [])[0]
    occluded_again = tracker.update(meta(3), [])[0]
    reacquired = tracker.update(meta(4), [detection(3, 130, 50)])[0]
    tracking_again = tracker.update(meta(5), [detection(4, 160, 50)])[0]

    assert first.track_id == "battery-0001"
    assert confirmed.state.value == "TRACKING"
    assert occluded.state.value == "OCCLUDED"
    assert occluded_again.state.value == "OCCLUDED"
    assert reacquired.track_id == confirmed.track_id
    assert reacquired.state.value == "REACQUIRED"
    assert reacquired.reassociation_motion_score is not None
    assert reacquired.reassociation_size_score is not None
    assert tracking_again.state.value == "TRACKING"


def test_track_becomes_lost_after_reacquisition_window() -> None:
    tracker = IoUTracker(TrackerConfig(min_confirmed_hits=1, max_age_frames=2))
    tracker.update(meta(0), [detection(1, 40, 50)])
    tracker.update(meta(1), [])
    tracker.update(meta(2), [])
    lost = tracker.update(meta(3), [])[0]

    assert lost.state.value == "LOST"
