"""Probabilistic catalog matching and catalog-derived volume uncertainty."""

from __future__ import annotations

from dataclasses import dataclass
from math import exp, log, log1p

from hackathon_reply.catalog.catalog import CatalogEntry
from hackathon_reply.contracts import CatalogCandidate, FrameMeasurement, TrackEstimate


@dataclass(frozen=True)
class MatcherConfig:
    measurement_sigma_mm: float = 5.0
    unique_probability: float = 0.8
    ambiguity_margin: float = 0.15

    def __post_init__(self) -> None:
        if self.measurement_sigma_mm <= 0:
            raise ValueError("measurement_sigma_mm must be positive")
        if not 0 < self.unique_probability <= 1:
            raise ValueError("unique_probability must be within (0, 1]")
        if not 0 <= self.ambiguity_margin <= 1:
            raise ValueError("ambiguity_margin must be within 0..1")


class CatalogMatcher:
    def __init__(self, entries: tuple[CatalogEntry, ...], config: MatcherConfig | None = None) -> None:
        if not entries:
            raise ValueError("catalog matcher requires at least one entry")
        self.entries = entries
        self.config = config or MatcherConfig()
        self._log_evidence: dict[str, dict[str, float]] = {}
        self._quality: dict[str, float] = {}

    def update(self, track_id: str, measurement: FrameMeasurement) -> TrackEstimate:
        if not measurement.usable or not measurement.calibration_validated:
            return TrackEstimate(
                track_id=track_id,
                catalog_candidates=(),
                catalog_id=None,
                ambiguous=False,
                length_mm=None,
                width_mm=None,
                volume_l=None,
                volume_ci95_l=None,
                volume_confidence=0.0,
                physical_validated=measurement.calibration_validated,
                warning=measurement.warning or "physical measurement unavailable",
            )

        evidence = self._log_evidence.setdefault(track_id, {entry.catalog_id: 0.0 for entry in self.entries})
        sigma = max(self.config.measurement_sigma_mm, measurement.geometry_uncertainty_mm or 0.0)
        for entry in self.entries:
            direct_error = _squared_error(measurement.length_mm or 0.0, measurement.width_mm or 0.0, entry.length_mm, entry.width_mm)
            swapped_error = _squared_error(measurement.length_mm or 0.0, measurement.width_mm or 0.0, entry.width_mm, entry.length_mm)
            likelihood_log = -0.5 * min(direct_error, swapped_error) / (sigma * sigma)
            evidence[entry.catalog_id] += measurement.quality * likelihood_log
        self._quality[track_id] = min(1.0, self._quality.get(track_id, 0.0) + measurement.quality)
        probabilities = _softmax([evidence[entry.catalog_id] for entry in self.entries])
        candidates = tuple(
            CatalogCandidate(
                catalog_id=entry.catalog_id,
                length_mm=entry.length_mm,
                width_mm=entry.width_mm,
                height_mm=entry.height_mm,
                categories=entry.categories,
                probability=probability,
                volume_l=entry.volume_l,
            )
            for entry, probability in zip(self.entries, probabilities)
        )
        ranked = sorted(candidates, key=lambda candidate: (-candidate.probability, candidate.catalog_id))
        top = ranked[0]
        second_probability = ranked[1].probability if len(ranked) > 1 else 0.0
        ambiguous = len(ranked) > 1 and (
            top.probability < self.config.unique_probability
            or top.probability - second_probability < self.config.ambiguity_margin
        )
        volume_l = sum(candidate.probability * candidate.volume_l for candidate in candidates)
        interval = _credible_interval(candidates)
        confidence = self._confidence(probabilities, self._quality[track_id])
        return TrackEstimate(
            track_id=track_id,
            catalog_candidates=candidates,
            catalog_id=None if ambiguous else top.catalog_id,
            ambiguous=ambiguous,
            length_mm=measurement.length_mm,
            width_mm=measurement.width_mm,
            volume_l=volume_l,
            volume_ci95_l=interval,
            volume_confidence=confidence,
            physical_validated=True,
        )

    @staticmethod
    def _confidence(probabilities: list[float], quality: float) -> float:
        if len(probabilities) == 1:
            return quality
        entropy = -sum(probability * log(max(probability, 1e-15)) for probability in probabilities)
        normalized_entropy = entropy / log(len(probabilities))
        return max(0.0, min(1.0, quality * (1.0 - normalized_entropy)))


def _squared_error(length: float, width: float, candidate_length: float, candidate_width: float) -> float:
    return (length - candidate_length) ** 2 + (width - candidate_width) ** 2


def _softmax(log_values: list[float]) -> list[float]:
    maximum = max(log_values)
    values = [exp(value - maximum) for value in log_values]
    total = sum(values)
    return [value / total for value in values]


def _credible_interval(candidates: tuple[CatalogCandidate, ...]) -> tuple[float, float]:
    ordered = sorted(candidates, key=lambda candidate: candidate.volume_l)
    return (_posterior_quantile(ordered, 0.025), _posterior_quantile(ordered, 0.975))


def _posterior_quantile(candidates: list[CatalogCandidate], quantile: float) -> float:
    cumulative = 0.0
    for candidate in candidates:
        cumulative += candidate.probability
        if cumulative >= quantile:
            return candidate.volume_l
    return candidates[-1].volume_l
