"""Stable value contracts shared by replay, tracking, counting, and events."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from math import isfinite
from typing import Mapping, TypeAlias

Box: TypeAlias = tuple[float, float, float, float]
Point: TypeAlias = tuple[float, float]


class TrackState(str, Enum):
    DETECTED = "DETECTED"
    TRACKING = "TRACKING"
    OCCLUDED = "OCCLUDED"
    REACQUIRED = "REACQUIRED"
    COUNTED = "COUNTED"
    LOST = "LOST"


def _require_finite(value: float, field_name: str) -> None:
    if not isfinite(value):
        raise ValueError(f"{field_name} must be finite")


def _validate_box(box: Box) -> None:
    if len(box) != 4:
        raise ValueError("bbox_xyxy must contain four coordinates")
    if not all(isfinite(value) for value in box):
        raise ValueError("bbox_xyxy must contain only finite coordinates")
    x_min, y_min, x_max, y_max = box
    if x_max <= x_min or y_max <= y_min:
        raise ValueError("bbox_xyxy must have positive width and height")


@dataclass(frozen=True)
class FrameMeta:
    video_id: str
    resolution: str
    frame_id: int
    timestamp_ms: int
    width: int
    height: int
    camera_id: str

    def __post_init__(self) -> None:
        if not self.video_id or not self.camera_id:
            raise ValueError("video_id and camera_id are required")
        if self.resolution not in {"720p", "1080p"}:
            raise ValueError("resolution must be 720p or 1080p")
        if self.frame_id < 0:
            raise ValueError("frame_id must be zero-based")
        if self.timestamp_ms < 0:
            raise ValueError("timestamp_ms must be non-negative")
        if self.width <= 0 or self.height <= 0:
            raise ValueError("frame dimensions must be positive")


@dataclass(frozen=True)
class Detection:
    detection_id: int
    bbox_xyxy: Box
    mask_polygon: list[Point]
    confidence: float
    class_id: int = 0

    def __post_init__(self) -> None:
        if self.detection_id < 0:
            raise ValueError("detection_id must be non-negative")
        if self.class_id != 0:
            raise ValueError("only class_id=0 (battery) is supported")
        _validate_box(self.bbox_xyxy)
        if not 0 <= self.confidence <= 1 or not isfinite(self.confidence):
            raise ValueError("confidence must be finite and within 0..1")
        for point in self.mask_polygon:
            if len(point) != 2 or not all(isfinite(value) for value in point):
                raise ValueError("mask_polygon must contain finite x/y points")

    @property
    def centroid(self) -> Point:
        x_min, y_min, x_max, y_max = self.bbox_xyxy
        return ((x_min + x_max) / 2, (y_min + y_max) / 2)

    @property
    def size(self) -> Point:
        x_min, y_min, x_max, y_max = self.bbox_xyxy
        return (x_max - x_min, y_max - y_min)


@dataclass(frozen=True)
class VolumeEstimate:
    volume_l: float | None
    volume_ci95_l: tuple[float, float] | None
    volume_confidence: float

    def __post_init__(self) -> None:
        if not isfinite(self.volume_confidence) or not 0 <= self.volume_confidence <= 1:
            raise ValueError("volume_confidence must be finite and within 0..1")
        if self.volume_l is None:
            if self.volume_ci95_l is not None or self.volume_confidence != 0:
                raise ValueError("unavailable volume must use null interval and zero confidence")
            return
        _require_finite(self.volume_l, "volume_l")
        if self.volume_l <= 0:
            raise ValueError("volume_l must be positive when supplied")
        if self.volume_ci95_l is None or len(self.volume_ci95_l) != 2:
            raise ValueError("available volume requires a two-value uncertainty interval")
        low, high = self.volume_ci95_l
        _require_finite(low, "volume_ci95_l[0]")
        _require_finite(high, "volume_ci95_l[1]")
        if low < 0 or high < low:
            raise ValueError("volume_ci95_l must be ordered and non-negative")

    @property
    def is_valid(self) -> bool:
        return self.volume_l is not None

    @classmethod
    def unavailable(cls) -> "VolumeEstimate":
        return cls(volume_l=None, volume_ci95_l=None, volume_confidence=0.0)


@dataclass(frozen=True)
class TrackObservation:
    track_id: str
    state: TrackState
    meta: FrameMeta
    bbox_xyxy: Box
    mask_polygon: list[Point] | None
    mask_confidence: float | None
    visibility: float
    predicted_centroid: Point | None
    counted: bool = False
    confirmed: bool = False
    detection_id: int | None = None
    previous_state: TrackState | None = None
    reassociation_motion_score: float | None = None
    reassociation_size_score: float | None = None

    def __post_init__(self) -> None:
        if not self.track_id.startswith("battery-"):
            raise ValueError("operational track IDs must start with battery-")
        _validate_box(self.bbox_xyxy)
        if not 0 <= self.visibility <= 1 or not isfinite(self.visibility):
            raise ValueError("visibility must be finite and within 0..1")
        if self.mask_confidence is not None and (
            not isfinite(self.mask_confidence) or not 0 <= self.mask_confidence <= 1
        ):
            raise ValueError("mask_confidence must be null or within 0..1")
        if self.predicted_centroid is not None and not all(isfinite(value) for value in self.predicted_centroid):
            raise ValueError("predicted_centroid must contain finite coordinates")

    @property
    def centroid(self) -> Point:
        if not self.visibility and self.predicted_centroid is not None:
            return self.predicted_centroid
        x_min, y_min, x_max, y_max = self.bbox_xyxy
        return ((x_min + x_max) / 2, (y_min + y_max) / 2)


@dataclass(frozen=True)
class ReplayFrame:
    meta: FrameMeta
    detections: tuple[Detection, ...]
    volume_estimates: Mapping[int, VolumeEstimate]
