from __future__ import annotations

from dataclasses import is_dataclass

from hackathon_reply.contracts import domain


def test_domain_exports_frame_and_detection_contracts() -> None:
    assert hasattr(domain, "FrameMeta")
    assert hasattr(domain, "Detection")
    assert is_dataclass(domain.FrameMeta)
    assert is_dataclass(domain.Detection)


def test_domain_exports_track_state_and_volume_contracts() -> None:
    assert hasattr(domain, "TrackState")
    assert {state.value for state in domain.TrackState} == {
        "DETECTED",
        "TRACKING",
        "OCCLUDED",
        "REACQUIRED",
        "COUNTED",
        "LOST",
    }
    assert hasattr(domain, "FrameMeasurement")
    assert hasattr(domain, "CatalogEntry")
    assert hasattr(domain, "CatalogCandidate")
    assert hasattr(domain, "VolumeEstimate")


def test_domain_exports_lot_and_summary_contracts() -> None:
    assert hasattr(domain, "CountGate")
    assert hasattr(domain, "Lot")
    assert hasattr(domain, "RunSummary")
    assert hasattr(domain, "ResolutionComparison")
