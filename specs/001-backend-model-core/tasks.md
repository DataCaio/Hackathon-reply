---

description: "Implementation tasks for User Story 3 stable event handoff"
---

# Tasks: User Story 3 — Consume Stable, Honest Events

**Input**: Design documents from `specs/001-backend-model-core/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/](./contracts/), and [quickstart.md](./quickstart.md)

**Scope fence**: This task list implements only User Story 3 (P3): the versioned battery-event boundary, canonical JSONL serialization, fixed-key and null semantics, run-summary diagnostics, deterministic replay, and the consumer fixture. User Stories 1, 2, and 4 are intentionally omitted; detector, tracking, geometry, catalog, count-gate, API, UI, VLM, and real PLC-control work is outside this task list.

**Tests**: Tests are required by the specification's test-first rule and must be written to fail before the corresponding implementation tasks.

**Environment**: Use `uv` with a Python `>=3.12` interpreter; `.python-version` recommends 3.14. No GPU, AWS account, live service, or `AWS.sh` invocation is needed.

**Format**: `[ID] [P?] [Story] Description`; every task below includes an exact file path and, where relevant, explicit dependencies.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Establish the package, test, fixture, and dependency layout needed for the isolated event-boundary slice.

- [X] T001 [P] Add `pytest` to the development dependency group and configure test discovery in `pyproject.toml`, keeping production dependencies limited to the standard library.
- [X] T002 [P] Create the planned package, CLI, contract-test, integration-test, and fixture directories under `src/hackathon_reply/contracts/`, `scripts/`, `tests/contract/`, `tests/integration/`, and `tests/fixtures/user_story3/invalid/`.
- [X] T003 [P] Review and extend `.gitignore` with scoped exclusions for private recordings, model weights, credentials, generated run output, and caches while keeping `tests/fixtures/user_story3/` and published contract examples trackable.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Establish the public package boundary and shared test support before implementing any Story 3 behavior.

**⚠️ CRITICAL**: No Story 3 implementation task starts until this phase is complete.

- [X] T004 [P] Define the narrow public contract package surface and version placeholder in `src/hackathon_reply/contracts/__init__.py`; do not import detector, tracker, geometry, catalog, pipeline, API, or PLC modules.
- [X] T005 [P] Add shared fixture-loading, JSON canonicalization, and temporary-output helpers in `tests/contract/conftest.py` for contract and consumer tests without embedding production internals.

**Checkpoint**: The repository can import the contract package and discover isolated Story 3 tests under `uv run pytest`.

---

## Phase 3: User Story 3 — Consume Stable, Honest Events (Priority: P3) 🎯 Scoped MVP

**Goal**: Let an interface consumer read and replay a canonical JSONL stream containing exactly the three battery event types, fixed keys, honest nulls, versioned diagnostics, and deterministic exactly-once count evidence without importing Model Core internals.

**Independent Test**: Consume `tests/fixtures/user_story3/events.jsonl` (at least 20 events) and `tests/fixtures/user_story3/summary.json` using only the published contract package. Verify fixed keys, event names, required fields, states, null semantics, finite numeric values, nondecreasing ordering, one update per processed frame for active tracks, transition-only occlusion, exactly-once counted identities, simulated-PLC labeling, and identical semantic summaries across two CPU-only replays.

### Tests for User Story 3 (write first)

> **Required Red-Green-Refactor evidence**: run these tests and confirm they fail for the intended missing implementation before starting T010.

- [X] T006 [P] [US3] Write failing fixed-key event contract tests in `tests/contract/test_events.py` covering `schema_version: 1`, the exact `TRACK_UPDATE`/`TRACK_OCCLUDED`/`BATTERY_COUNTED` enum, common envelopes, per-event key sets, required nulls, finite numbers, state values, operational IDs, timestamp ordering, duplicate counts, and rejection of `PLC_STATE` or undeclared keys.
- [X] T007 [P] [US3] Write failing run-summary and diagnostics tests in `tests/contract/test_diagnostics.py` covering `summary_schema_version: 1`, fixed diagnostic keys, `HEALTHY`/`DEGRADED`/`FAILED` health, `COMPLETE`/`PARTIAL`/`FAILED` run status, lot-count/volume invariants, replay references, and runtime-only `processing_fps` normalization.
- [X] T008 [P] [US3] Write a failing published-consumer contract test in `tests/contract/test_consumer_fixture.py` that imports only the public contract package and reads the fixture paths, asserting no internal vision/tracking/geometry/catalog/pipeline/PLC imports.
- [X] T009 [P] [US3] Write failing deterministic replay integration tests in `tests/integration/test_user_story3_replay.py` for line-order preservation, first-invalid-line diagnostics, partial evidence, transition-only occlusion plus hidden-frame updates, reacquisition, one frozen count followed by post-count updates, and repeated replay equality.

### Implementation for User Story 3

- [X] T010 [P] [US3] Implement fixed event records, state enums, exact key sets, operational ID checks, nullability rules, finite-number checks, and event-level invariants in `src/hackathon_reply/contracts/events.py` so T006 passes.
- [X] T011 [P] [US3] Implement versioned `Diagnostic` and run-summary records, status validation, counted-identity cardinality, lot-volume invariants, and replayability semantics in `src/hackathon_reply/contracts/diagnostics.py` so T007 passes.
- [X] T012 [US3] Implement streaming canonical JSONL and summary serialization/validation in `src/hackathon_reply/contracts/serialization.py`, preserving one UTF-8 object per line, canonical key/value encoding, first-invalid-line reporting, fixed-key rejection, and explicit `null` handling (depends on T010 and T011).
- [X] T013 [US3] Implement CPU-only deterministic event replay in `src/hackathon_reply/replay.py`, preserving canonical line order and partial evidence while comparing semantic summaries with runtime-only `processing_fps` normalized (depends on T012 and T009).
- [X] T014 [P] [US3] Implement the strict validator CLI in `scripts/validate_events.py` with the `--input` and `--summary` arguments documented in `specs/001-backend-model-core/quickstart.md` (depends on T012).
- [X] T015 [P] [US3] Implement the replay CLI in `scripts/replay_events.py` with the documented `--input`, `--summary`, `--output`, and `--result` arguments and no detector/GPU/AWS dependency (depends on T013).
- [X] T016 [US3] Author the valid canonical fixture and versioned summary in `tests/fixtures/user_story3/events.jsonl` and `tests/fixtures/user_story3/summary.json`, with at least 20 events covering incomplete physical evidence/nulls, per-frame active-track updates, transition-only occlusion, hidden-frame updates, reacquisition, exactly one `BATTERY_COUNTED`, post-count visibility, terminal loss or explicit partial status, lot invariants, warnings/errors, and simulated-PLC labeling (depends on T010 and T011).
- [X] T017 [P] [US3] Add invalid replay inputs under `tests/fixtures/user_story3/invalid/` for missing/extra keys, wrong schema version, non-finite or invalid confidence/interval values, timestamp regression, invalid state or track ID, duplicate counted identity, inconsistent lot totals, and an interrupted stream mislabeled `COMPLETE` (depends on T012).
- [X] T018 [US3] Run the focused contract and replay suite from `tests/contract/` and `tests/integration/test_user_story3_replay.py`, then close the Red-Green-Refactor loop by retaining assertions for every changed contract rule (depends on T006–T017).

**Checkpoint**: User Story 3 is independently consumable when T018 passes and the validator/replay CLIs operate only on the published fixture and summary.

---

## Phase 4: Polish & Cross-Cutting Concerns (Story 3 Handoff)

**Purpose**: Freeze compatibility evidence, synchronize the handoff documentation, and verify the release boundary without expanding scope.

- [X] T019 [P] Add schema-compatibility regression cases in `tests/contract/test_events.py` and versioned examples under `tests/fixtures/user_story3/compat/` for an approved additive v1 change and a breaking change that must increment `schema_version`.
- [X] T020 Synchronize `specs/001-backend-model-core/contracts/events.md`, `specs/001-backend-model-core/contracts/diagnostics.md`, `specs/001-backend-model-core/contracts/replay.md`, and `specs/001-backend-model-core/quickstart.md` with the implemented key sets, nullability, cadence, diagnostics, CLI arguments, fixture paths, and compatibility behavior (depends on T018 and T019).
- [X] T021 [P] Add a concise downstream handoff section to `README.md` linking the canonical JSONL fixture, summary, validator, replay command, no-internals boundary, and explicit simulated-PLC/no-AWS limitation.
- [X] T022 Execute the complete Story 3 handoff rehearsal in a Python `>=3.12` `uv` environment: `uv run pytest tests/contract tests/integration/test_user_story3_replay.py -q`, both commands from `scripts/validate_events.py` and `scripts/replay_events.py`, and a two-run semantic comparison; record the command/output evidence and confirm no private artifacts or out-of-scope modules enter the diff (depends on T018–T021).

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: T001–T003 have no prerequisites and can run in parallel.
- **Foundational (Phase 2)**: T004–T005 depend on Setup and block Story 3 tests/implementation.
- **User Story 3 tests**: T006–T009 depend on the foundational package/test surface and must fail before implementation.
- **User Story 3 implementation**: T010 and T011 can proceed in parallel after the failing tests; T012 depends on both; T013 and T014 follow T012, with T014 parallel to T013; T015 follows T013; T016 follows the event/diagnostics schemas; T017 can run in parallel with T016 after validation behavior exists; T018 is the red-green checkpoint.
- **Polish (Phase 4)**: T019 can run after the contract implementation; T020 and T021 follow the Story 3 checkpoint; T022 is the final handoff gate.

### User Story 3 Dependencies

- **User Story 3 (P3)**: This plan's scoped MVP is independently testable after Phase 2 and does not depend on User Stories 1, 2, or 4. Upstream producers may supply boundary-shaped fixture data, but no detector, tracker, geometry, catalog, count-gate, API, UI, VLM, or PLC-control module may be imported.

### Parallel Opportunities

- T001–T003 are independent setup edits.
- T004–T005 are independent package/test-surface edits.
- T006–T009 are separate test files and can be authored in parallel.
- T010–T011 are separate contract modules and can be implemented in parallel.
- T013 and T014 are separate replay/CLI surfaces after serialization; T016 and T017 are separate valid/invalid fixture trees.
- T019 and T021 are separate compatibility/handoff artifacts once the Story 3 checkpoint is reached.

### Parallel execution example: User Story 3

After T005 completes, the following independent work can start together:

```text
T006  tests/contract/test_events.py
T007  tests/contract/test_diagnostics.py
T008  tests/contract/test_consumer_fixture.py
T009  tests/integration/test_user_story3_replay.py
```

After the failing tests are recorded, T010 and T011 can run together; after T012, T013 and T014 can run together, followed by T015. T016 and T017 can then be authored in parallel before T018 closes the story checkpoint.

### Within User Story 3

- Tests MUST be written and observed failing before T010–T015 implementation work.
- Event and diagnostics models precede serialization; serialization precedes replay and CLIs.
- Valid and invalid fixtures must exercise the same published schemas; no fixture may encode a private internal object.
- The story is complete only when the consumer test passes without internal imports and two replays produce the same semantic summary.

---

## Implementation Strategy

### Scoped MVP First

1. Complete Setup and Foundational phases.
2. Write T006–T009 and capture intended failures.
3. Implement T010–T017 and close the focused suite with T018.
4. Stop and validate the independently consumable Story 3 handoff before any other feature story is attempted.

### Incremental Delivery

1. Deliver fixed event and diagnostics contracts with negative tests.
2. Add canonical JSONL serialization and a 20+ event fixture.
3. Add deterministic replay and validator/replay CLIs.
4. Add compatibility evidence and the consumer handoff rehearsal.

### Release Gate

The handoff is ready only when the focused tests, invalid-input checks, two-run replay comparison, quickstart commands, and scope/security review in T022 all pass in the declared Python `>=3.12` environment.
