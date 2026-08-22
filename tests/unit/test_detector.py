from __future__ import annotations

from hackathon_reply.contracts.domain import Detection, FrameMeta
from hackathon_reply.io.replay import ReplayFrame
from hackathon_reply.vision import detector


def _meta(frame_id: int) -> FrameMeta:
    return FrameMeta("video_01", "1080p", frame_id, frame_id * 40, 200, 100, "cctv_01")


def test_replay_detector_returns_domain_detections_and_empty_frames() -> None:
    detection = Detection(1, (1, 2, 10, 20), ((1, 2), (10, 2), (10, 20)), 0.9)
    source = detector.ReplayDetector((ReplayFrame(_meta(0), (detection,)),))
    assert source.detect(_meta(0)) == (detection,)
    assert source.detect(_meta(1)) == ()


def test_empty_detector_is_a_valid_boundary_adapter() -> None:
    source = detector.EmptyDetector()
    assert source.detect(_meta(0)) == ()
