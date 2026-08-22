"""Directed, confirmed, exactly-once count decisions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import cast

from hackathon_reply.contracts import FrameMeta, TrackObservation, TrackState, VolumeEstimate
from hackathon_reply.counting.gate import CountGate
from hackathon_reply.counting.lot import CountRecord, Lot


@dataclass(frozen=True)
class CounterConfig:
    require_confirmed_track: bool = True


@dataclass(frozen=True)
class CountDecision:
    record: CountRecord
    meta: FrameMeta
    lot_count: int
    lot_volume_l: float

    @property
    def track_id(self) -> str:
        return self.record.track_id

    @property
    def estimate(self) -> VolumeEstimate:
        return cast(VolumeEstimate, self.record.estimate)


class ExactlyOnceCounter:
    def __init__(self, gate: CountGate, config: CounterConfig | None = None) -> None:
        self.gate = gate
        self.config = config or CounterConfig()
        self.lot = Lot()
        self._last_side: dict[str, float] = {}

    def update(self, observation: TrackObservation, estimate: VolumeEstimate | None) -> CountDecision | None:
        if observation.visibility <= 0:
            return None
        point = self.gate.normalized_point(
            observation.centroid,
            observation.meta.width,
            observation.meta.height,
        )
        current_side = self.gate.side(point)
        previous_side = self._last_side.get(observation.track_id)
        crossed = previous_side is not None and self.gate.crossed(previous_side, current_side)
        if abs(current_side) >= self.gate.epsilon:
            self._last_side[observation.track_id] = current_side

        eligible_state = observation.state in {TrackState.TRACKING, TrackState.REACQUIRED}
        if self.config.require_confirmed_track and not observation.confirmed:
            eligible_state = False
        if not eligible_state or observation.counted or observation.track_id in self.lot.counted_track_ids:
            return None
        if not crossed or estimate is None or not estimate.is_valid:
            return None
        record = self.lot.record_once(observation.track_id, estimate)
        if record is None:
            return None
        return CountDecision(
            record=record,
            meta=observation.meta,
            lot_count=self.lot.count,
            lot_volume_l=self.lot.volume_l,
        )
