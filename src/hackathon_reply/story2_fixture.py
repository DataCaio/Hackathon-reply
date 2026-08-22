"""Small deterministic replay fixture for User Story 2 and the demo backup path."""

from __future__ import annotations

from hackathon_reply.contracts import Detection, FrameMeta, ReplayFrame, VolumeEstimate

FRAME_WIDTH = 400
FRAME_HEIGHT = 200


def meta(frame_id: int) -> FrameMeta:
    return FrameMeta(
        video_id="story2-fixture",
        resolution="720p",
        frame_id=frame_id,
        timestamp_ms=frame_id * 100,
        width=FRAME_WIDTH,
        height=FRAME_HEIGHT,
        camera_id="camera-fixture",
    )


def detection(
    detection_id: int,
    center_x: float,
    center_y: float,
    *,
    width: float = 32,
    height: float = 18,
    confidence: float = 0.95,
) -> Detection:
    return Detection(
        detection_id=detection_id,
        bbox_xyxy=(
            center_x - width / 2,
            center_y - height / 2,
            center_x + width / 2,
            center_y + height / 2,
        ),
        mask_polygon=[],
        confidence=confidence,
    )


def valid_volume(volume_l: float = 5.0) -> VolumeEstimate:
    return VolumeEstimate(
        volume_l=volume_l,
        volume_ci95_l=(volume_l - 0.2, volume_l + 0.2),
        volume_confidence=0.9,
    )


def acceptance_fixture() -> tuple[ReplayFrame, ...]:
    """A crosses after occlusion, B approaches without crossing, C is a false positive."""

    frames: list[ReplayFrame] = []
    for frame_id in range(10):
        detections: list[Detection] = []
        estimates: dict[int, VolumeEstimate] = {}

        a_centers = {0: 80, 1: 120, 2: 160, 5: 220, 6: 250, 7: 280, 9: 310}
        if frame_id in a_centers:
            item = detection(100 + frame_id, a_centers[frame_id], 50)
            detections.append(item)
            estimates[item.detection_id] = valid_volume()

        b_centers = {0: 80, 1: 110, 2: 140, 3: 165, 4: 180, 5: 185, 6: 185}
        if frame_id in b_centers:
            item = detection(200 + frame_id, b_centers[frame_id], 150)
            detections.append(item)
            estimates[item.detection_id] = valid_volume(4.0)

        if frame_id in (0, 1):
            item = detection(300 + frame_id, 60 + frame_id * 20, 100)
            detections.append(item)
            estimates[item.detection_id] = valid_volume(3.0)

        frames.append(
            ReplayFrame(meta=meta(frame_id), detections=tuple(detections), volume_estimates=estimates)
        )
    return tuple(frames)


def reverse_crossing_fixture() -> tuple[ReplayFrame, ...]:
    frames: list[ReplayFrame] = []
    for frame_id, center_x in enumerate((320, 280, 240, 160, 120)):
        item = detection(500 + frame_id, center_x, 50)
        frames.append(
            ReplayFrame(
                meta=meta(frame_id),
                detections=(item,),
                volume_estimates={item.detection_id: valid_volume()},
            )
        )
    return tuple(frames)
