"""Trusted planar calibration and explicitly marked pixel-scale fallback."""

from __future__ import annotations

from dataclasses import dataclass
from math import hypot, isfinite

from hackathon_reply.contracts import Point


@dataclass(frozen=True)
class PlanarCalibration:
    coefficients: tuple[float, float, float, float, float, float, float, float]
    trusted: bool
    source: str
    reprojection_rmse_mm: float | None

    @classmethod
    def from_scale(
        cls,
        mm_per_pixel: float | tuple[float, float],
        *,
        source: str,
        trusted: bool = True,
    ) -> "PlanarCalibration":
        if isinstance(mm_per_pixel, tuple):
            sx, sy = mm_per_pixel
        else:
            sx = sy = mm_per_pixel
        if sx <= 0 or sy <= 0 or not isfinite(sx) or not isfinite(sy):
            raise ValueError("mm_per_pixel must contain positive finite values")
        if not source:
            raise ValueError("calibration source is required")
        return cls((sx, 0.0, 0.0, 0.0, sy, 0.0, 0.0, 0.0), trusted, source, 0.0)

    @classmethod
    def from_correspondences(
        cls,
        pixel_points: tuple[Point, ...],
        physical_points: tuple[Point, ...],
        *,
        source: str,
        rmse_tolerance_mm: float,
        trusted: bool = True,
    ) -> "PlanarCalibration":
        if len(pixel_points) != len(physical_points) or len(pixel_points) < 4:
            raise ValueError("planar calibration requires at least four point correspondences")
        if rmse_tolerance_mm <= 0 or not source:
            raise ValueError("calibration tolerance and source are required")
        rows: list[list[float]] = []
        values: list[float] = []
        for (x, y), (X, Y) in zip(pixel_points, physical_points):
            rows.append([x, y, 1.0, 0.0, 0.0, 0.0, -X * x, -X * y])
            values.append(X)
            rows.append([0.0, 0.0, 0.0, x, y, 1.0, -Y * x, -Y * y])
            values.append(Y)
        coefficients = tuple(_solve_linear_system(rows, values))
        calibration = cls(coefficients, trusted, source, None)
        errors = []
        for pixel, physical in zip(pixel_points, physical_points):
            mapped = calibration.map_point(pixel)
            errors.append(hypot(mapped[0] - physical[0], mapped[1] - physical[1]))
        rmse = (sum(error * error for error in errors) / len(errors)) ** 0.5
        return cls(coefficients, trusted and rmse <= rmse_tolerance_mm, source, rmse)

    @property
    def physical_supported(self) -> bool:
        return self.trusted

    def map_point(self, point: Point) -> Point:
        x, y = point
        h00, h01, h02, h10, h11, h12, h20, h21 = self.coefficients
        denominator = h20 * x + h21 * y + 1.0
        if denominator == 0 or not isfinite(denominator):
            raise ValueError("calibration maps point to an invalid projective coordinate")
        mapped = (
            (h00 * x + h01 * y + h02) / denominator,
            (h10 * x + h11 * y + h12) / denominator,
        )
        if not all(isfinite(value) for value in mapped):
            raise ValueError("calibration produced a non-finite coordinate")
        return mapped


def _solve_linear_system(matrix: list[list[float]], values: list[float]) -> list[float]:
    size = len(values)
    augmented = [row[:] + [value] for row, value in zip(matrix, values)]
    for column in range(size):
        pivot = max(range(column, size), key=lambda row: abs(augmented[row][column]))
        if abs(augmented[pivot][column]) < 1e-12:
            raise ValueError("calibration points are degenerate")
        augmented[column], augmented[pivot] = augmented[pivot], augmented[column]
        divisor = augmented[column][column]
        augmented[column] = [value / divisor for value in augmented[column]]
        for row in range(size):
            if row == column:
                continue
            factor = augmented[row][column]
            if factor:
                augmented[row] = [
                    current - factor * pivot_value
                    for current, pivot_value in zip(augmented[row], augmented[column])
                ]
    return [augmented[row][-1] for row in range(size)]
