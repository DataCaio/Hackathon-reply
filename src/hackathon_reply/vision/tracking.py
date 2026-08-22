"""Persistent battery-track state machine."""

from __future__ import annotations

from dataclasses import dataclass
from math import hypot
from typing import Iterable

from hackathon_reply.contracts.domain import (
    Detection,
    FrameMeta,
    TrackObservation,
    TrackState,
    VolumeEstimate,
    bbox_centroid,
)


class TrackingError(ValueError):
    """Raised when track input violates the ordered frame contract."""


@dataclass
class _Track:
    track_id: str
    bbox_xyxy: tuple[float, float, float, float]
    mask_polygon: tuple[tuple[float, float], ...] | None
    mask_confidence: float | None
    centroid: tuple[float, float]
    velocity: tuple[float, float]
    last_frame_id: int
    state: TrackState
    occluded_frames: int = 0
    counted: bool = False
    volume_estimate: VolumeEstimate | None = None


def _box_size(bbox: tuple[float, float, float, float]) -> tuple[float, float]:
    return (max(0.001, bbox[2] - bbox[0]), max(0.001, bbox[3] - bbox[1]))


def _predict_box(track: _Track, frame_id: int) -> tuple[float, float, float, float]:
    elapsed = max(1, frame_id - track.last_frame_id)
    center = (
        track.centroid[0] + track.velocity[0] * elapsed,
        track.centroid[1] + track.velocity[1] * elapsed,
    )
    width, height = _box_size(track.bbox_xyxy)
    return (
        center[0] - width / 2,
        center[1] - height / 2,
        center[0] + width / 2,
        center[1] + height / 2,
    )


