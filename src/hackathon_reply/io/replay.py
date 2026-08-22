"""Cached detection replay input with deterministic frame validation."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

from hackathon_reply.contracts.domain import Detection, FrameMeta


class ReplayError(ValueError):
    """Raised when cached detections cannot be replayed deterministically."""


@dataclass(frozen=True, slots=True)
class ReplayFrame:
    meta: FrameMeta
    detections: tuple[Detection, ...]


def read_detection_jsonl(path: str | Path) -> Iterator[ReplayFrame]:
    """Yield validated cached frames in zero-based monotonic order."""
    expected_frame_id = 0
    previous_timestamp = -1
    source = Path(path)
    with source.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ReplayError(f"invalid JSON at line {line_number}") from exc
            if not isinstance(record, dict):
                raise ReplayError(f"frame record at line {line_number} must be an object")
            try:
                meta = FrameMeta(
                    video_id=str(record["video_id"]),
                    resolution=str(record["resolution"]),
                    frame_id=int(record["frame_id"]),
                    timestamp_ms=int(record["timestamp_ms"]),
                    width=int(record["width"]),
                    height=int(record["height"]),
                    camera_id=str(record["camera_id"]),
                )
                detections = tuple(
                    Detection(
                        detection_id=int(item["detection_id"]),
                        bbox_xyxy=tuple(item["bbox_xyxy"]),
                        mask_polygon=tuple(tuple(point) for point in item["mask_polygon"]),
                        confidence=float(item["confidence"]),
                        class_id=int(item.get("class_id", 0)),
                    )
                    for item in record.get("detections", [])
                )
            except (KeyError, TypeError, ValueError) as exc:
                raise ReplayError(f"invalid frame record at line {line_number}") from exc
            if meta.frame_id != expected_frame_id:
                raise ReplayError(f"frame identifier must start at zero and increment by one; line {line_number}")
            if meta.timestamp_ms < previous_timestamp:
                raise ReplayError(f"timestamp regressed at line {line_number}")
            yield ReplayFrame(meta=meta, detections=detections)
            expected_frame_id += 1
            previous_timestamp = meta.timestamp_ms
