"""Shared backend value contracts plus the public Story 3 event boundary.

The package exposes stable value objects used by Stories 2 and 4 alongside
versioned event/diagnostic helpers for Story 3. It does not import detector,
tracker, geometry, catalog, pipeline, API, or PLC implementations.
"""

CONTRACT_SCHEMA_VERSION = 1
SUMMARY_SCHEMA_VERSION = 1

from .core import (  # noqa: E402
    Box,
    CatalogCandidate,
    Detection,
    FrameMeasurement,
    FrameMeta,
    Point,
    ReplayFrame,
    TrackEstimate,
    TrackObservation,
    TrackState,
    VolumeEstimate,
)
from .diagnostics import (  # noqa: E402  (constants intentionally precede exports)
    DiagnosticValidationError,
    normalize_summary,
    validate_diagnostic,
    validate_summary,
)
from .events import (  # noqa: E402
    EventValidationError,
    iter_validated_jsonl,
    load_event_stream,
    validate_event,
    validate_event_stream,
)
from .serialization import (  # noqa: E402
    RunValidationResult,
    canonical_json,
    load_summary,
    serialize_event,
    serialize_summary,
    validate_run,
    write_event_stream,
)

__all__ = [
    "CONTRACT_SCHEMA_VERSION",
    "SUMMARY_SCHEMA_VERSION",
    "Box",
    "CatalogCandidate",
    "Detection",
    "DiagnosticValidationError",
    "EventValidationError",
    "FrameMeasurement",
    "FrameMeta",
    "Point",
    "ReplayFrame",
    "RunValidationResult",
    "TrackEstimate",
    "TrackObservation",
    "TrackState",
    "VolumeEstimate",
    "canonical_json",
    "iter_validated_jsonl",
    "load_event_stream",
    "load_summary",
    "normalize_summary",
    "serialize_event",
    "serialize_summary",
    "validate_diagnostic",
    "validate_event",
    "validate_event_stream",
    "validate_run",
    "validate_summary",
    "write_event_stream",
]
