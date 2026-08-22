from __future__ import annotations

import pytest

from hackathon_reply.contracts.domain import FrameMeasurement
from hackathon_reply.geometry import calibration, measurement


def test_untrusted_calibration_keeps_physical_measurement_unvalidated() -> None:
    assert hasattr(calibration, "PhysicalCalibration")
    assert hasattr(measurement, "measure_bbox")
    physical = calibration.PhysicalCalibration.untrusted()
    result = measurement.measure_bbox(
        track_id="battery-0001",
        frame_id=0,
        bbox_xyxy=(10, 20, 50, 80),
        mask_confidence=0.9,
        visibility=1.0,
        calibration=physical,
    )
    assert isinstance(result, FrameMeasurement)
    assert result.length_mm is None
    assert result.width_mm is None


def test_trusted_calibration_converts_frame_dimensions_to_millimeters() -> None:
    physical = calibration.PhysicalCalibration.trusted_from_scale(2.0, 3.0)
    result = measurement.measure_bbox(
        track_id="battery-0001",
        frame_id=0,
        bbox_xyxy=(10, 20, 50, 80),
        mask_confidence=0.9,
        visibility=1.0,
        calibration=physical,
    )
    assert result.length_mm == 180.0
    assert result.width_mm == 80.0
    assert result.quality > 0


def test_reference_calibration_rejects_nonfinite_or_mismatched_evidence() -> None:
    with pytest.raises(calibration.CalibrationError):
        calibration.PhysicalCalibration.from_reference_points(
            ((0.0, 0.0), (1.0, 0.0), (1.0, float("nan")), (0.0, 1.0)),
            ((0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)),
            mm_per_pixel_x=1.0,
            mm_per_pixel_y=1.0,
        )
