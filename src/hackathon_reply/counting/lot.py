"""Exactly-once lot aggregation."""

from __future__ import annotations

from dataclasses import dataclass, field
from math import isfinite

from hackathon_reply.contracts.domain import VolumeEstimate


class LotError(ValueError):
    """Raised when a lot contribution is invalid."""


@dataclass(frozen=True)
class CountRecord:
    """Compatibility record for the repository's pre-existing replay runner."""

    track_id: str
    estimate: object


@dataclass
class Lot:
    """Mutable exactly-once total shared by US1 and the legacy replay adapter."""

    counted_track_ids: set[str] = field(default_factory=set)
    frozen_volumes_l: dict[str, float] = field(default_factory=dict)

    @property
    def count(self) -> int:
        return len(self.counted_track_ids)

    @property
    def volume_l(self) -> float:
        return sum(self.frozen_volumes_l.values())

    def record_once(self, track_id: str, estimate: object) -> CountRecord | None:
        if track_id in self.counted_track_ids:
            return None
        volume = getattr(estimate, "volume_l", None)
        if not getattr(estimate, "is_valid", False) or volume is None or volume <= 0:
            return None
        self.counted_track_ids.add(track_id)
        self.frozen_volumes_l[track_id] = float(volume)
        return CountRecord(track_id=track_id, estimate=estimate)


def is_countable(estimate: VolumeEstimate) -> bool:
    """Check the invariant required before a volume can enter a lot."""

    if not estimate.physical_validated or estimate.expected_volume_l is None:
        return False
    interval = estimate.uncertainty_interval_l
    return (
        estimate.confidence > 0
        and interval is not None
        and isfinite(estimate.expected_volume_l)
        and estimate.expected_volume_l > 0
        and interval[0] > 0
        and interval[1] >= interval[0]
        and all(isfinite(value) for value in interval)
    )


@dataclass
class LotAccumulator:
    """Freeze the first valid contribution for each operational track."""

    lot: Lot = field(default_factory=Lot)
    frozen_estimates: dict[str, VolumeEstimate] = field(default_factory=dict)

    def add(self, track_id: str, estimate: VolumeEstimate) -> bool:
        if not track_id:
            raise LotError("track_id is required")
        if track_id in self.lot.counted_track_ids:
            return False
        if not is_countable(estimate):
            return False
        assert estimate.expected_volume_l is not None
        self.lot.counted_track_ids.add(track_id)
        self.lot.frozen_volumes_l[track_id] = estimate.expected_volume_l
        self.frozen_estimates[track_id] = estimate
        return True

    def has_counted(self, track_id: str) -> bool:
        return track_id in self.lot.counted_track_ids
