"""US1 live/replay orchestration and paired-resolution summaries."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Mapping

from hackathon_reply.catalog.matcher import US1CatalogMatcher
from hackathon_reply.contracts import events
from hackathon_reply.contracts.domain import (
    CatalogEntry,
    CountGate,
    ResolutionComparison,
    RunSummary,
    TrackState,
    VolumeEstimate,
    bbox_centroid,
)
from hackathon_reply.counting.gate import crossed_gate
from hackathon_reply.counting.lot import LotAccumulator
from hackathon_reply.geometry.calibration import PhysicalCalibration
from hackathon_reply.geometry.measurement import measure_bbox
from hackathon_reply.io.event_sink import ExactlyOnceEventSink
from hackathon_reply.io.replay import ReplayFrame
from hackathon_reply.vision.detector import ReplayDetector
from hackathon_reply.vision.tracking import TrackManager


@dataclass(frozen=True)
class ReplayConfig:
    """Explicit US1 processing choices with safe, non-physical defaults."""

    calibration: PhysicalCalibration = field(default_factory=PhysicalCalibration.untrusted)
    catalog_entries: tuple[CatalogEntry, ...] = ()
    count_gate: CountGate = field(default_factory=lambda: CountGate((0.5, 0.0), (0.5, 1.0), "entry_to_exit"))
    max_occluded_frames: int = 3
    reacquisition_max_distance_norm: float = 0.10
    reacquisition_size_tolerance: float = 0.35
    minimum_measurement_quality: float = 0.10
    gate_epsilon: float = 1e-9
    schema_version: str = "1.0"


class PipelineError(RuntimeError):
    """Raised when a replay cannot produce a trustworthy run result."""


def _candidate_dicts(estimate: VolumeEstimate | None) -> list[dict[str, object]]:
    if estimate is None:
        return []
    return [
        {
            "catalog_id": candidate.catalog_id,
            "length_mm": candidate.length_mm,
            "width_mm": candidate.width_mm,
            "height_mm": candidate.height_mm,
            "probability": candidate.probability,
            "categories": list(candidate.categories),
        }
        for candidate in estimate.candidates
    ]


def _unavailable_estimate() -> VolumeEstimate:
    return VolumeEstimate(None, None, 0.0, (), physical_validated=False)


def _summary(
    *,
    video_id: str,
    resolution: str,
    frames_processed: int,
    lot: LotAccumulator,
    unique_tracks: int,
    first_timestamp_ms: int,
    last_timestamp_ms: int,
    warnings: list[str],
    errors: list[str],
) -> RunSummary:
    recording_seconds = max(0.0, (last_timestamp_ms - first_timestamp_ms) / 1000.0)
    observed_rate = (frames_processed / recording_seconds) if recording_seconds > 0 else 0.0
    return RunSummary(
        video_id=video_id,
        resolution=resolution,
        status="failed" if errors else "completed",
        frames_processed=frames_processed,
        lot_count=lot.lot.count,
        lot_volume_l=lot.lot.volume_l,
        unique_tracks=unique_tracks,
        counted_track_ids=tuple(sorted(lot.lot.counted_track_ids)),
        observed_rate_fps=observed_rate,
        warnings=tuple(dict.fromkeys(warnings)),
        errors=tuple(dict.fromkeys(errors)),
    )


def run_replay(
    frames: Iterable[ReplayFrame],
    *,
    output_path: str,
    run_id: str,
    calibration: PhysicalCalibration | None = None,
    catalog_entries: Iterable[CatalogEntry] = (),
    count_gate: CountGate | None = None,
    config: ReplayConfig | None = None,
) -> RunSummary:
    """Run one deterministic cached-detection sequence and emit JSONL events."""

    replay_frames = tuple(frames)
    if not replay_frames:
        raise PipelineError("replay requires at least one frame")
    first = replay_frames[0].meta
    for expected_id, replay_frame in enumerate(replay_frames):
        if replay_frame.meta.frame_id != expected_id:
            raise PipelineError("replay frame identifiers must start at zero and increment by one")
        if (replay_frame.meta.video_id, replay_frame.meta.resolution, replay_frame.meta.camera_id) != (
            first.video_id,
            first.resolution,
            first.camera_id,
        ):
            raise PipelineError("a replay run cannot mix video IDs, resolutions, or cameras")
    catalog_tuple = tuple(catalog_entries)
    active_config = config or ReplayConfig(
        calibration=calibration or PhysicalCalibration.untrusted(),
        catalog_entries=catalog_tuple,
        count_gate=count_gate or CountGate((0.5, 0.0), (0.5, 1.0), "entry_to_exit"),
    )
    if config is not None and (calibration is not None or catalog_tuple or count_gate is not None):
        active_config = ReplayConfig(
            calibration=calibration or active_config.calibration,
            catalog_entries=catalog_tuple if catalog_tuple else active_config.catalog_entries,
            count_gate=count_gate or active_config.count_gate,
            max_occluded_frames=active_config.max_occluded_frames,
            reacquisition_max_distance_norm=active_config.reacquisition_max_distance_norm,
            reacquisition_size_tolerance=active_config.reacquisition_size_tolerance,
            minimum_measurement_quality=active_config.minimum_measurement_quality,
            gate_epsilon=active_config.gate_epsilon,
            schema_version=active_config.schema_version,
        )
    if not run_id:
        raise PipelineError("run_id is required")
    if active_config.minimum_measurement_quality < 0 or active_config.minimum_measurement_quality > 1:
        raise PipelineError("minimum_measurement_quality must be between zero and one")

    detector = ReplayDetector(replay_frames)
    tracker = TrackManager(
        max_occluded_frames=active_config.max_occluded_frames,
        reacquisition_max_distance_norm=active_config.reacquisition_max_distance_norm,
        reacquisition_size_tolerance=active_config.reacquisition_size_tolerance,
    )
    matcher = US1CatalogMatcher(active_config.catalog_entries) if active_config.catalog_entries else None
    lot = LotAccumulator()
    previous_gate_points: dict[str, tuple[float, float]] = {}
    warnings: list[str] = []
    errors: list[str] = []
    if not active_config.calibration.trusted:
        warnings.append("trusted physical calibration unavailable; absolute volume is unvalidated")
    if not active_config.catalog_entries:
        warnings.append("catalog unavailable; volume inference is unavailable")

    try:
        with ExactlyOnceEventSink(output_path, run_id=run_id) as sink:
            for replay_frame in replay_frames:
                meta = replay_frame.meta
                observations = tracker.update(meta, detector.detect(meta))
                for observation in observations:
                    if observation.state in {TrackState.OCCLUDED, TrackState.LOST}:
                        estimate = tracker.volume_estimate(observation.track_id)
                        sink.write(
                            events.build_track_occluded(
                                run_id=run_id,
                                sequence=sink.next_sequence,
                                video_id=meta.video_id,
                                resolution=meta.resolution,
                                timestamp_ms=meta.timestamp_ms,
                                track_id=observation.track_id,
                                predicted_position=observation.predicted_centroid,
                                last_volume_l=estimate.expected_volume_l if estimate else None,
                                volume_confidence=estimate.confidence if estimate else 0.0,
                                schema_version=active_config.schema_version,
                            )
                        )
                        continue

                    measurement = measure_bbox(
                        track_id=observation.track_id,
                        frame_id=meta.frame_id,
                        bbox_xyxy=observation.bbox_xyxy,
                        mask_confidence=observation.mask_confidence,
                        visibility=observation.visibility,
                        calibration=active_config.calibration,
                    )
                    estimate = _unavailable_estimate()
                    if matcher is not None and measurement.quality >= active_config.minimum_measurement_quality:
                        estimate = matcher.update(measurement)
                        if estimate.expected_volume_l is not None:
                            tracker.set_volume_estimate(observation.track_id, estimate)
                    elif active_config.calibration.trusted and matcher is None:
                        warnings.append("trusted calibration supplied without a catalog; volume is unavailable")
                    previous_point = previous_gate_points.get(observation.track_id)
                    current_point = (
                        bbox_centroid(observation.bbox_xyxy)[0] / meta.width,
                        bbox_centroid(observation.bbox_xyxy)[1] / meta.height,
                    )
                    crossed = previous_point is not None and crossed_gate(
                        previous_point,
                        current_point,
                        active_config.count_gate,
                        epsilon=active_config.gate_epsilon,
                    )
                    previous_gate_points[observation.track_id] = current_point
                    sink.write(
                        events.build_track_update(
                            run_id=run_id,
                            sequence=sink.next_sequence,
                            video_id=meta.video_id,
                            resolution=meta.resolution,
                            timestamp_ms=meta.timestamp_ms,
                            track_id=observation.track_id,
                            state=observation.state.value,
                            bbox=observation.bbox_xyxy,
                            visibility=observation.visibility,
                            mask_confidence=observation.mask_confidence,
                            length_mm=measurement.length_mm,
                            width_mm=measurement.width_mm,
                            volume_l=estimate.expected_volume_l,
                            uncertainty_interval_l=estimate.uncertainty_interval_l,
                            volume_confidence=estimate.confidence,
                            counted=lot.has_counted(observation.track_id),
                            catalog_candidates=_candidate_dicts(estimate),
                            schema_version=active_config.schema_version,
                        )
                    )
                    if crossed and lot.add(observation.track_id, estimate):
                        tracker.mark_counted(observation.track_id)
                        assert estimate.expected_volume_l is not None
                        assert estimate.uncertainty_interval_l is not None
                        sink.write(
                            events.build_battery_counted(
                                run_id=run_id,
                                sequence=sink.next_sequence,
                                video_id=meta.video_id,
                                resolution=meta.resolution,
                                timestamp_ms=meta.timestamp_ms,
                                track_id=observation.track_id,
                                volume_l=estimate.expected_volume_l,
                                uncertainty_interval_l=estimate.uncertainty_interval_l,
                                volume_confidence=estimate.confidence,
                                lot_count=lot.lot.count,
                                lot_volume_l=lot.lot.volume_l,
                                catalog_candidates=_candidate_dicts(estimate),
                                schema_version=active_config.schema_version,
                            )
                        )
    except Exception as exc:
        errors.append(str(exc))

    return _summary(
        video_id=first.video_id,
        resolution=first.resolution,
        frames_processed=len(replay_frames) if not errors else 0,
        lot=lot,
        unique_tracks=tracker.unique_track_count,
        first_timestamp_ms=replay_frames[0].meta.timestamp_ms,
        last_timestamp_ms=replay_frames[-1].meta.timestamp_ms,
        warnings=warnings,
        errors=errors,
    )


def compare_summaries(
    pair_id: str,
    high_resolution: RunSummary,
    low_resolution: RunSummary,
) -> ResolutionComparison:
    """Compare aligned 1080p/720p outcomes without treating either as truth."""

    count_gap: int | None = None
    relative_volume_gap: float | None = None
    status = {
        "count_gap": "not_available",
        "relative_volume_gap": "not_available",
    }
    if high_resolution.status == "completed" and low_resolution.status == "completed":
        count_gap = high_resolution.lot_count - low_resolution.lot_count
        status["count_gap"] = "computed"
        denominator = (high_resolution.lot_volume_l + low_resolution.lot_volume_l) / 2
        if denominator > 0:
            relative_volume_gap = abs(high_resolution.lot_volume_l - low_resolution.lot_volume_l) / denominator
            status["relative_volume_gap"] = "computed"
    return ResolutionComparison(pair_id, count_gap, relative_volume_gap, status)


def run_paired_replay(
    frames_by_resolution: Mapping[str, Iterable[ReplayFrame]],
    *,
    output_paths: Mapping[str, str],
    run_id_prefix: str,
    config: ReplayConfig | None = None,
) -> tuple[dict[str, RunSummary], ResolutionComparison]:
    """Run exactly one 1080p/720p pair and return both summaries plus comparison."""

    if set(frames_by_resolution) != {"1080p", "720p"}:
        raise PipelineError("paired replay requires exactly 1080p and 720p inputs")
    summaries = {
        resolution: run_replay(
            frames,
            output_path=output_paths[resolution],
            run_id=f"{run_id_prefix}:{resolution}",
            config=config,
        )
        for resolution, frames in frames_by_resolution.items()
    }
    video_ids = {summary.video_id for summary in summaries.values()}
    if len(video_ids) != 1:
        raise PipelineError("paired replay inputs must share a physical video identity")
    comparison = compare_summaries(next(iter(video_ids)), summaries["1080p"], summaries["720p"])
    return summaries, comparison
