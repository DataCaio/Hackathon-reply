"""Evidence-aware metrics that never substitute one resolution for truth."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from math import isfinite
from typing import Iterable


class MetricStatus(str, Enum):
    EVALUATED = "evaluated"
    NOT_AVAILABLE = "not_available"


@dataclass(frozen=True)
class MetricResult:
    status: MetricStatus
    value: float | None
    reason: str


@dataclass(frozen=True)
class AuditEvidence:
    predicted_count: int
    predicted_track_ids: Iterable[str]
    predicted_volumes: dict[str, float]
    manual_count: int | None = None
    reference_volumes: dict[str, float] | None = None
    uncertainty_intervals: dict[str, tuple[float, float]] | None = None


@dataclass(frozen=True)
class RunOutcome:
    video_id: str
    resolution: str
    camera_config_id: str
    gate_config_id: str
    lot_count: int
    lot_volume_l: float
    counted_track_ids: tuple[str, ...]


@dataclass(frozen=True)
class ResolutionComparison:
    video_id: str
    count_gap: int
    relative_volume_gap: float | None
    metrics: dict[str, MetricResult]


def evaluate_metrics(evidence: AuditEvidence) -> dict[str, MetricResult]:
    track_ids = tuple(evidence.predicted_track_ids)
    duplicate_excess = len(track_ids) - len(set(track_ids))
    results = {
        "relative_volume_error": _relative_volume_error(evidence),
        "duplicate_rate": _metric(
            duplicate_excess / len(track_ids) if track_ids else None,
            "duplicate identities measured from counted track IDs" if track_ids else "no counted track IDs",
        ),
        "count_error": _metric(
            float(abs(evidence.predicted_count - evidence.manual_count)) if evidence.manual_count is not None else None,
            "manual count available" if evidence.manual_count is not None else "manual count unavailable",
        ),
        "resolution_volume_gap": _not_available("requires two paired run outcomes"),
        "uncertainty_calibration": _uncertainty_calibration(evidence),
    }
    return results


def compare_resolutions(left: RunOutcome, right: RunOutcome) -> ResolutionComparison:
    if left.video_id != right.video_id:
        raise ValueError("resolution comparison requires the same physical video ID")
    if left.camera_config_id != right.camera_config_id or left.gate_config_id != right.gate_config_id:
        raise ValueError("resolution comparison requires the same camera and gate configuration")
    if {left.resolution, right.resolution} != {"720p", "1080p"}:
        raise ValueError("comparison requires one 720p and one 1080p run")
    denominator = (left.lot_volume_l + right.lot_volume_l) / 2
    gap = abs(left.lot_volume_l - right.lot_volume_l) / denominator if denominator > 0 else None
    metric = _metric(gap, "both lot volumes are positive" if gap is not None else "lot volume unavailable")
    return ResolutionComparison(
        left.video_id,
        abs(left.lot_count - right.lot_count),
        gap,
        {"resolution_volume_gap": metric},
    )


def evaluate_paired_metrics(
    left: RunOutcome,
    right: RunOutcome,
    evidence: AuditEvidence,
) -> dict[str, MetricResult]:
    metrics = evaluate_metrics(evidence)
    metrics["resolution_volume_gap"] = compare_resolutions(left, right).metrics["resolution_volume_gap"]
    return metrics


def _relative_volume_error(evidence: AuditEvidence) -> MetricResult:
    reference = evidence.reference_volumes or {}
    common = set(evidence.predicted_volumes).intersection(reference)
    if not common or sum(reference[track_id] for track_id in common) <= 0:
        return _not_available("independently verified volume truth unavailable")
    predicted = sum(evidence.predicted_volumes[track_id] for track_id in common)
    expected = sum(reference[track_id] for track_id in common)
    return _metric(abs(predicted - expected) / expected, "independently verified volume truth available")


def _uncertainty_calibration(evidence: AuditEvidence) -> MetricResult:
    reference = evidence.reference_volumes or {}
    intervals = evidence.uncertainty_intervals or {}
    common = set(reference).intersection(intervals)
    if not common:
        return _not_available("reference volumes and uncertainty intervals unavailable")
    covered = sum(intervals[track_id][0] <= reference[track_id] <= intervals[track_id][1] for track_id in common)
    return _metric(covered / len(common), "reference values are available for interval coverage")


def _metric(value: float | None, reason: str) -> MetricResult:
    if value is None or not isfinite(value):
        return _not_available(reason)
    return MetricResult(MetricStatus.EVALUATED, value, reason)


def _not_available(reason: str) -> MetricResult:
    return MetricResult(MetricStatus.NOT_AVAILABLE, None, reason)
