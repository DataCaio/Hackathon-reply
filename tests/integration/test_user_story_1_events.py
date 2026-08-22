from __future__ import annotations

import json
from pathlib import Path

from hackathon_reply import pipeline
from hackathon_reply.catalog.loader import load_catalog
from hackathon_reply.contracts.domain import CountGate
from hackathon_reply.geometry.calibration import PhysicalCalibration
from hackathon_reply.io.replay import read_detection_jsonl
from scripts.validate_events import validate

FIXTURES = Path(__file__).parents[1] / "fixtures" / "user_story_1"


def _frames():
    return tuple(read_detection_jsonl(FIXTURES / "detections.jsonl"))


def _catalog():
    return load_catalog(FIXTURES / "catalog.csv")[0]


def test_trusted_fixture_emits_one_count_and_replay_stable_events(tmp_path) -> None:
    summary = pipeline.run_replay(
        _frames(),
        output_path=tmp_path / "trusted.jsonl",
        run_id="trusted-run",
        calibration=PhysicalCalibration.trusted_from_scale(5.0, 2.5),
        catalog_entries=_catalog(),
        count_gate=CountGate((0.5, 0.0), (0.5, 1.0), "entry_to_exit"),
    )
    records = [json.loads(line) for line in (tmp_path / "trusted.jsonl").read_text(encoding="utf-8").splitlines()]
    counted = [record for record in records if record["event"] == "BATTERY_COUNTED"]
    assert summary.status == "completed"
    assert summary.lot_count == 1
    assert len(counted) == 1
    assert len({record.get("track_id") for record in counted}) == 1
    assert all(record["sequence"] == index for index, record in enumerate(records))
    assert validate(tmp_path / "trusted.jsonl")["status"] == "valid"


def test_untrusted_fixture_never_emits_counted_volume(tmp_path) -> None:
    summary = pipeline.run_replay(
        _frames(),
        output_path=tmp_path / "untrusted.jsonl",
        run_id="untrusted-run",
        calibration=PhysicalCalibration.untrusted(),
        catalog_entries=_catalog(),
        count_gate=CountGate((0.5, 0.0), (0.5, 1.0), "entry_to_exit"),
    )
    records = [json.loads(line) for line in (tmp_path / "untrusted.jsonl").read_text(encoding="utf-8").splitlines()]
    assert summary.lot_count == 0
    assert not any(record["event"] == "BATTERY_COUNTED" for record in records)
    assert any("unvalidated" in warning for warning in summary.warnings)
    updates = [record for record in records if record["event"] == "TRACK_UPDATE"]
    assert updates and all(record["length_mm"] is None and record["volume_l"] is None for record in updates)
