from __future__ import annotations

from hackathon_reply.contracts import domain


def test_run_summary_contains_us1_totals_and_health() -> None:
    summary = domain.RunSummary(
        video_id="video_01",
        resolution="1080p",
        status="completed",
        frames_processed=1,
        lot_count=0,
        lot_volume_l=0.0,
        unique_tracks=0,
        counted_track_ids=(),
        observed_rate_fps=1.0,
    )
    assert summary.to_dict()["resolution"] == "1080p"
    assert summary.to_dict()["status"] == "completed"
    assert "warnings" in summary.to_dict()
    assert "errors" in summary.to_dict()


def test_resolution_comparison_reports_gaps_or_unavailability() -> None:
    comparison = domain.ResolutionComparison(
        pair_id="video_01",
        count_gap=0,
        relative_volume_gap=0.0,
        metric_status={"count_gap": "computed"},
    )
    assert comparison.to_dict()["pair_id"] == "video_01"
    assert comparison.to_dict()["metric_status"]["count_gap"] == "computed"
