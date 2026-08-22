"""Framework-independent value objects for the US1 processing pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from math import isfinite
from typing import Any, Mapping


class ContractError(ValueError):
    """Raised when an externally supplied domain value is invalid."""


def _finite(value: float, name: str) -> float:
    number = float(value)
    if not isfinite(number):
        raise ContractError(f"{name} must be finite")
    return number


def _point(point: tuple[float, float] | list[float], name: str) -> tuple[float, float]:
    if len(point) != 2:
        raise ContractError(f"{name} must contain two coordinates")
    return (_finite(point[0], f"{name}.x"), _finite(point[1], f"{name}.y"))


class Resolution(str, Enum):
    """Supported source resolutions."""

    P720 = "720p"
    P1080 = "1080p"


class TrackState(str, Enum):
    """Externally visible battery-track lifecycle states."""

    DETECTED = "DETECTED"
    TRACKING = "TRACKING"
    OCCLUDED = "OCCLUDED"
    REACQUIRED = "REACQUIRED"
    COUNTED = "COUNTED"
    LOST = "LOST"


@dataclass(frozen=True, slots=True)
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
            raise ContractError("video_id and camera_id are required")
        resolution = self.resolution.value if isinstance(self.resolution, Resolution) else self.resolution
        if resolution not in {item.value for item in Resolution}:
            raise ContractError(f"unsupported resolution: {resolution}")
        if self.frame_id < 0 or self.timestamp_ms < 0:
            raise ContractError("frame_id and timestamp_ms must be non-negative")
        if self.width <= 0 or self.height <= 0:
            raise ContractError("frame dimensions must be positive")
        object.__setattr__(self, "resolution", resolution)


@dataclass(frozen=True, slots=True)
class Detection:
    detection_id: int
    bbox_xyxy: tuple[float, float, float, float]
    mask_polygon: tuple[tuple[float, float], ...]
    confidence: float
    class_id: int = 0

    def __post_init__(self) -> None:
        if len(self.bbox_xyxy) != 4:
            raise ContractError("bbox_xyxy must contain four coordinates")
        coordinates = tuple(_finite(value, "bbox coordinate") for value in self.bbox_xyxy)
        if coordinates[2] < coordinates[0] or coordinates[3] < coordinates[1]:
            raise ContractError("bbox_xyxy must be ordered x_min,y_min,x_max,y_max")
        if len(self.mask_polygon) < 3:
            raise ContractError("mask_polygon must contain at least three points")
        polygon = tuple(_point(point, "mask_polygon point") for point in self.mask_polygon)
        confidence = _finite(self.confidence, "confidence")
        if not 0 <= confidence <= 1:
            raise ContractError("confidence must be between 0 and 1")
        object.__setattr__(self, "bbox_xyxy", coordinates)
        object.__setattr__(self, "mask_polygon", polygon)
        object.__setattr__(self, "confidence", confidence)


@dataclass(frozen=True, slots=True)
class TrackObservation:
    track_id: str
    state: TrackState
    meta: FrameMeta
    bbox_xyxy: tuple[float, float, float, float]
    mask_polygon: tuple[tuple[float, float], ...] | None
    mask_confidence: float | None
    visibility: float
    predicted_centroid: tuple[float, float] | None = None

    def __post_init__(self) -> None:
        if not self.track_id:
            raise ContractError("track_id is required")
        if len(self.bbox_xyxy) != 4:
            raise ContractError("track bbox must contain four coordinates")
        if not 0 <= self.visibility <= 1:
            raise ContractError("visibility must be between 0 and 1")
        if self.mask_confidence is not None and not 0 <= self.mask_confidence <= 1:
            raise ContractError("mask_confidence must be between 0 and 1")


@dataclass(frozen=True, slots=True)
class FrameMeasurement:
    track_id: str
    frame_id: int
    length_mm: float | None
    width_mm: float | None
    geometry_uncertainty_mm: float | None
    quality: float

    def __post_init__(self) -> None:
        if not self.track_id or self.frame_id < 0:
            raise ContractError("measurement identity is invalid")
        if not 0 <= self.quality <= 1:
            raise ContractError("measurement quality must be between 0 and 1")
        for value, name in (
            (self.length_mm, "length_mm"),
            (self.width_mm, "width_mm"),
            (self.geometry_uncertainty_mm, "geometry_uncertainty_mm"),
        ):
            if value is not None and (not isfinite(float(value)) or float(value) < 0):
                raise ContractError(f"{name} must be finite and non-negative when present")


@dataclass(frozen=True, slots=True)
class CatalogEntry:
    catalog_id: str
    length_mm: float
    width_mm: float
    height_mm: float
    categories: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.catalog_id:
            raise ContractError("catalog_id is required")
        for value, name in (
            (self.length_mm, "length_mm"),
            (self.width_mm, "width_mm"),
            (self.height_mm, "height_mm"),
        ):
            if not isfinite(float(value)) or float(value) <= 0:
                raise ContractError(f"{name} must be positive and finite")


@dataclass(frozen=True, slots=True)
class CatalogCandidate:
    catalog_id: str
    length_mm: float
    width_mm: float
    height_mm: float
    probability: float
    categories: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.catalog_id or not 0 <= self.probability <= 1:
            raise ContractError("candidate identity or probability is invalid")
        if any(
            not isfinite(float(value)) or float(value) <= 0
            for value in (self.length_mm, self.width_mm, self.height_mm)
        ):
            raise ContractError("candidate dimensions must be positive and finite")


@dataclass(frozen=True, slots=True)
class VolumeEstimate:
    expected_volume_l: float | None
    uncertainty_interval_l: tuple[float, float] | None
    confidence: float
    candidates: tuple[CatalogCandidate, ...] = ()
    physical_validated: bool = False

    def __post_init__(self) -> None:
        if not 0 <= self.confidence <= 1:
            raise ContractError("volume confidence must be between 0 and 1")
        if self.expected_volume_l is None:
            if self.uncertainty_interval_l is not None or self.confidence != 0:
                raise ContractError("unavailable volume must have no interval and zero confidence")
            return
        expected = _finite(self.expected_volume_l, "expected_volume_l")
        if expected <= 0 or self.uncertainty_interval_l is None:
            raise ContractError("available volume must be positive and have an interval")
        lower, upper = self.uncertainty_interval_l
        lower = _finite(lower, "uncertainty lower bound")
        upper = _finite(upper, "uncertainty upper bound")
        if lower <= 0 or upper < lower:
            raise ContractError("uncertainty interval must be ordered and positive")
        object.__setattr__(self, "expected_volume_l", expected)
        object.__setattr__(self, "uncertainty_interval_l", (lower, upper))

    def to_dict(self) -> dict[str, Any]:
        return {
            "volume_l": self.expected_volume_l,
            "uncertainty_interval_l": list(self.uncertainty_interval_l) if self.uncertainty_interval_l else None,
            "confidence": self.confidence,
            "physical_validated": self.physical_validated,
            "catalog_candidates": [
                {
                    "catalog_id": candidate.catalog_id,
                    "length_mm": candidate.length_mm,
                    "width_mm": candidate.width_mm,
                    "height_mm": candidate.height_mm,
                    "probability": candidate.probability,
                    "categories": list(candidate.categories),
                }
                for candidate in self.candidates
            ],
        }


@dataclass(frozen=True, slots=True)
class CountGate:
    p1_norm: tuple[float, float]
    p2_norm: tuple[float, float]
    direction: str = "entry_to_exit"

    def __post_init__(self) -> None:
        p1 = _point(self.p1_norm, "p1_norm")
        p2 = _point(self.p2_norm, "p2_norm")
        if p1 == p2:
            raise ContractError("count gate endpoints must differ")
        if self.direction not in {"entry_to_exit", "exit_to_entry"}:
            raise ContractError("count gate direction is invalid")
        object.__setattr__(self, "p1_norm", p1)
        object.__setattr__(self, "p2_norm", p2)


@dataclass
class Lot:
    counted_track_ids: set[str] = field(default_factory=set)
    frozen_volumes_l: dict[str, float] = field(default_factory=dict)

    @property
    def count(self) -> int:
        return len(self.counted_track_ids)

    @property
    def volume_l(self) -> float:
        return sum(self.frozen_volumes_l.values())

    def to_dict(self) -> dict[str, Any]:
        return {
            "count": self.count,
            "volume_l": self.volume_l,
            "counted_track_ids": sorted(self.counted_track_ids),
            "frozen_volumes_l": dict(sorted(self.frozen_volumes_l.items())),
        }


@dataclass(frozen=True, slots=True)
class RunSummary:
    video_id: str
    resolution: str
    status: str
    frames_processed: int
    lot_count: int
    lot_volume_l: float
    unique_tracks: int
    counted_track_ids: tuple[str, ...]
    observed_rate_fps: float
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "video_id": self.video_id,
            "resolution": self.resolution,
            "status": self.status,
            "frames_processed": self.frames_processed,
            "lot_count": self.lot_count,
            "lot_volume_l": self.lot_volume_l,
            "unique_tracks": self.unique_tracks,
            "counted_track_ids": list(self.counted_track_ids),
            "observed_rate_fps": self.observed_rate_fps,
            "warnings": list(self.warnings),
            "errors": list(self.errors),
        }


@dataclass(frozen=True, slots=True)
class ResolutionComparison:
    pair_id: str
    count_gap: int | None
    relative_volume_gap: float | None
    metric_status: Mapping[str, str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "pair_id": self.pair_id,
            "count_gap": self.count_gap,
            "relative_volume_gap": self.relative_volume_gap,
            "metric_status": dict(self.metric_status),
        }


def bbox_centroid(bbox_xyxy: tuple[float, float, float, float]) -> tuple[float, float]:
    """Return the center of an original-frame xyxy box."""
    x_min, y_min, x_max, y_max = bbox_xyxy
    return ((x_min + x_max) / 2, (y_min + y_max) / 2)
