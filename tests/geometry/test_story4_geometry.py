from __future__ import annotations

import math

import pytest

from hackathon_reply.contracts import FrameMeta, TrackObservation, TrackState
from hackathon_reply.geometry.calibration import PlanarCalibration
from hackathon_reply.geometry.measurement import GeometryEstimator


def observation(polygon: list[tuple[float, float]], confidence: float = 1.0) -> TrackObservation:
    xs = [point[0] for point in polygon] or [0.0, 1.0]
    ys = [point[1] for point in polygon] or [0.0, 1.0]
    return TrackObservation(
        track_id="battery-0001",
        state=TrackState.TRACKING,
        meta=FrameMeta("story4", "720p", 0, 0, 400, 300, "camera-fixture"),
        bbox_xyxy=(min(xs), min(ys), max(xs), max(ys)),
        mask_polygon=polygon,
        mask_confidence=confidence,
        visibility=1.0,
        predicted_centroid=(sum(xs) / len(xs), sum(ys) / len(ys)),
        confirmed=True,
    )


def rotated_rectangle(
    center: tuple[float, float], length: float, width: float, angle_degrees: float
) -> list[tuple[float, float]]:
    cx, cy = center
    angle = math.radians(angle_degrees)
    ux, uy = math.cos(angle), math.sin(angle)
    vx, vy = -uy, ux
    return [
        (cx + sx * length / 2 * ux + sy * width / 2 * vx, cy + sx * length / 2 * uy + sy * width / 2 * vy)
        for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))
    ]


def test_four_reference_points_are_reprojected_within_tolerance() -> None:
    calibration = PlanarCalibration.from_correspondences(
        pixel_points=((0, 0), (100, 0), (100, 50), (0, 50)),
        physical_points=((0, 0), (200, 0), (200, 100), (0, 100)),
        source="calibration-fixture",
        rmse_tolerance_mm=0.01,
    )

    assert calibration.trusted is True
    assert calibration.reprojection_rmse_mm == pytest.approx(0.0)
    assert calibration.map_point((50, 25)) == pytest.approx((100, 50))


def test_rotated_mask_recovers_orientation_invariant_physical_dimensions() -> None:
    calibration = PlanarCalibration.from_scale(2.0, source="trusted-ruler")
    measurement = GeometryEstimator(calibration).measure(
        observation(rotated_rectangle((200, 150), 40, 20, 37))
    )

    assert sorted((measurement.length_mm, measurement.width_mm)) == pytest.approx([40.0, 80.0])
    assert measurement.calibration_validated is True
    assert measurement.quality > 0.8


def test_untrusted_calibration_and_invalid_masks_remain_explicit() -> None:
    fallback = PlanarCalibration.from_scale(2.0, source="pixel-only-fallback", trusted=False)
    result = GeometryEstimator(fallback).measure(
        observation(rotated_rectangle((200, 150), 40, 20, 0))
    )
    invalid = GeometryEstimator(fallback).measure(observation([]))

    assert result.length_mm is None
    assert result.width_mm is None
    assert result.pixel_length_px is not None
    assert result.warning == "physical calibration unavailable"
    assert invalid.quality == 0.0
    assert invalid.length_mm is None
