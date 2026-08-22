"""Explicit, case-sensitive paired-video manifest and leakage checks."""

from __future__ import annotations

from dataclasses import dataclass
from math import isclose


@dataclass(frozen=True)
class VideoPair:
    video_id: str
    physical_video_id: str
    video_1080: str
    video_720: str
    partition: str
    frame_count_1080: int
    frame_count_720: int
    duration_s_1080: float
    duration_s_720: float
    fps_1080: float
    fps_720: float
    camera_id: str

    def validate(self) -> None:
        if not all((self.video_id, self.physical_video_id, self.video_1080, self.video_720, self.camera_id)):
            raise ValueError("video pair requires explicit IDs, filenames, and camera")
        if self.video_1080 == self.video_720:
            raise ValueError("paired resolutions require distinct explicit filenames")
        if self.partition not in {"train", "validation", "test"}:
            raise ValueError("partition must be train, validation, or test")
        if self.frame_count_1080 <= 0 or self.frame_count_720 <= 0:
            raise ValueError("frame counts must be positive")
        if self.fps_1080 <= 0 or self.fps_720 <= 0 or self.duration_s_1080 <= 0 or self.duration_s_720 <= 0:
            raise ValueError("durations and frame rates must be positive")
        if self.frame_count_1080 != self.frame_count_720:
            raise ValueError("paired videos must have equal frame counts")
        if not isclose(
            self.duration_s_1080,
            self.duration_s_720,
            rel_tol=0.0,
            abs_tol=1 / min(self.fps_1080, self.fps_720),
        ):
            raise ValueError("paired videos must have aligned duration")
        if not isclose(self.fps_1080, self.fps_720, rel_tol=0.0, abs_tol=1e-6):
            raise ValueError("paired videos must have aligned frame rates")


@dataclass(frozen=True)
class DatasetManifest:
    pairs: tuple[VideoPair, ...]

    def validate(self) -> None:
        if not self.pairs:
            raise ValueError("dataset manifest cannot be empty")
        ids: set[str] = set()
        filenames: set[str] = set()
        casefolded_filenames: set[str] = set()
        for pair in self.pairs:
            pair.validate()
            if pair.video_id in ids:
                raise ValueError(f"duplicate video_id {pair.video_id}")
            ids.add(pair.video_id)
            for filename in (pair.video_1080, pair.video_720):
                if filename in filenames:
                    raise ValueError(f"duplicate filename {filename}")
                if filename.casefold() in casefolded_filenames:
                    raise ValueError("filenames that differ only by case are ambiguous")
                filenames.add(filename)
                casefolded_filenames.add(filename.casefold())

        expected_partitions = {
            "video_01": "train",
            "video_02": "train",
            "video_03": "train",
            "video_04": "validation",
            "video_05": "test",
        }
        missing = set(expected_partitions).difference(ids)
        if missing:
            raise ValueError(f"manifest is missing required explicit pairs: {sorted(missing)}")
        for video_id, partition in expected_partitions.items():
            pair = next(candidate for candidate in self.pairs if candidate.video_id == video_id)
            if pair.partition != partition:
                raise ValueError(f"{video_id} must be in the {partition} partition")

    def pair_for(self, video_id: str) -> VideoPair:
        try:
            return next(pair for pair in self.pairs if pair.video_id == video_id)
        except StopIteration as error:
            raise KeyError(video_id) from error

    def partition_of(self, video_id: str) -> str:
        return self.pair_for(video_id).partition
