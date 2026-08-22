#!/usr/bin/env python3
"""Produce a small, traceable User Story 4 audit report without private media."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from hackathon_reply.audit import GoldenSet, GoldenTrack
from hackathon_reply.manifest import DatasetManifest, VideoPair
from hackathon_reply.metrics.audit import AuditEvidence, RunOutcome, compare_resolutions, evaluate_paired_metrics


def complete_manifest() -> DatasetManifest:
    partitions = {1: "train", 2: "train", 3: "train", 4: "validation", 5: "test"}
    return DatasetManifest(
        tuple(
            VideoPair(
                video_id=f"video_{number:02d}",
                physical_video_id=f"physical_{number:02d}",
                video_1080=f"video_{number:02d}_1080.mp4",
                video_720=f"video_{number:02d}_720.mp4",
                partition=partitions[number],
                frame_count_1080=100,
                frame_count_720=100,
                duration_s_1080=10.0,
                duration_s_720=10.0,
                fps_1080=30.0,
                fps_720=30.0,
                camera_id="camera-fixture",
            )
            for number in range(1, 6)
        )
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    manifest = complete_manifest()
    manifest.validate()
    tracks = tuple(
        GoldenTrack(
            track_id=f"battery-{index:04d}",
            video_id="video_01",
            start_frame=index * 10,
            end_frame=index * 10 + 8,
            occluded_frames=(index * 10 + 3,),
            counted=index < 2,
            catalog_id=None,
            volume_l=None,
        )
        for index in range(10)
    )
    golden = GoldenSet(tracks=tracks, manual_count=2)
    golden.validate()

    comparison = compare_resolutions(
        RunOutcome("video_01", "1080p", "camera-fixture", "gate-fixture", 2, 10.0, ("battery-0000", "battery-0001")),
        RunOutcome("video_01", "720p", "camera-fixture", "gate-fixture", 2, 9.0, ("battery-0000", "battery-0001")),
    )
    evidence = AuditEvidence(
        predicted_count=2,
        manual_count=2,
        predicted_track_ids=("battery-0000", "battery-0001"),
        predicted_volumes={"battery-0000": 5.0, "battery-0001": 5.0},
        reference_volumes={"battery-0000": 5.0, "battery-0001": 5.0},
        uncertainty_intervals={"battery-0000": (4.5, 5.5), "battery-0001": (4.5, 5.5)},
    )
    metrics = evaluate_paired_metrics(
        RunOutcome("video_01", "1080p", "camera-fixture", "gate-fixture", 2, 10.0, ("battery-0000", "battery-0001")),
        RunOutcome("video_01", "720p", "camera-fixture", "gate-fixture", 2, 9.0, ("battery-0000", "battery-0001")),
        evidence,
    )
    report = {
        "golden_tracks": len(golden.tracks),
        "partition_by_video": {f"video_{number:02d}": manifest.partition_of(f"video_{number:02d}") for number in range(1, 6)},
        "comparison": {
            "video_id": comparison.video_id,
            "count_gap": comparison.count_gap,
            "relative_volume_gap": comparison.relative_volume_gap,
        },
        "metrics": {
            name: {"status": metric.status.value, "value": metric.value, "reason": metric.reason}
            for name, metric in metrics.items()
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
