"""Traceable golden-set evidence for measurements, identity, and occlusion."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GoldenTrack:
    track_id: str
    video_id: str
    start_frame: int
    end_frame: int
    occluded_frames: tuple[int, ...]
    counted: bool
    catalog_id: str | None
    volume_l: float | None


@dataclass(frozen=True)
class GoldenSet:
    tracks: tuple[GoldenTrack, ...]
    manual_count: int | None = None

    def validate(self) -> None:
        if not 10 <= len(self.tracks) <= 20:
            raise ValueError("golden set must contain 10..20 traceable tracks")
        ids: set[str] = set()
        for track in self.tracks:
            if not track.track_id.startswith("battery-") or track.track_id in ids:
                raise ValueError("golden tracks require unique operational IDs")
            if not track.video_id or track.start_frame < 0 or track.end_frame < track.start_frame:
                raise ValueError("golden track frame interval is invalid")
            if any(frame < track.start_frame or frame > track.end_frame for frame in track.occluded_frames):
                raise ValueError("occlusion frames must be inside the traceable track interval")
            if track.volume_l is not None and track.volume_l <= 0:
                raise ValueError("golden volume must be positive when supplied")
            ids.add(track.track_id)
        if self.manual_count is not None and self.manual_count < 0:
            raise ValueError("manual count must be non-negative")
