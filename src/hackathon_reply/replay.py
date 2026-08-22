"""Deterministic replay utilities for the Story 2 and Story 3 acceptance paths."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
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

from hackathon_reply.contracts.diagnostics import normalize_summary
from hackathon_reply.contracts.events import EventValidationError, iter_validated_jsonl
from hackathon_reply.contracts.serialization import canonical_json, load_summary


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


class ReplayError(ValueError):
    """A Story 3 event replay input or summary violates its contract."""

    def __init__(
        self,
        message: str,
        *,
        code: str = "replay_error",
        line_number: int | None = None,
        event_type: str | None = None,
        track_id: str | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.line_number = line_number
        self.event_type = event_type
        self.track_id = track_id


@dataclass(frozen=True)
class CanonicalReplayResult:
    """Semantic result for a validated Story 3 canonical JSONL stream."""

    event_count: int
    event_types: frozenset[str]
    track_ids: frozenset[str]
    counted_track_ids: frozenset[str]
    events: tuple[dict[str, Any], ...]
    semantic_summary: dict[str, Any]


def _replay_error(exc: Exception) -> ReplayError:
    if isinstance(exc, EventValidationError):
        return ReplayError(
            str(exc),
            code=exc.code,
            line_number=exc.line_number,
            event_type=exc.event_type,
            track_id=exc.track_id,
        )
    return ReplayError(str(exc))


def replay_events(
    events_path: str | Path,
    summary_path: str | Path,
) -> CanonicalReplayResult:
    """Replay and validate a Story 3 canonical event stream."""

    try:
        summary = load_summary(summary_path)
    except Exception as exc:  # normalize all boundary errors to ReplayError
        raise _replay_error(exc) from exc

    event_count = 0
    event_types: set[str] = set()
    track_ids: set[str] = set()
    counted_track_ids: set[str] = set()
    events: list[dict[str, Any]] = []
    try:
        with Path(events_path).open("r", encoding="utf-8") as handle:
            for event in iter_validated_jsonl(handle):
                event_count += 1
                event_types.add(event["event"])
                track_ids.add(event["track_id"])
                if event["event"] == "BATTERY_COUNTED":
                    counted_track_ids.add(event["track_id"])
                events.append(event)
    except (OSError, EventValidationError) as exc:
        raise _replay_error(exc) from exc

    summary_ids = set(summary["counted_track_ids"])
    if summary_ids != counted_track_ids:
        raise ReplayError(
            "summary counted_track_ids do not match replayed count identities",
            code="summary_count_mismatch",
        )
    if summary["lot_count"] != len(counted_track_ids):
        raise ReplayError("summary lot_count does not match replayed counts", code="summary_count_mismatch")
    if summary["unique_tracks"] != len(track_ids):
        raise ReplayError("summary unique_tracks does not match replayed identities", code="summary_track_mismatch")

    return CanonicalReplayResult(
        event_count=event_count,
        event_types=frozenset(event_types),
        track_ids=frozenset(track_ids),
        counted_track_ids=frozenset(counted_track_ids),
        events=tuple(events),
        semantic_summary=normalize_summary(summary),
    )


def replay_to_files(
    events_path: str | Path,
    summary_path: str | Path,
    output_path: str | Path,
    result_path: str | Path,
) -> CanonicalReplayResult:
    """Replay a Story 3 stream to canonical JSONL and normalized result JSON."""

    result = replay_events(events_path, summary_path)
    output = Path(output_path)
    result_file = Path(result_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    result_file.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="\n") as handle:
        for event in result.events:
            handle.write(canonical_json(event))
            handle.write("\n")
    payload = {
        "event_count": result.event_count,
        "event_types": sorted(result.event_types),
        "track_ids": sorted(result.track_ids),
        "counted_track_ids": sorted(result.counted_track_ids),
        "summary": result.semantic_summary,
    }
    result_file.write_text(canonical_json(payload) + "\n", encoding="utf-8")
    return result


def semantic_summary(summary: dict[str, Any]) -> dict[str, Any]:
    """Normalize a Story 3 summary for deterministic equality checks."""

    return normalize_summary(summary)
