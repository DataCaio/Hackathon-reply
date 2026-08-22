# Implementation Plan: User Story 3 — Consume Stable, Honest Events

**Branch**: `001-backend-model-core` | **Date**: 2026-08-22 | **Spec**: [spec.md](./spec.md#user-story-3---consume-stable-honest-events-priority-p3)

**Scope fence**: This plan covers only User Story 3: the stable versioned event boundary, canonical JSONL handoff, fixed-key/null rules, versioned run-summary diagnostics, deterministic event replay, and consumer fixture. It does not plan detector, tracking, geometry, catalog, count-gate, API, UI, VLM, or PLC-control implementation.

## Summary

Deliver a transport-neutral contract that lets the interface team consume and replay Model Core results without importing internal vision or tracking code. The contract consists of three battery event types (`TRACK_UPDATE`, `TRACK_OCCLUDED`, and `BATTERY_COUNTED`) serialized as one UTF-8 JSON object per JSONL line, plus one versioned run-summary/diagnostics record for health, warnings, errors, lot invariants, and replay evidence.

The design freezes `schema_version: 1`, fixed keys per event type, `null` for unavailable applicable values, no undeclared MVP fields, one update per processed frame for each active track, transition-only occlusion records, exactly-once counted identities, and deterministic replay that normalizes runtime-only processing-rate telemetry.

## Technical Context

**Language/Version**: Python `>=3.12` as declared by the merged repository; `.python-version` recommends 3.14 and the current Python 3.13.7 shell is compatible.

**Primary Dependencies**: Python standard library for domain records, finite-number checks, JSON, and JSONL framing; `pytest` as a development/test dependency; `uv` for the declared project environment. No API framework, tracker vendor, model runtime, or cloud SDK is needed for this slice.

**Storage**: UTF-8 canonical JSONL event streams, one JSON run-summary/diagnostics record per run, and versioned test fixtures under `tests/fixtures/user_story3/`. No database is introduced.

**Testing**: Test-first contract tests, consumer-fixture tests, strict serialization/validation tests, negative input tests, and deterministic CPU-only replay tests executed through `uv run pytest` in a Python `>=3.12` environment.

**Target Platform**: Headless Linux execution. Contract validation and replay must run on CPU without AWS, GPU, a live service, or `AWS.sh`.

**Project Type**: Internal Python package plus validation/replay CLI utilities for a pipeline integration boundary.

**Performance Goals**: Stream validation line-by-line without loading a full event file into memory; emit one `TRACK_UPDATE` per processed frame for each active track; validate a fixture of at least 20 events; replay a cached sequence of 300–900 frames deterministically; support the documented under-10-minute operator rehearsal including backup replay.

**Constraints**: Exactly three battery event types; `schema_version: 1` on every event; fixed keys; all declared keys present; `null` rather than zero for unavailable applicable values; finite numbers only; no undeclared MVP fields; diagnostics separate from battery events; no `PLC_STATE`; no internal detector/tracker/vendor imports; no private media, credentials, or runtime caches in version control; test-first evidence is mandatory.

**Scale/Scope**: A minimum 20-event consumer fixture, 300–900-frame deterministic replay, and full-run streams from the available recordings (up to 44,788 frames per resolution). One summary/diagnostics record describes each run. The validator must remain streaming and bounded in memory.

## Constitution Check

*Gate status before Phase 0: PASS.*

| Principle / gate | Evidence in this scoped plan |
|---|---|
| Architecture-first, contract-driven boundaries | `contracts/events.md`, `contracts/diagnostics.md`, and `contracts/replay.md` define a stable boundary. Serialization and replay adapters do not expose detector, tracker, geometry, catalog, or PLC internals. |
| SOLID and Clean Code | Event schemas, diagnostics, JSONL validation, and replay have separate responsibilities and are replaceable through narrow interfaces. No framework or global state is required. |
| Test-first development | Contract and negative tests are written to fail before implementation; focused tests and the full relevant suite are required before merge. |
| Evidence-first measurement integrity | Event fields retain uncertainty, null semantics, operational IDs, source resolution, and replay references. The plan does not invent volume or catalog identity. |
| Observable and honest behavior | Versioned events, structured run diagnostics, explicit partial/failed status, replayability, and simulated-PLC labeling are required. |
| Scope and P0 protection | The plan preserves the replayable handoff and does not pull API, UI, VLM, PLC control, or upstream model work into this story. |

No constitution violation or complexity exception is required.

## Project Structure

### Documentation (this feature)

```text
specs/001-backend-model-core/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── events.md
│   ├── diagnostics.md
│   └── replay.md
└── tasks.md                 # created later by $speckit-tasks; not part of this command
```

### Source Code (repository root)

```text
src/hackathon_reply/
├── __init__.py
├── contracts/
│   ├── events.py             # fixed event records, enums, key-set validation
│   ├── diagnostics.py        # versioned run-summary and diagnostic records
│   └── serialization.py       # JSONL framing, finite-number and null checks
└── replay.py                 # contract-level deterministic event replay

scripts/
├── validate_events.py        # strict JSONL + diagnostics validator
└── replay_events.py          # CPU-only canonical event replay utility

tests/
├── contract/
│   ├── test_events.py
│   ├── test_diagnostics.py
│   └── test_consumer_fixture.py
├── integration/
│   └── test_user_story3_replay.py
└── fixtures/
    └── user_story3/
        ├── events.jsonl
        ├── summary.json
        └── invalid/
```

Existing upstream modules such as detection, tracking, geometry, catalog, and count gate are consumed only through boundary-shaped inputs in fixtures or adapters. They are not edited by this User Story 3 plan.

**Structure Decision**: Keep the contract implementation inside the existing `src/hackathon_reply` package so it remains compatible with `pyproject.toml`. Keep normative human-readable contracts under the feature directory and executable fixtures/tests outside production modules. Use CLI utilities only for validation and replay; do not introduce an API or persistence service.

## Phase 0: Research Complete

Research decisions are recorded in [research.md](./research.md). All specification clarifications for this story are resolved. The research also records the Python-version mismatch, the offline/CPU replay boundary, transition-only occlusion semantics, explicit partial-run status, and normalization of `processing_fps` during deterministic comparison.

## Phase 1: Design Complete

- [data-model.md](./data-model.md) defines the common event envelope, fixed per-event keys, nullability, state and lot invariants, and the versioned diagnostics record.
- [contracts/events.md](./contracts/events.md) is the normative battery-event contract and JSONL serialization rule.
- [contracts/diagnostics.md](./contracts/diagnostics.md) is the normative run-summary/diagnostics contract, including `COMPLETE`, `PARTIAL`, and `FAILED` status.
- [contracts/replay.md](./contracts/replay.md) defines line-order preservation, validation failures, acceptance fixture coverage, and the consumer boundary.
- [quickstart.md](./quickstart.md) provides the CPU-only contract-test, validation, replay, and handoff rehearsal commands.

## Implementation Boundaries for Later Tasks

1. Write contract tests for the fixed schemas, schema version, key sets, nullability, finite numbers, state enums, identity format, timestamps, intervals, and forbidden `PLC_STATE`/extra fields before production code.
2. Implement domain records and strict validators without importing upstream vendors or framework types.
3. Implement line-oriented JSONL serialization and diagnostics serialization with explicit partial-output handling.
4. Create the 20+ event fixture covering incomplete evidence, per-frame updates, occlusion/reacquisition, count, post-count visibility, and terminal loss; create valid and invalid diagnostics fixtures.
5. Implement CPU-only replay and canonical summary comparison, excluding runtime-only `processing_fps` from equality.
6. Run the consumer contract test using only published fixtures/contracts, then hand off the examples, fixture, nullability matrix, cadence, state enum, replay command, and simulated-PLC notice.

## Constitution Check — Post-Design

*Gate status after Phase 1: PASS.*

- The fixed event schemas and diagnostics sidecar preserve a single-direction boundary and keep downstream consumers independent of internals.
- The design separates domain records, validation/serialization, diagnostics, and replay; it does not create a speculative service layer.
- The quickstart and planned tests enforce Red-Green-Refactor, strict contract compatibility, deterministic replay, and negative-path evidence.
- Uncertainty, null semantics, source resolution, operational UUIDs, partial output, and replay references remain visible; no volume or PLC claim is fabricated.
- The three battery event types remain frozen; health/errors are structured separately; APIs or streams remain wrappers rather than alternate schemas.

## Complexity Tracking

No violations. No additional project, service, repository abstraction, or cloud dependency is introduced for User Story 3.
