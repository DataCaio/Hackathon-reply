from __future__ import annotations

from hackathon_reply import pipeline
from hackathon_reply.contracts.domain import FrameMeta
from hackathon_reply.io.replay import ReplayFrame


def test_replay_produces_identical_summary_for_identical_inputs(tmp_path) -> None:
    assert hasattr(pipeline, "run_replay")
    frames = [ReplayFrame(FrameMeta("video_01", "1080p", 0, 0, 200, 100, "cctv_01"), ())]
    first = pipeline.run_replay(frames, output_path=tmp_path / "first.jsonl", run_id="run-1")
    second = pipeline.run_replay(frames, output_path=tmp_path / "second.jsonl", run_id="run-2")
    assert first.to_dict() == second.to_dict()
