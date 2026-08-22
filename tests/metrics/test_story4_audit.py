from __future__ import annotations

import pytest

from hackathon_reply.audit import GoldenSet, GoldenTrack
from hackathon_reply.manifest import DatasetManifest, VideoPair
from hackathon_reply.metrics.audit import (
    AuditEvidence,
    MetricStatus,
    RunOutcome,
    compare_resolutions,
    evaluate_metrics,
    evaluate_paired_metrics,
)


def pair(video_number: int, partition: str) -> VideoPair:
    return VideoPair(
        video_id=f"video_{video_number:02d}",
        physical_video_id=f"physical_{video_number:02d}",
        video_1080=f"video_{video_number:02d}_1080.MP4",
        video_720=f"video_{video_number:02d}_720.mp4",
        partition=partition,
        frame_count_1080=100,
        frame_count_720=100,
        duration_s_1080=10.0,
        duration_s_720=10.0,
        fps_1080=30.0,
        fps_720=30.0,
        camera_id="camera-01",
    )


def test_explicit_manifest_keeps_paired_resolutions_in_one_partition() -> None:
    manifest = DatasetManifest((pair(1, "train"), pair(2, "train"), pair(3, "train"), pair(4, "validation"), pair(5, "test")))

    manifest.validate()
    assert manifest.partition_of("video_01") == "train"
    assert manifest.pair_for("video_05").video_720.endswith(".mp4")


def test_resolution_comparison_reports_count_and_relative_volume_gaps() -> None:
    left = RunOutcome("video_01", "1080p", "camera-01", "gate-1", 10, 100.0, ("battery-1",))
    right = RunOutcome("video_01", "720p", "camera-01", "gate-1", 9, 90.0, ("battery-2",))

    comparison = compare_resolutions(left, right)

    assert comparison.count_gap == 1
    assert comparison.relative_volume_gap == pytest.approx(10 / 95)
    assert comparison.metrics["resolution_volume_gap"].status == MetricStatus.EVALUATED


def test_unsupported_metrics_are_not_available_without_golden_truth() -> None:
    result = evaluate_metrics(
        AuditEvidence(
            predicted_count=10,
            predicted_track_ids=(f"battery-{i:04d}" for i in range(10)),
            predicted_volumes={"battery-0001": 5.0},
        )
    )

    assert result["relative_volume_error"].status == MetricStatus.NOT_AVAILABLE
    assert result["count_error"].status == MetricStatus.NOT_AVAILABLE
    assert result["uncertainty_calibration"].status == MetricStatus.NOT_AVAILABLE


def test_golden_truth_evaluates_error_duplicate_and_uncertainty_metrics() -> None:
    result = evaluate_metrics(
        AuditEvidence(
            predicted_count=2,
            manual_count=2,
            predicted_track_ids=("battery-0001", "battery-0001", "battery-0002"),
            predicted_volumes={"battery-0001": 5.0, "battery-0002": 4.0},
            reference_volumes={"battery-0001": 5.0, "battery-0002": 5.0},
            uncertainty_intervals={"battery-0001": (4.5, 5.5), "battery-0002": (3.5, 4.5)},
        )
    )

    assert result["relative_volume_error"].status == MetricStatus.EVALUATED
    assert result["count_error"].value == 0
    assert result["duplicate_rate"].value == pytest.approx(1 / 3)
    assert result["uncertainty_calibration"].value == pytest.approx(0.5)


def test_paired_evaluation_reports_all_supported_story4_metrics() -> None:
    evidence = AuditEvidence(
        predicted_count=2,
        manual_count=2,
        predicted_track_ids=("battery-0001", "battery-0002"),
        predicted_volumes={"battery-0001": 5.0, "battery-0002": 5.0},
        reference_volumes={"battery-0001": 5.0, "battery-0002": 5.0},
        uncertainty_intervals={"battery-0001": (4.5, 5.5), "battery-0002": (4.5, 5.5)},
    )
    result = evaluate_paired_metrics(
        RunOutcome("video_01", "1080p", "camera-01", "gate-1", 2, 10.0, ("battery-0001", "battery-0002")),
        RunOutcome("video_01", "720p", "camera-01", "gate-1", 2, 9.0, ("battery-0001", "battery-0002")),
        evidence,
    )

    assert set(result) == {
        "relative_volume_error",
        "duplicate_rate",
        "count_error",
        "resolution_volume_gap",
        "uncertainty_calibration",
    }
    assert all(metric.status == MetricStatus.EVALUATED for metric in result.values())


def test_golden_set_requires_traceable_ten_to_twenty_tracks() -> None:
    tracks = tuple(
        GoldenTrack(
            track_id=f"battery-{index:04d}",
            video_id="video_01",
            start_frame=index * 10,
            end_frame=index * 10 + 5,
            occluded_frames=(index * 10 + 2,),
            counted=index % 2 == 0,
            catalog_id=None,
            volume_l=None,
        )
        for index in range(10)
    )

    GoldenSet(tracks=tracks, manual_count=5).validate()
    with pytest.raises(ValueError, match="10..20"):
        GoldenSet(tracks=tracks[:9], manual_count=5).validate()