class TrackManager:
    """Associate detections with persistent operational battery identities."""

    def __init__(
        self,
        *,
        max_occluded_frames: int = 3,
        reacquisition_max_distance_norm: float = 0.10,
        reacquisition_size_tolerance: float = 0.35,
    ) -> None:
        if max_occluded_frames < 0:
            raise TrackingError("max_occluded_frames must be non-negative")
        if reacquisition_max_distance_norm <= 0 or reacquisition_size_tolerance < 0:
            raise TrackingError("reacquisition thresholds are invalid")
        self.max_occluded_frames = max_occluded_frames
        self.reacquisition_max_distance_norm = reacquisition_max_distance_norm
        self.reacquisition_size_tolerance = reacquisition_size_tolerance
        self._tracks: dict[str, _Track] = {}
        self._next_identity = 1
        self._last_frame_id = -1

    @property
    def active_track_ids(self) -> tuple[str, ...]:
        return tuple(sorted(track_id for track_id, track in self._tracks.items() if track.state != TrackState.LOST))

    @property
    def unique_track_count(self) -> int:
        return len(self._tracks)

    @property
    def last_estimates(self) -> dict[str, VolumeEstimate]:
        return {
            track_id: track.volume_estimate
            for track_id, track in self._tracks.items()
            if track.volume_estimate is not None
        }

    def set_volume_estimate(self, track_id: str, estimate: VolumeEstimate) -> None:
        track = self._tracks.get(track_id)
        if track is None:
            raise TrackingError(f"unknown track: {track_id}")
        track.volume_estimate = estimate

    def volume_estimate(self, track_id: str) -> VolumeEstimate | None:
        track = self._tracks.get(track_id)
        return track.volume_estimate if track else None

    def mark_counted(self, track_id: str) -> None:
        track = self._tracks.get(track_id)
        if track is None:
            raise TrackingError(f"unknown track: {track_id}")
        track.counted = True
        track.state = TrackState.COUNTED

    def _new_track(self, meta: FrameMeta, detection: Detection) -> _Track:
        track_id = f"battery-{self._next_identity:04d}"
        self._next_identity += 1
        center = bbox_centroid(detection.bbox_xyxy)
        track = _Track(
            track_id=track_id,
            bbox_xyxy=detection.bbox_xyxy,
            mask_polygon=detection.mask_polygon,
            mask_confidence=detection.confidence,
            centroid=center,
            velocity=(0.0, 0.0),
            last_frame_id=meta.frame_id,
            state=TrackState.DETECTED,
        )
        self._tracks[track_id] = track
        return track

    def _match_score(self, track: _Track, detection: Detection, meta: FrameMeta) -> tuple[float, float] | None:
        predicted = _predict_box(track, meta.frame_id)
        predicted_center = bbox_centroid(predicted)
        detection_center = bbox_centroid(detection.bbox_xyxy)
        frame_scale = max(float(meta.width), float(meta.height), 1.0)
        distance_norm = hypot(
            detection_center[0] - predicted_center[0],
            detection_center[1] - predicted_center[1],
        ) / frame_scale
        old_width, old_height = _box_size(track.bbox_xyxy)
        new_width, new_height = _box_size(detection.bbox_xyxy)
        size_error = max(
            abs(new_width - old_width) / old_width,
            abs(new_height - old_height) / old_height,
        )
        if distance_norm > self.reacquisition_max_distance_norm or size_error > self.reacquisition_size_tolerance:
            return None
        return distance_norm, size_error

    def _visible_observation(self, track: _Track, meta: FrameMeta, detection: Detection) -> TrackObservation:
        previous_state = track.state
        previous_centroid = track.centroid
        current_centroid = bbox_centroid(detection.bbox_xyxy)
        elapsed = max(1, meta.frame_id - track.last_frame_id)
        track.velocity = (
            (current_centroid[0] - previous_centroid[0]) / elapsed,
            (current_centroid[1] - previous_centroid[1]) / elapsed,
        )
        track.bbox_xyxy = detection.bbox_xyxy
        track.mask_polygon = detection.mask_polygon
        track.mask_confidence = detection.confidence
        track.centroid = current_centroid
        track.last_frame_id = meta.frame_id
        track.occluded_frames = 0
        if track.counted:
            track.state = TrackState.COUNTED
        elif previous_state == TrackState.OCCLUDED:
            track.state = TrackState.REACQUIRED
        else:
            track.state = TrackState.TRACKING if previous_state != TrackState.DETECTED else TrackState.DETECTED
        return TrackObservation(
            track_id=track.track_id,
            state=track.state,
            meta=meta,
            bbox_xyxy=track.bbox_xyxy,
            mask_polygon=track.mask_polygon,
            mask_confidence=track.mask_confidence,
            visibility=max(0.0, min(1.0, detection.confidence)),
        )

    def _occluded_observation(self, track: _Track, meta: FrameMeta) -> TrackObservation:
        predicted = _predict_box(track, meta.frame_id)
        predicted_centroid = bbox_centroid(predicted)
        track.occluded_frames += 1
        track.bbox_xyxy = predicted
        track.centroid = predicted_centroid
        track.last_frame_id = meta.frame_id
        track.state = TrackState.OCCLUDED if track.occluded_frames <= self.max_occluded_frames else TrackState.LOST
        return TrackObservation(
            track_id=track.track_id,
            state=track.state,
            meta=meta,
            bbox_xyxy=predicted,
            mask_polygon=None,
            mask_confidence=None,
            visibility=0.0,
            predicted_centroid=predicted_centroid,
        )

    def update(self, meta: FrameMeta, detections: Iterable[Detection]) -> tuple[TrackObservation, ...]:
        if meta.frame_id <= self._last_frame_id:
            raise TrackingError("frame identifiers must increase strictly")
        self._last_frame_id = meta.frame_id
        incoming = tuple(detections)
        active = [track for track in self._tracks.values() if track.state != TrackState.LOST]
        matches: dict[str, Detection] = {}
        unmatched_detections = set(range(len(incoming)))
        candidates: list[tuple[float, float, str, int]] = []
        for track in active:
            for index, incoming_detection in enumerate(incoming):
                score = self._match_score(track, incoming_detection, meta)
                if score is not None:
                    candidates.append((score[0], score[1], track.track_id, index))
        for _, _, track_id, detection_index in sorted(candidates):
            if track_id in matches or detection_index not in unmatched_detections:
                continue
            matches[track_id] = incoming[detection_index]
            unmatched_detections.remove(detection_index)

        observations: list[TrackObservation] = []
        for track in sorted(active, key=lambda item: item.track_id):
            detection = matches.get(track.track_id)
            observations.append(
                self._visible_observation(track, meta, detection)
                if detection is not None
                else self._occluded_observation(track, meta)
            )
        for detection_index in sorted(unmatched_detections):
            track = self._new_track(meta, incoming[detection_index])
            observations.append(self._visible_observation(track, meta, incoming[detection_index]))
        return tuple(sorted(observations, key=lambda item: item.track_id))
