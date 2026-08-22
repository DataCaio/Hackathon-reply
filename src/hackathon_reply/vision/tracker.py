"""Dependency-free persistent tracker used by the deterministic replay path."""

from __future__ import annotations

from dataclasses import dataclass
from math import hypot

from hackathon_reply.contracts import Detection, FrameMeta, Point, TrackObservation, TrackState


@dataclass(frozen=True)
class TrackerConfig:
    min_confirmed_hits: int = 3
    max_age_frames: int = 45
    max_match_distance_px: float = 120.0
    size_similarity_threshold: float = 0.45
    motion_weight: float = 0.7
    size_weight: float = 0.3

    def __post_init__(self) -> None:
        if self.min_confirmed_hits <= 0:
            raise ValueError("min_confirmed_hits must be positive")
        if self.max_age_frames < 0:
            raise ValueError("max_age_frames must be non-negative")
        if self.max_match_distance_px <= 0:
            raise ValueError("max_match_distance_px must be positive")
        if not 0 < self.size_similarity_threshold <= 1:
            raise ValueError("size_similarity_threshold must be within (0, 1]")
        if self.motion_weight < 0 or self.size_weight < 0 or self.motion_weight + self.size_weight == 0:
            raise ValueError("motion and size weights must be non-negative and non-zero together")


@dataclass
class _Track:
    track_id: str
    last_detection: Detection
    last_frame_id: int
    velocity: Point = (0.0, 0.0)
    hits: int = 1
    missed: int = 0
    state: TrackState = TrackState.DETECTED
    confirmed: bool = False
    counted: bool = False

    @property
    def center(self) -> Point:
        return self.last_detection.centroid

    @property
    def size(self) -> Point:
        return self.last_detection.size


@dataclass(frozen=True)
class _Match:
    track: _Track
    detection: Detection
    motion_score: float
    size_score: float
    score: float
    frame_gap: int


