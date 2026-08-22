from __future__ import annotations

import pytest

from hackathon_reply.contracts.diagnostics import (
    DIAGNOSTIC_KEYS,
    SUMMARY_KEYS,
    DiagnosticValidationError,
    normalize_summary,
    validate_diagnostic,
    validate_summary,
)


def diagnostic(*, code: str = "SIMULATED_PLC_DISPLAY") -> dict[str, object]:
    return {
        "code": code,
        "message": "PLC-oriented display is simulated; Model Core does not control hardware.",
        "frame_id": None,
        "recoverable": True,
    }


def summary() -> dict[str, object]:
    return {
        "summary_schema_version": 1,
        "video_id": "video_03",
        "resolution": "720p",
        "frames_processed": 8,
        "lot_count": 1,
        "lot_volume_l": 7.94,
        "unique_tracks": 1,
        "counted_track_ids": ["battery-0001"],
        "processing_fps": 30.0,
        "health_status": "HEALTHY",
        "run_status": "COMPLETE",
        "warnings": [diagnostic()],
        "errors": [],
        "replayable": True,
        "replay_evidence_refs": ["events/video_03_720p.jsonl"],
    }


def test_diagnostic_and_summary_use_fixed_keys() -> None:
    assert set(validate_diagnostic(diagnostic())) == DIAGNOSTIC_KEYS
    assert set(validate_summary(summary())) == SUMMARY_KEYS


def test_summary_validates_statuses_lot_invariants_and_version() -> None:
    validate_summary(summary())

    invalid = summary()
    invalid["lot_count"] = 2
    with pytest.raises(DiagnosticValidationError, match="lot_count"):
        validate_summary(invalid)

    invalid_version = summary()
    invalid_version["summary_schema_version"] = 2
    with pytest.raises(DiagnosticValidationError, match="schema"):
        validate_summary(invalid_version)


def test_summary_normalization_removes_runtime_only_fps() -> None:
    first = normalize_summary(summary())
    second = summary()
    second["processing_fps"] = 999.0
    assert first == normalize_summary(second)


def test_complete_summary_cannot_hide_fatal_errors() -> None:
    invalid = summary()
    invalid["errors"] = [diagnostic(code="FATAL_INPUT")]
    with pytest.raises(DiagnosticValidationError, match="COMPLETE"):
        validate_summary(invalid)
