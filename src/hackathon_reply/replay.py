"""Deterministic detection-cache replay for the User Story 2 acceptance path."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from hackathon_reply.contracts import ReplayFrame, TrackState, VolumeEstimate
from hackathon_reply.counting.counter import CounterConfig, ExactlyOnceCounter
from hackathon_reply.counting.gate import CountGate
from hackathon_reply.events import (
    JsonlEventSink,
    battery_counted_event,
    track_occluded_event,
    track_update_event,
)
from hackathon_reply.vision.tracker import IoUTracker


@dataclass(frozen=True)
class ReplayResult:
    events: tuple[dict[str, Any], ...]
    summary: dict[str, Any]

    def write_events(self, path: str) -> None:
        sink = JsonlEventSink(path)
        for event in self.events:
            sink.write(event)


class ReplayRunner:
    def __init__(
        self,
        tracker: IoUTracker,
        gate: CountGate,
        counter_config: CounterConfig | None = None,
        processing_fps: float | None = None,
    ) -> None:
        self.tracker = tracker
        self.counter = ExactlyOnceCounter(gate, counter_config)
        self.processing_fps = processing_fps

    def run(self, frames: Iterable[ReplayFrame]) -> ReplayResult:
        sink = JsonlEventSink()
        expected_frame_id = 0
        previous_timestamp = -1
        video_id: str | None = None
        resolution: str | None = None
        last_estimates: dict[str, VolumeEstimate] = {}
        frames_processed = 0

        for frame in frames:
            meta = frame.meta
            if meta.frame_id != expected_frame_id:
                raise ValueError("frame identifiers must begin at zero and remain consecutive")
            if meta.timestamp_ms < previous_timestamp:
                raise ValueError("recording timestamps must be monotonic")
            if video_id is None:
                video_id, resolution = meta.video_id, meta.resolution
            elif (meta.video_id, meta.resolution) != (video_id, resolution):
                raise ValueError("a replay run cannot mix video IDs or resolutions")
            self._validate_estimates(frame.volume_estimates.values())

            observations = self.tracker.update(meta, frame.detections)
            for observation in observations:
                estimate = frame.volume_estimates.get(observation.detection_id) if observation.detection_id is not None else None
                if estimate is not None and estimate.is_valid:
                    last_estimates[observation.track_id] = estimate
                previous_estimate = last_estimates.get(observation.track_id)
                effective_estimate = estimate if estimate is not None and estimate.is_valid else previous_estimate

                if observation.state == TrackState.OCCLUDED:
                    sink.write(track_occluded_event(observation, previous_estimate))
                else:
                    sink.write(track_update_event(observation, effective_estimate))

                decision = self.counter.update(observation, effective_estimate)
                if decision is not None:
                    self.tracker.mark_counted(decision.track_id)
                    sink.write(battery_counted_event(decision))

            frames_processed += 1
            expected_frame_id += 1
            previous_timestamp = meta.timestamp_ms

        summary = {
            "video_id": video_id,
            "resolution": resolution,
            "frames_processed": frames_processed,
            "lot_count": self.counter.lot.count,
            "lot_volume_l": self.counter.lot.volume_l,
            "unique_tracks": len(self.tracker.confirmed_track_ids),
            "counted_track_ids": list(self.counter.lot.counted_track_ids),
            "processing_fps": self.processing_fps,
        }
        return ReplayResult(events=tuple(sink.events), summary=summary)

    @staticmethod
    def _validate_estimates(estimates: Iterable[VolumeEstimate]) -> None:
        for estimate in estimates:
            # Construction rejects non-finite, non-positive, or malformed values;
            # this loop also makes the fail-fast boundary explicit at replay input.
            if estimate.volume_l is None:
                continue
            if not estimate.is_valid:
                raise ValueError("invalid volume estimate cannot enter replay")