class IoUTracker:
    """A small adapter with stable identity, occlusion, and reacquisition semantics.

    The adapter intentionally exposes no internal tracker identifier. A new track is
    confirmed after ``min_confirmed_hits`` matching detections. Missing detections
    enter ``OCCLUDED`` until ``max_age_frames`` is exceeded, then become ``LOST``.
    A visible detection matched after an occlusion requires both predicted-motion and
    size evidence and enters ``REACQUIRED`` while retaining the operational ID.
    """

    def __init__(self, config: TrackerConfig | None = None) -> None:
        self.config = config or TrackerConfig()
        self._tracks: dict[str, _Track] = {}
        self._next_id = 1
        self._last_frame_id: int | None = None

    def update(self, meta: FrameMeta, detections: list[Detection] | tuple[Detection, ...]) -> list[TrackObservation]:
        self._validate_frame_progress(meta)
        detections = tuple(detections)
        active_tracks = [track for track in self._tracks.values() if track.state != TrackState.LOST]
        matches = self._match(active_tracks, detections, meta.frame_id)
        matched_detection_ids = {match.detection.detection_id for match in matches}

        observations: list[TrackObservation] = []
        for track in active_tracks:
            match = next((item for item in matches if item.track.track_id == track.track_id), None)
            if match is not None:
                observations.append(self._apply_match(match, meta))
                continue
            observations.append(self._apply_miss(track, meta))

        for detection in detections:
            if detection.detection_id in matched_detection_ids:
                continue
            track = self._new_track(detection, meta.frame_id)
            observations.append(self._observation_for_new_track(track, meta))

        self._last_frame_id = meta.frame_id
        return observations

    def mark_counted(self, track_id: str) -> None:
        track = self._tracks.get(track_id)
        if track is None:
            raise KeyError(f"unknown track {track_id}")
        track.counted = True
        if track.state in {TrackState.TRACKING, TrackState.REACQUIRED}:
            track.state = TrackState.COUNTED

    @property
    def confirmed_track_ids(self) -> tuple[str, ...]:
        return tuple(track.track_id for track in self._tracks.values() if track.confirmed)

    def _validate_frame_progress(self, meta: FrameMeta) -> None:
        if self._last_frame_id is not None and meta.frame_id <= self._last_frame_id:
            raise ValueError("frame identifiers must increase strictly within a run")

    def _match(self, tracks: list[_Track], detections: tuple[Detection, ...], frame_id: int) -> list[_Match]:
        candidates: list[_Match] = []
        for track in tracks:
            if track.missed > self.config.max_age_frames:
                continue
            frame_gap = frame_id - track.last_frame_id
            predicted = self._predicted_center(track, frame_gap)
            for detection in detections:
                motion_score = self._motion_score(predicted, detection.centroid)
                size_score = self._size_score(track.size, detection.size)
                if motion_score <= 0 or size_score < self.config.size_similarity_threshold:
                    continue
                score = (
                    self.config.motion_weight * motion_score + self.config.size_weight * size_score
                ) / (self.config.motion_weight + self.config.size_weight)
                candidates.append(_Match(track, detection, motion_score, size_score, score, frame_gap))

        candidates.sort(key=lambda match: (-match.score, match.track.track_id, match.detection.detection_id))
        selected: list[_Match] = []
        used_tracks: set[str] = set()
        used_detections: set[int] = set()
        for candidate in candidates:
            if candidate.track.track_id in used_tracks or candidate.detection.detection_id in used_detections:
                continue
            selected.append(candidate)
            used_tracks.add(candidate.track.track_id)
            used_detections.add(candidate.detection.detection_id)
        return selected

    def _apply_match(self, match: _Match, meta: FrameMeta) -> TrackObservation:
        track = match.track
        previous_state = track.state
        previous_center = track.center
        current_center = match.detection.centroid
        track.velocity = (
            (current_center[0] - previous_center[0]) / match.frame_gap,
            (current_center[1] - previous_center[1]) / match.frame_gap,
        )
        track.last_detection = match.detection
        track.last_frame_id = meta.frame_id
        was_occluded = track.missed > 0 or previous_state == TrackState.OCCLUDED
        track.missed = 0
        track.hits += 1
        track.confirmed = track.confirmed or track.hits >= self.config.min_confirmed_hits
        if was_occluded:
            next_state = TrackState.REACQUIRED if track.confirmed else TrackState.DETECTED
        elif track.counted:
            next_state = TrackState.COUNTED
        elif track.confirmed:
            next_state = TrackState.TRACKING
        else:
            next_state = TrackState.DETECTED
        track.state = next_state
        return TrackObservation(
            track_id=track.track_id,
            state=next_state,
            meta=meta,
            bbox_xyxy=match.detection.bbox_xyxy,
            mask_polygon=match.detection.mask_polygon,
            mask_confidence=match.detection.confidence,
            visibility=match.detection.confidence,
            predicted_centroid=self._predicted_center(track, match.frame_gap),
            counted=track.counted,
            confirmed=track.confirmed,
            detection_id=match.detection.detection_id,
            previous_state=previous_state,
            reassociation_motion_score=match.motion_score if was_occluded else None,
            reassociation_size_score=match.size_score if was_occluded else None,
        )

    def _apply_miss(self, track: _Track, meta: FrameMeta) -> TrackObservation:
        frame_gap = meta.frame_id - track.last_frame_id
        track.missed = meta.frame_id - track.last_frame_id
        previous_state = track.state
        predicted = self._predicted_center(track, frame_gap)
        if track.missed > self.config.max_age_frames:
            track.state = TrackState.LOST
        else:
            track.state = TrackState.OCCLUDED
        return TrackObservation(
            track_id=track.track_id,
            state=track.state,
            meta=meta,
            bbox_xyxy=track.last_detection.bbox_xyxy,
            mask_polygon=None,
            mask_confidence=None,
            visibility=0.0,
            predicted_centroid=predicted,
            counted=track.counted,
            confirmed=track.confirmed,
            previous_state=previous_state,
        )

    def _new_track(self, detection: Detection, frame_id: int) -> _Track:
        track = _Track(
            track_id=f"battery-{self._next_id:04d}",
            last_detection=detection,
            last_frame_id=frame_id,
        )
        self._next_id += 1
        self._tracks[track.track_id] = track
        return track

    @staticmethod
    def _observation_for_new_track(track: _Track, meta: FrameMeta) -> TrackObservation:
        return TrackObservation(
            track_id=track.track_id,
            state=track.state,
            meta=meta,
            bbox_xyxy=track.last_detection.bbox_xyxy,
            mask_polygon=track.last_detection.mask_polygon,
            mask_confidence=track.last_detection.confidence,
            visibility=track.last_detection.confidence,
            predicted_centroid=track.center,
            counted=track.counted,
            confirmed=track.confirmed,
            detection_id=track.last_detection.detection_id,
        )

    def _predicted_center(self, track: _Track, frame_gap: int) -> Point:
        return (
            track.center[0] + track.velocity[0] * frame_gap,
            track.center[1] + track.velocity[1] * frame_gap,
        )

    def _motion_score(self, predicted: Point, observed: Point) -> float:
        distance = hypot(predicted[0] - observed[0], predicted[1] - observed[1])
        return max(0.0, 1.0 - distance / self.config.max_match_distance_px)

    @staticmethod
    def _size_score(previous: Point, observed: Point) -> float:
        width_score = min(previous[0] / observed[0], observed[0] / previous[0])
        height_score = min(previous[1] / observed[1], observed[1] / previous[1])
        return max(0.0, min(1.0, (width_score + height_score) / 2))
