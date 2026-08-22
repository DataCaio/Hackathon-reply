from __future__ import annotations

from hackathon_reply.contracts.domain import CatalogCandidate, Detection, FrameMeta, TrackState, VolumeEstimate
from hackathon_reply.vision import tracking


def _meta(frame_id: int) -> FrameMeta:
    return FrameMeta("video_01", "1080p", frame_id, frame_id * 40, 200, 100, "cctv_01")


def _detection(x: float) -> Detection:
    return Detection(1, (x, 30, x + 20, 50), ((x, 30), (x + 20, 30), (x + 20, 50)), 0.9)


def test_track_keeps_operational_identity_across_temporary_occlusion() -> None:
    assert hasattr(tracking, "TrackManager")
    manager = tracking.TrackManager(max_occluded_frames=2)
    first = manager.update(_meta(0), (_detection(10),))
    assert first[0].track_id == "battery-0001"
    assert first[0].state == TrackState.DETECTED
    prior = VolumeEstimate(
        expected_volume_l=0.1,
        uncertainty_interval_l=(0.08, 0.12),
        confidence=0.8,
        candidates=(CatalogCandidate("catalog-a", 100, 50, 20, 1.0, ("A",)),),
        physical_validated=True,
    )
    manager.set_volume_estimate(first[0].track_id, prior)

    occluded = manager.update(_meta(1), ())
    assert occluded[0].track_id == "battery-0001"
    assert occluded[0].state == TrackState.OCCLUDED

    reacquired = manager.update(_meta(2), (_detection(12),))
    assert reacquired[0].track_id == "battery-0001"
    assert reacquired[0].state == TrackState.REACQUIRED
    assert manager.volume_estimate(reacquired[0].track_id) == prior
