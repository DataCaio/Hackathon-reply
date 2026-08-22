"""Versioned run-summary and diagnostics validation for User Story 3."""

from __future__ import annotations

import math
import re
from collections.abc import Mapping
from typing import Any


SUMMARY_SCHEMA_VERSION = 1
SUMMARY_KEYS = frozenset(
    {
        "summary_schema_version",
        "video_id",
        "resolution",
        "frames_processed",
        "lot_count",
        "lot_volume_l",
        "unique_tracks",
        "counted_track_ids",
        "processing_fps",
        "health_status",
        "run_status",
        "warnings",
        "errors",
        "replayable",
        "replay_evidence_refs",
    }
)
DIAGNOSTIC_KEYS = frozenset({"code", "message", "frame_id", "recoverable"})
HEALTH_STATUSES = frozenset({"HEALTHY", "DEGRADED", "FAILED"})
RUN_STATUSES = frozenset({"COMPLETE", "PARTIAL", "FAILED"})
RESOLUTIONS = frozenset({"720p", "1080p"})
_TRACK_ID = re.compile(r"^battery-[A-Za-z0-9]{4,}$")


class DiagnosticValidationError(ValueError):
    """A run-summary or diagnostic record violates its fixed contract."""

    def __init__(self, message: str, *, code: str = "invalid_diagnostics") -> None:
        super().__init__(message)
        self.code = code


def _finite(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value))


def _non_empty_string(value: Any, field: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise DiagnosticValidationError(f"{field} must be a non-empty string", code=f"invalid_{field}")


def validate_diagnostic(diagnostic: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(diagnostic, Mapping):
        raise DiagnosticValidationError("diagnostic must be a JSON object", code="invalid_diagnostic")
    actual = set(diagnostic)
    missing = DIAGNOSTIC_KEYS - actual
    extra = actual - DIAGNOSTIC_KEYS
    if missing:
        raise DiagnosticValidationError(
            f"diagnostic missing keys: {', '.join(sorted(missing))}", code="missing_diagnostic_keys"
        )
    if extra:
        raise DiagnosticValidationError(
            f"diagnostic has undeclared keys: {', '.join(sorted(extra))}", code="undeclared_diagnostic_keys"
        )
    _non_empty_string(diagnostic["code"], "code")
    _non_empty_string(diagnostic["message"], "message")
    frame_id = diagnostic["frame_id"]
    if frame_id is not None and (not isinstance(frame_id, int) or isinstance(frame_id, bool) or frame_id < 0):
        raise DiagnosticValidationError("frame_id must be a non-negative integer or null", code="invalid_frame_id")
    if not isinstance(diagnostic["recoverable"], bool):
        raise DiagnosticValidationError("recoverable must be boolean", code="invalid_recoverable")
    return dict(diagnostic)


def validate_summary(summary: Mapping[str, Any]) -> dict[str, Any]:
    """Validate one strict versioned run-summary record."""

    if not isinstance(summary, Mapping):
        raise DiagnosticValidationError("summary must be a JSON object", code="invalid_summary")
    actual = set(summary)
    missing = SUMMARY_KEYS - actual
    extra = actual - SUMMARY_KEYS
    if missing:
        raise DiagnosticValidationError(
            f"summary missing keys: {', '.join(sorted(missing))}", code="missing_summary_keys"
        )
    if extra:
        raise DiagnosticValidationError(
            f"summary has undeclared keys: {', '.join(sorted(extra))}", code="undeclared_summary_keys"
        )

    version = summary["summary_schema_version"]
    if not isinstance(version, int) or isinstance(version, bool) or version != SUMMARY_SCHEMA_VERSION:
        raise DiagnosticValidationError(
            f"summary_schema_version must be {SUMMARY_SCHEMA_VERSION}", code="summary_schema_version"
        )
    _non_empty_string(summary["video_id"], "video_id")
    if summary["resolution"] not in RESOLUTIONS:
        raise DiagnosticValidationError("resolution must be 720p or 1080p", code="invalid_resolution")

    for field in ("frames_processed", "lot_count", "unique_tracks"):
        value = summary[field]
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise DiagnosticValidationError(f"{field} must be a non-negative integer", code=f"invalid_{field}")

    lot_volume = summary["lot_volume_l"]
    if lot_volume is not None and (not _finite(lot_volume) or float(lot_volume) < 0.0):
        raise DiagnosticValidationError("lot_volume_l must be finite, non-negative, or null", code="invalid_lot_volume")

    counted_ids = summary["counted_track_ids"]
    if not isinstance(counted_ids, list):
        raise DiagnosticValidationError("counted_track_ids must be an array", code="invalid_counted_ids")
    if len(counted_ids) != len(set(counted_ids)):
        raise DiagnosticValidationError("counted_track_ids must be unique", code="duplicate_counted_ids")
    for track_id in counted_ids:
        if not isinstance(track_id, str) or not _TRACK_ID.fullmatch(track_id):
            raise DiagnosticValidationError(
                "counted_track_ids contains an invalid operational ID",
                code="invalid_counted_id",
            )
    if summary["lot_count"] != len(counted_ids):
        raise DiagnosticValidationError("lot_count must equal counted_track_ids cardinality", code="lot_count_mismatch")

    fps = summary["processing_fps"]
    if fps is not None and (not _finite(fps) or float(fps) <= 0.0):
        raise DiagnosticValidationError(
            "processing_fps must be finite and positive or null",
            code="invalid_processing_fps",
        )
    if summary["health_status"] not in HEALTH_STATUSES:
        raise DiagnosticValidationError("health_status is invalid", code="invalid_health_status")
    if summary["run_status"] not in RUN_STATUSES:
        raise DiagnosticValidationError("run_status is invalid", code="invalid_run_status")

    warnings = summary["warnings"]
    errors = summary["errors"]
    if not isinstance(warnings, list) or not isinstance(errors, list):
        raise DiagnosticValidationError("warnings and errors must be arrays", code="invalid_diagnostics")
    normalized_warnings = [validate_diagnostic(item) for item in warnings]
    normalized_errors = [validate_diagnostic(item) for item in errors]
    if summary["run_status"] == "COMPLETE" and normalized_errors:
        raise DiagnosticValidationError("COMPLETE runs cannot contain fatal errors", code="complete_with_errors")

    if not isinstance(summary["replayable"], bool):
        raise DiagnosticValidationError("replayable must be boolean", code="invalid_replayable")
    refs = summary["replay_evidence_refs"]
    if not isinstance(refs, list) or not all(isinstance(ref, str) and ref.strip() for ref in refs):
        raise DiagnosticValidationError(
            "replay_evidence_refs must contain non-empty strings",
            code="invalid_replay_refs",
        )

    result = dict(summary)
    result["warnings"] = normalized_warnings
    result["errors"] = normalized_errors
    return result


def normalize_summary(summary: Mapping[str, Any]) -> dict[str, Any]:
    """Return the semantic summary used for deterministic replay comparison."""

    normalized = validate_summary(summary)
    normalized["processing_fps"] = None
    return normalized
