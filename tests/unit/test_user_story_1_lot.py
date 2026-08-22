from __future__ import annotations

from hackathon_reply.contracts.domain import CatalogCandidate, CountGate, VolumeEstimate
from hackathon_reply.counting import gate, lot


def test_directed_gate_crossing_only_allows_entry_to_exit() -> None:
    assert hasattr(gate, "crossed_gate")
    count_gate = CountGate((0.5, 0.0), (0.5, 1.0), "entry_to_exit")
    assert gate.crossed_gate((0.4, 0.5), (0.6, 0.5), count_gate)
    assert not gate.crossed_gate((0.6, 0.5), (0.4, 0.5), count_gate)


def test_lot_freezes_one_ambiguous_expected_volume_per_track() -> None:
    assert hasattr(lot, "LotAccumulator")
    accumulator = lot.LotAccumulator()
    estimate = VolumeEstimate(
        expected_volume_l=1.0,
        uncertainty_interval_l=(0.8, 1.2),
        confidence=0.7,
        candidates=(CatalogCandidate("a", 100, 50, 20, 1.0, ("A",)),),
        physical_validated=True,
    )
    assert accumulator.add("battery-0001", estimate) is True
    assert accumulator.add("battery-0001", estimate) is False
    assert accumulator.lot.count == 1
    assert accumulator.lot.volume_l == 1.0
