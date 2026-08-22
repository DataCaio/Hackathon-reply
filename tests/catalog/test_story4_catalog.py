from __future__ import annotations

import pytest

from hackathon_reply.catalog.catalog import CatalogLoader
from hackathon_reply.catalog.matcher import CatalogMatcher, MatcherConfig
from hackathon_reply.contracts import FrameMeasurement

CSV = """length_mm;width_mm;height_mm;category
197;130;225;starter
197;130;225;deep-cycle
50,0;100,0;95,50;compact
bad;20;30;invalid-number
0;20;30;invalid-dimension
"""


def measurement(length: float | None, width: float | None, quality: float = 1.0) -> FrameMeasurement:
    return FrameMeasurement(
        track_id="battery-0001",
        frame_id=4,
        length_mm=length,
        width_mm=width,
        geometry_uncertainty_mm=2.0 if length is not None else None,
        quality=quality,
    )


def test_catalog_normalizes_locale_decimals_collapses_dimensions_and_reports_rejections() -> None:
    result = CatalogLoader.from_csv_text(CSV)

    assert len(result.entries) == 2
    assert len(result.rejected_rows) == 2
    duplicate = next(entry for entry in result.entries if entry.length_mm == 197.0)
    assert set(duplicate.categories) == {"starter", "deep-cycle"}
    assert duplicate.catalog_id == CatalogLoader.from_csv_text(CSV).entries[0].catalog_id
    locale_entry = next(entry for entry in result.entries if entry.height_mm == 95.5)
    assert (locale_entry.length_mm, locale_entry.width_mm) == (50.0, 100.0)


def test_catalog_matching_treats_length_and_width_as_equivalent() -> None:
    entries = CatalogLoader.from_csv_text(CSV).entries
    config = MatcherConfig(measurement_sigma_mm=8.0, unique_probability=0.7, ambiguity_margin=0.1)
    first = CatalogMatcher(entries, config).update("battery-0001", measurement(197, 130))
    second = CatalogMatcher(entries, config).update("battery-0001", measurement(130, 197))

    assert [candidate.probability for candidate in first.catalog_candidates] == pytest.approx(
        [candidate.probability for candidate in second.catalog_candidates]
    )
    assert first.volume_l == pytest.approx(197 * 130 * 225 / 1_000_000)
    assert first.volume_ci95_l[0] <= first.volume_l <= first.volume_ci95_l[1]


def test_ambiguous_catalog_evidence_remains_ambiguous() -> None:
    entries = CatalogLoader.from_csv_text(
        "length_mm;width_mm;height_mm;category\n100;50;10;A\n102;49;10;B\n"
    ).entries
    estimate = CatalogMatcher(
        entries,
        MatcherConfig(measurement_sigma_mm=10.0, unique_probability=0.95, ambiguity_margin=0.2),
    ).update("battery-0001", measurement(101, 49.5))

    assert estimate.ambiguous is True
    assert estimate.catalog_id is None
    assert len(estimate.catalog_candidates) == 2
    assert sum(candidate.probability for candidate in estimate.catalog_candidates) == pytest.approx(1.0)


def test_missing_physical_measurement_has_no_invented_volume() -> None:
    entries = CatalogLoader.from_csv_text("length_mm;width_mm;height_mm;category\n100;50;10;A\n").entries
    estimate = CatalogMatcher(entries).update("battery-0001", measurement(None, None, quality=0.0))

    assert estimate.volume_l is None
    assert estimate.volume_ci95_l is None
    assert estimate.volume_confidence == 0.0
