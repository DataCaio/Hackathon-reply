"""Mask-to-dimension measurement with quality and calibration evidence."""

from __future__ import annotations

from dataclasses import dataclass
from math import atan2, cos, isfinite, sin

from hackathon_reply.contracts import FrameMeasurement, Point, TrackObservation
from hackathon_reply.contracts.domain import FrameMeasurement as US1FrameMeasurement
from hackathon_reply.geometry.calibration import PhysicalCalibration, PlanarCalibration


@dataclass(frozen=True)
class MeasurementConfig:
    min_mask_area_px: float = 10.0
    stability_change_fraction: float = 0.25
    boundary_quality_factor: float = 0.35


class GeometryEstimator:
    def __init__(self, calibration: PlanarCalibration, config: MeasurementConfig | None = None) -> None:
        self.calibration = calibration
        self.config = config or MeasurementConfig()
        self._best_measurements: dict[str, FrameMeasurement] = {}

    def measure(self, observation: TrackObservation) -> FrameMeasurement:
        polygon = observation.mask_polygon or []
        if len(polygon) < 3:
            return self._unusable(observation, "invalid mask")
        pixel_area = abs(_polygon_area(polygon))
        if pixel_area < self.config.min_mask_area_px:
            return self._unusable(observation, "invalid mask")
        pixel_length, pixel_width, _ = _minimum_area_dimensions(polygon)
        if pixel_length <= 0 or pixel_width <= 0:
            return self._unusable(observation, "invalid mask")

        contour_quality = min(1.0, pixel_area / (pixel_length * pixel_width))
        quality = max(0.0, min(1.0, (observation.mask_confidence or 0.0) * observation.visibility * contour_quality))
        boundary_truncated = any(
            point[0] <= 0
            or point[1] <= 0
            or point[0] >= observation.meta.width - 1
            or point[1] >= observation.meta.height - 1
            for point in polygon
        )
        if boundary_truncated:
            quality *= self.config.boundary_quality_factor

        physical_points = [self.calibration.map_point(point) for point in polygon]
        if self.calibration.trusted:
            length, width, _ = _minimum_area_dimensions(physical_points)
            warning = "mask truncated at frame boundary" if boundary_truncated else None
            uncertainty = max(0.5, max(length, width) * (1.0 - quality) * 0.1)
            measurement = FrameMeasurement(
                track_id=observation.track_id,
                frame_id=observation.meta.frame_id,
                length_mm=length,
                width_mm=width,
                geometry_uncertainty_mm=uncertainty,
                quality=quality,
                pixel_length_px=pixel_length,
                pixel_width_px=pixel_width,
                calibration_validated=True,
                boundary_truncated=boundary_truncated,
                warning=warning,
            )
        else:
            measurement = FrameMeasurement(
                track_id=observation.track_id,
                frame_id=observation.meta.frame_id,
                length_mm=None,
                width_mm=None,
                geometry_uncertainty_mm=None,
                quality=quality,
                pixel_length_px=pixel_length,
                pixel_width_px=pixel_width,
                calibration_validated=False,
                boundary_truncated=boundary_truncated,
                warning="physical calibration unavailable",
            )
        measurement = self._apply_stability(measurement)
        previous = self._best_measurements.get(observation.track_id)
        if previous is None or measurement.quality >= previous.quality:
            self._best_measurements[observation.track_id] = measurement
        return measurement

    def best_measurement(self, track_id: str) -> FrameMeasurement | None:
        return self._best_measurements.get(track_id)

    def _apply_stability(self, measurement: FrameMeasurement) -> FrameMeasurement:
        previous = self._best_measurements.get(measurement.track_id)
        if previous is None or measurement.length_mm is None or previous.length_mm is None:
            return measurement
        change = max(
            abs(measurement.length_mm - previous.length_mm) / previous.length_mm,
            abs((measurement.width_mm or 0) - (previous.width_mm or 0)) / (previous.width_mm or 1),
        )
        stability = max(0.0, 1.0 - change / self.config.stability_change_fraction)
        return FrameMeasurement(
            track_id=measurement.track_id,
            frame_id=measurement.frame_id,
            length_mm=measurement.length_mm,
            width_mm=measurement.width_mm,
            geometry_uncertainty_mm=measurement.geometry_uncertainty_mm,
            quality=measurement.quality * stability,
            pixel_length_px=measurement.pixel_length_px,
            pixel_width_px=measurement.pixel_width_px,
            calibration_validated=measurement.calibration_validated,
            boundary_truncated=measurement.boundary_truncated,
            warning=measurement.warning,
        )

    @staticmethod
    def _unusable(observation: TrackObservation, warning: str) -> FrameMeasurement:
        return FrameMeasurement(
            track_id=observation.track_id,
            frame_id=observation.meta.frame_id,
            length_mm=None,
            width_mm=None,
            geometry_uncertainty_mm=None,
            quality=0.0,
            calibration_validated=False,
            warning=warning,
        )


def _polygon_area(points: list[Point]) -> float:
    return 0.5 * abs(
        sum(
            point[0] * points[(index + 1) % len(points)][1]
            - points[(index + 1) % len(points)][0] * point[1]
            for index, point in enumerate(points)
        )
    )


def _minimum_area_dimensions(points: list[Point]) -> tuple[float, float, float]:
    best_area = float("inf")
    best_dimensions = (0.0, 0.0)
    for index, point in enumerate(points):
        next_point = points[(index + 1) % len(points)]
        angle = atan2(next_point[1] - point[1], next_point[0] - point[0])
        ux, uy = cos(angle), sin(angle)
        vx, vy = -uy, ux
        projections_u = [candidate[0] * ux + candidate[1] * uy for candidate in points]
        projections_v = [candidate[0] * vx + candidate[1] * vy for candidate in points]
        length = max(projections_u) - min(projections_u)
        width = max(projections_v) - min(projections_v)
        area = length * width
        if area < best_area:
            best_area = area
            best_dimensions = (max(length, width), min(length, width))
    return best_dimensions[0], best_dimensions[1], best_area


def measure_bbox(
    *,
    track_id: str,
    frame_id: int,
    bbox_xyxy: tuple[float, float, float, float],
    mask_confidence: float | None,
    visibility: float,
    calibration: PhysicalCalibration,
) -> US1FrameMeasurement:
    """Measure a replay bounding box and preserve missing physical evidence."""

    x_min, y_min, x_max, y_max = bbox_xyxy
    width_px = float(x_max) - float(x_min)
    height_px = float(y_max) - float(y_min)
    if width_px <= 0 or height_px <= 0:
        return US1FrameMeasurement(track_id, frame_id, None, None, None, 0.0)
    confidence = 0.0 if mask_confidence is None else max(0.0, min(1.0, float(mask_confidence)))
    quality = confidence * max(0.0, min(1.0, float(visibility)))
    if not calibration.trusted:
        return US1FrameMeasurement(track_id, frame_id, None, None, None, quality)
    assert calibration.mm_per_pixel_x is not None
    assert calibration.mm_per_pixel_y is not None
    width_mm = width_px * calibration.mm_per_pixel_x
    height_mm = height_px * calibration.mm_per_pixel_y
    length_mm = max(width_mm, height_mm)
    short_mm = min(width_mm, height_mm)
    uncertainty = max(0.01, (1.0 - quality) * max(length_mm, short_mm) * 0.05)
    if not all(isfinite(value) and value > 0 for value in (length_mm, short_mm, uncertainty)):
        return US1FrameMeasurement(track_id, frame_id, None, None, None, 0.0)
    return US1FrameMeasurement(track_id, frame_id, length_mm, short_mm, uncertainty, quality)
