from __future__ import annotations

from hackathon_reply import pipeline
from hackathon_reply.contracts.domain import FrameMeta
from hackathon_reply.io.replay import ReplayFrame


def test_paired_run_emits_summaries_for_both_resolutions(tmp_path) -> None:
    assert hasattr(pipeline, "run_replay")
    frames_1080 = [ReplayFrame(FrameMeta("video_01", "1080p", 0, 0, 200, 100, "cctv_01"), ())]
    frames_720 = [ReplayFrame(FrameMeta("video_01", "720p", 0, 0, 128, 72, "cctv_01"), ())]
    high = pipeline.run_replay(frames_1080, output_path=tmp_path / "high.jsonl", run_id="high")
    low = pipeline.run_replay(frames_720, output_path=tmp_path / "low.jsonl", run_id="low")
    assert high.resolution == "1080p"
    assert low.resolution == "720p"
