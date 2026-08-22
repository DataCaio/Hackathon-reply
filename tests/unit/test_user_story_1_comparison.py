from __future__ import annotations

from hackathon_reply import pipeline
from hackathon_reply.contracts.domain import RunSummary


def test_paired_comparison_reports_count_and_relative_volume_gaps() -> None:
    assert hasattr(pipeline, "compare_summaries")
    high = RunSummary("video_01", "1080p", "completed", 2, 3, 10.0, 3, ("battery-0001",), 20.0)
    low = RunSummary("video_01", "720p", "completed", 2, 2, 9.0, 2, ("battery-0001",), 20.0)
    comparison = pipeline.compare_summaries("video_01", high, low)
    assert comparison.count_gap == 1
    assert comparison.relative_volume_gap == 1 / 9.5
    assert comparison.metric_status["relative_volume_gap"] == "computed"
