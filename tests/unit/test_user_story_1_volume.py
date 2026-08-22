from __future__ import annotations

from hackathon_reply.catalog import loader, matcher, uncertainty
from hackathon_reply.contracts.domain import CatalogCandidate, FrameMeasurement


def test_catalog_loader_normalizes_decimal_and_collapses_exact_dimensions(tmp_path) -> None:
    path = tmp_path / "catalog.csv"
    path.write_text(
        "L,W,H,category\n100,50,20,A\n100,50,20,B\n100,50,95,50,C\n",
        encoding="utf-8",
    )
    entries, rejected = loader.load_catalog(path)
    assert rejected == ()
    assert len(entries) == 2
    assert entries[0].categories == ("A", "B")
    assert entries[1].height_mm == 95.5


def test_uncertainty_uses_expected_volume_and_candidate_measurement_bounds() -> None:
    candidates = (
        CatalogCandidate("a", 100, 50, 20, 0.75, ("A",)),
        CatalogCandidate("b", 110, 55, 20, 0.25, ("B",)),
    )
    estimate = uncertainty.estimate_volume(candidates, measurement_error_mm=2.0)
    assert estimate.expected_volume_l is not None
    assert estimate.uncertainty_interval_l is not None
    assert estimate.uncertainty_interval_l[0] < estimate.expected_volume_l < estimate.uncertainty_interval_l[1]
    assert len(estimate.candidates) == 2


def test_unvalidated_measurement_cannot_produce_countable_volume() -> None:
    measurement = FrameMeasurement("battery-0001", 0, None, None, None, 0.0)
    assert hasattr(matcher, "estimate_from_measurement")
    estimate = matcher.estimate_from_measurement(measurement, ())
    assert estimate.expected_volume_l is None
    assert estimate.confidence == 0
