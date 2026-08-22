"""Deterministic uncertainty calculations for catalog-constrained volume."""

from __future__ import annotations

from math import fsum

from hackathon_reply.contracts.domain import CatalogCandidate, VolumeEstimate

_MM3_PER_LITER = 1_000_000.0


def _volume_l(length_mm: float, width_mm: float, height_mm: float) -> float:
    return (length_mm * width_mm * height_mm) / _MM3_PER_LITER


def _normalized_candidates(candidates: tuple[CatalogCandidate, ...]) -> tuple[CatalogCandidate, ...]:
    if not candidates:
        return ()
    total = sum(max(0.0, candidate.probability) for candidate in candidates)
    denominator = total if total > 0 else float(len(candidates))
    return tuple(
        CatalogCandidate(
            catalog_id=candidate.catalog_id,
            length_mm=candidate.length_mm,
            width_mm=candidate.width_mm,
            height_mm=candidate.height_mm,
            probability=(max(0.0, candidate.probability) / denominator) if total > 0 else 1.0 / denominator,
            categories=candidate.categories,
        )
        for candidate in candidates
    )


def estimate_volume(
    candidates: tuple[CatalogCandidate, ...] | list[CatalogCandidate],
    measurement_error_mm: float,
    *,
    physical_validated: bool = True,
) -> VolumeEstimate:
    """Return a weighted expected volume and auditable candidate/error bounds.

    The catalog candidate interval and the independent per-dimension
    measurement error are both represented.  The calculation is deliberately
    deterministic so replay does not depend on model or platform randomness.
    """

    normalized = _normalized_candidates(tuple(candidates))
    if not normalized or measurement_error_mm < 0:
        return VolumeEstimate(None, None, 0.0, normalized, physical_validated=False)
    error = float(measurement_error_mm)
    expected = fsum(
        candidate.probability * _volume_l(candidate.length_mm, candidate.width_mm, candidate.height_mm)
        for candidate in normalized
    )
    lower_values: list[float] = []
    upper_values: list[float] = []
    for candidate in normalized:
        lower_values.append(
            _volume_l(
                max(0.001, candidate.length_mm - error),
                max(0.001, candidate.width_mm - error),
                max(0.001, candidate.height_mm - error),
            )
        )
        upper_values.append(
            _volume_l(
                candidate.length_mm + error,
                candidate.width_mm + error,
                candidate.height_mm + error,
            )
        )
    lower = min(lower_values)
    upper = max(upper_values)
    # Candidate volumes are positive by contract, but guard against future
    # changes to the arithmetic before constructing the stricter domain value.
    if expected <= 0 or lower <= 0 or upper < lower:
        return VolumeEstimate(None, None, 0.0, normalized, physical_validated=False)
    confidence = max(candidate.probability for candidate in normalized)
    return VolumeEstimate(
        expected_volume_l=expected,
        uncertainty_interval_l=(lower, max(upper, expected)),
        confidence=confidence,
        candidates=normalized,
        physical_validated=physical_validated,
    )
