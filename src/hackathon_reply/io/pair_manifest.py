"""Explicit, case-sensitive paired-recording contracts."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping


class ManifestError(ValueError):
    """Raised when a pair manifest or its recordings are invalid."""


@dataclass(frozen=True, slots=True)
class RecordingSpec:
    resolution: str
    filename: str

    def __post_init__(self) -> None:
        if self.resolution not in {"720p", "1080p"}:
            raise ManifestError(f"unsupported recording resolution: {self.resolution}")
        if not self.filename:
            raise ManifestError("recording filename is required")


@dataclass(frozen=True, slots=True)
class VideoPairManifest:
    pair_id: str
    camera_id: str
    recordings: tuple[RecordingSpec, ...]

    def __post_init__(self) -> None:
        if not self.pair_id or not self.camera_id:
            raise ManifestError("pair_id and camera_id are required")
        resolutions = {recording.resolution for recording in self.recordings}
        if resolutions != {"720p", "1080p"} or len(self.recordings) != 2:
            raise ManifestError("a pair must contain exactly one 720p and one 1080p recording")

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "VideoPairManifest":
        recordings = tuple(
            RecordingSpec(str(item["resolution"]), str(item["filename"]))
            for item in data.get("recordings", [])
        )
        return cls(str(data.get("pair_id", "")), str(data.get("camera_id", "")), recordings)

    def recording(self, resolution: str) -> RecordingSpec:
        for recording in self.recordings:
            if recording.resolution == resolution:
                return recording
        raise ManifestError(f"recording is missing for {resolution}")


@dataclass(frozen=True, slots=True)
class RecordingMetadata:
    frame_count: int
    duration_ms: float
    frame_rate: float
    physical_recording_id: str
    frame_ids: tuple[int, ...] | None = None

    def __post_init__(self) -> None:
        if self.frame_count <= 0 or self.duration_ms <= 0 or self.frame_rate <= 0:
            raise ManifestError("recording metadata values must be positive")
        if not self.physical_recording_id:
            raise ManifestError("physical_recording_id is required")


def load_manifest(path: str | Path) -> VideoPairManifest:
    """Load a JSON manifest while preserving filename case exactly."""
    source = Path(path)
    try:
        data = json.loads(source.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ManifestError("pair manifests must be JSON-compatible") from exc
    if not isinstance(data, dict):
        raise ManifestError("pair manifest root must be an object")
    return VideoPairManifest.from_dict(data)


def validate_pair_metadata(
    manifest: VideoPairManifest,
    metadata_by_resolution: Mapping[str, RecordingMetadata],
    *,
    duration_tolerance_ms: float = 1.0,
    frame_rate_tolerance: float = 1e-6,
) -> None:
    """Validate that both declared recordings are the same physical source."""
    first = metadata_by_resolution.get("1080p")
    second = metadata_by_resolution.get("720p")
    if first is None or second is None:
        raise ManifestError("metadata for both resolutions is required")
    if first.physical_recording_id != second.physical_recording_id:
        raise ManifestError("recordings do not represent the same physical recording")
    if first.frame_count != second.frame_count:
        raise ManifestError("paired recordings have different frame counts")
    if abs(first.duration_ms - second.duration_ms) > duration_tolerance_ms:
        raise ManifestError("paired recordings have different durations")
    if abs(first.frame_rate - second.frame_rate) > frame_rate_tolerance:
        raise ManifestError("paired recordings have different frame rates")
    if first.frame_ids is not None and second.frame_ids is not None and first.frame_ids != second.frame_ids:
        raise ManifestError("paired recordings are not aligned by frame identifier")
