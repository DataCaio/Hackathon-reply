from __future__ import annotations

import sys
from pathlib import Path

from hackathon_reply.contracts.serialization import load_summary, validate_run


def test_published_fixture_is_consumable_without_internal_modules(
    fixture_root: Path,
) -> None:
    events_path = fixture_root / "events.jsonl"
    summary_path = fixture_root / "summary.json"
    modules_before = set(sys.modules)
    result = validate_run(events_path, summary_path)

    assert result.event_count >= 20
    assert result.event_types == {
        "TRACK_UPDATE",
        "TRACK_OCCLUDED",
        "BATTERY_COUNTED",
    }
    assert result.counted_track_ids == {"battery-0001"}
    summary = load_summary(summary_path)
    assert any(
        "simulated" in item["message"].lower()
        for item in summary["warnings"]
    )

    forbidden = (
        "detector",
        "tracker",
        "geometry",
        "catalog",
        "pipeline",
        "plc",
    )
    modules_during_consume = set(sys.modules) - modules_before
    assert not any(
        module.startswith("hackathon_reply.")
        and any(part in module.lower() for part in forbidden)
        for module in modules_during_consume
    )
