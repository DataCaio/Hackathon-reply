"""Detector protocol and replay/live adapters."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from typing import Protocol, runtime_checkable

from hackathon_reply.contracts.domain import Detection, FrameMeta
from hackathon_reply.io.replay import ReplayFrame


class DetectorError(ValueError):
    """Raised when a detector adapter returns an invalid domain result."""


@runtime_checkable
class Detector(Protocol):
    """Project-owned detector boundary; vendor objects stop behind it."""

    def detect(self, meta: FrameMeta, frame: object | None = None) -> tuple[Detection, ...]:
        ...


def _validated_detections(value: Iterable[Detection] | None) -> tuple[Detection, ...]:
    if value is None:
        return ()
    detections = tuple(value)
    if not all(isinstance(item, Detection) for item in detections):
        raise DetectorError("detector adapters must return Detection domain objects")
    return detections


class EmptyDetector:
    """Detector used for an empty or deliberately disabled live source."""

    def detect(self, meta: FrameMeta, frame: object | None = None) -> tuple[Detection, ...]:
        del meta, frame
        return ()


class ReplayDetector:
    """Read cached detections by zero-based frame identifier."""

    def __init__(self, frames: Iterable[ReplayFrame] | Mapping[int, Iterable[Detection]]) -> None:
        by_frame: dict[int, tuple[Detection, ...]] = {}
        if isinstance(frames, Mapping):
            for frame_id, detections in frames.items():
                by_frame[int(frame_id)] = _validated_detections(detections)
        else:
            for replay_frame in frames:
                if not isinstance(replay_frame, ReplayFrame):
                    raise DetectorError("replay detector requires ReplayFrame values")
                by_frame[replay_frame.meta.frame_id] = replay_frame.detections
        self._detections_by_frame = by_frame

    @classmethod
    def from_frames(cls, frames: Iterable[ReplayFrame]) -> "ReplayDetector":
        return cls(frames)

    def detect(self, meta: FrameMeta, frame: object | None = None) -> tuple[Detection, ...]:
        del frame
        return self._detections_by_frame.get(meta.frame_id, ())


class CallableDetector:
    """Adapt a live/vendor callable while exposing only domain detections."""

    def __init__(self, callback: Callable[[FrameMeta, object | None], Iterable[Detection] | None]) -> None:
        self._callback = callback

    def detect(self, meta: FrameMeta, frame: object | None = None) -> tuple[Detection, ...]:
        return _validated_detections(self._callback(meta, frame))


LiveDetectorAdapter = CallableDetector
