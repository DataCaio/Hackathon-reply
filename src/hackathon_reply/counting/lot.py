"""Immutable-per-count lot aggregation."""

from __future__ import annotations

from dataclasses import dataclass

from hackathon_reply.contracts import VolumeEstimate


@dataclass(frozen=True)
class CountRecord:
    track_id: str
    estimate: VolumeEstimate


class Lot:
    def __init__(self) -> None:
        self._records: dict[str, CountRecord] = {}

    def record_once(self, track_id: str, estimate: VolumeEstimate) -> CountRecord | None:
        if not estimate.is_valid:
            raise ValueError("a counted track requires a valid positive volume estimate")
        if track_id in self._records:
            return None
        record = CountRecord(track_id=track_id, estimate=estimate)
        self._records[track_id] = record
        return record

    @property
    def count(self) -> int:
        return len(self._records)

    @property
    def volume_l(self) -> float:
        return sum(record.estimate.volume_l or 0.0 for record in self._records.values())

    @property
    def counted_track_ids(self) -> tuple[str, ...]:
        return tuple(self._records)
