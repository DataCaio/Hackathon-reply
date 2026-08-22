from __future__ import annotations

import json

import pytest

from hackathon_reply.io import pair_manifest, replay


def test_pair_manifest_exports_explicit_pair_contract() -> None:
    assert hasattr(pair_manifest, "VideoPairManifest")
    assert hasattr(pair_manifest, "RecordingSpec")
    assert hasattr(pair_manifest, "load_manifest")
    assert hasattr(pair_manifest, "validate_pair_metadata")


def test_pair_manifest_loads_exact_filenames_and_rejects_mismatched_recordings(tmp_path) -> None:
    path = tmp_path / "pairs.json"
    path.write_text(
        json.dumps(
            {
                "pair_id": "video_01",
                "camera_id": "cctv_01",
                "recordings": [
                    {"resolution": "1080p", "filename": "Video_01.mp4"},
                    {"resolution": "720p", "filename": "Video_01_720p.mp4"},
                ],
            }
        ),
        encoding="utf-8",
    )
    manifest = pair_manifest.load_manifest(path)
    assert manifest.recording("1080p").filename == "Video_01.mp4"
    assert manifest.recording("720p").filename == "Video_01_720p.mp4"

    metadata = {
        "1080p": pair_manifest.RecordingMetadata(100, 10_000, 25.0, "physical-1"),
        "720p": pair_manifest.RecordingMetadata(100, 10_000, 25.0, "physical-2"),
    }
    with pytest.raises(pair_manifest.ManifestError, match="physical recording"):
        pair_manifest.validate_pair_metadata(manifest, metadata)


def test_replay_exports_frame_reader_contract() -> None:
    assert hasattr(replay, "ReplayFrame")
    assert hasattr(replay, "read_detection_jsonl")


def test_replay_reads_zero_based_monotonic_frames_and_detections(tmp_path) -> None:
    path = tmp_path / "detections.jsonl"
    path.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "video_id": "video_01",
                        "resolution": "1080p",
                        "frame_id": 0,
                        "timestamp_ms": 0,
                        "width": 1920,
                        "height": 1080,
                        "camera_id": "cctv_01",
                        "detections": [
                            {
                                "detection_id": 1,
                                "bbox_xyxy": [10, 20, 40, 60],
                                "mask_polygon": [[10, 20], [40, 20], [40, 60]],
                                "confidence": 0.9,
                            }
                        ],
                    }
                ),
                json.dumps(
                    {
                        "video_id": "video_01",
                        "resolution": "1080p",
                        "frame_id": 1,
                        "timestamp_ms": 40,
                        "width": 1920,
                        "height": 1080,
                        "camera_id": "cctv_01",
                        "detections": [],
                    }
                ),
            ]
        ),
        encoding="utf-8",
    )
    frames = list(replay.read_detection_jsonl(path))
    assert len(frames) == 2
    assert frames[0].meta.frame_id == 0
    assert len(frames[0].detections) == 1
    assert frames[1].detections == ()
