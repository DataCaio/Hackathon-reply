# Research: User Story 3 — Consume Stable, Honest Events

**Scope**: This research covers only the event boundary, canonical replay, run diagnostics, and downstream handoff required by User Story 3. Detection, tracking, geometry, catalog inference, counting, API, UI, and PLC control remain outside this plan.

**Research status**: Complete. The five contract decisions were resolved during `$speckit-clarify`; no `NEEDS CLARIFICATION` items remain for this slice.

## Decision 1: Canonical event serialization

**Decision**: Use UTF-8 JSONL as the normative handoff and replay format, with exactly one complete event object per line. A future stream or API may wrap the same objects but does not define a second event schema.

**Rationale**:

- It matches the delivery plan's replay-first operating model.
- It is transport-neutral and consumable by the interface without importing internal modules.
- Line boundaries provide a simple fixture, partial-output, and failure-recovery boundary.
- Deterministic replay can preserve source order without a live service or GPU.

**Alternatives considered**:

- A live API or stream as the normative format: rejected for this slice because it couples the contract to an adapter that is explicitly out of scope.
- Maintaining JSONL and an API schema in parallel: rejected because it creates two compatibility surfaces during the hackathon.

## Decision 2: Event versioning

**Decision**: Every battery event carries `schema_version: 1` from the initial release. Additive changes require consumer approval and contract tests; breaking changes increment the schema version.

**Rationale**:

- The constitution requires a versioned structured event contract.
- Self-describing fixtures make replay and consumer diagnostics unambiguous.
- The policy preserves the frozen field meanings required by the interface handoff.

**Alternatives considered**:

- Add a version only when the first breaking change occurs: rejected because initial fixtures would not identify their schema.
- Put version only in an outer transport envelope: rejected because canonical JSONL must remain self-describing when copied or replayed directly.

## Decision 3: Operational diagnostics boundary

**Decision**: Keep the battery event set limited to `TRACK_UPDATE`, `TRACK_OCCLUDED`, and `BATTERY_COUNTED`. Emit health, warnings, errors, and replay evidence in a separate versioned run-summary/diagnostics record.

**Rationale**:

- It preserves the plan's frozen domain-event contract.
- It satisfies the constitution's observability and honest-behavior requirements without making operational failures look like battery state.
- A summary can describe a run-level failure even when no battery event is valid.

**Alternatives considered**:

- Add `SYSTEM_STATUS` and `SYSTEM_ERROR` to the battery JSONL: rejected because it expands the consumer event enum and mixes run-level and track-level concerns.
- Use process exit codes and human logs only: rejected because those signals are not structured or replayable.

## Decision 4: Track-update cadence

**Decision**: Emit one `TRACK_UPDATE` per processed frame for every active track (any track not in `LOST`), preserving state changes in sequence.

**Rationale**:

- It makes the contract deterministic and traceable to frame evidence.
- It lets the interface reconstruct the same state timeline during replay.
- It avoids an unspecified sampling policy that could hide short-lived state changes.

**Alternatives considered**:

- Emit only on state or measurement changes: rejected because the consumer would lose frame-level evidence and cadence would vary with model noise.
- Sample at a fixed wall-clock rate: rejected because replay and paired-video evidence are frame-indexed, not wall-clock-indexed.

## Decision 5: Fixed event shapes and missing values

**Decision**: Each event type has a fixed declared key set. Every declared key is present; unavailable applicable values are `null`; undeclared fields are forbidden in the MVP.

**Rationale**:

- The interface can validate records without guessing whether omission means unknown, not applicable, or schema drift.
- It implements the plan's explicit `null`, never zero, rule for unavailable physical values.
- It makes contract tests and additive compatibility decisions concrete.

**Alternatives considered**:

- Sparse payloads that omit unavailable keys: rejected because omission is ambiguous for a fixed consumer contract.
- Freely added fields under an additive-only promise: rejected for the MVP because an undeclared field still changes consumer parsing and fixture expectations.

## Decision 6: Runtime and test boundary

**Decision**: Target the merged repository's declared Python `>=3.12` environment and use `pytest` contract/replay tests executed through the project's `uv` workflow. The `.python-version` file recommends Python 3.14, while the current Python 3.13.7 shell remains compatible.

**Rationale**:

- The project metadata is the authoritative runtime contract.
- The constitution requires test-first evidence and contract tests.
- No cloud connection, credential, or `AWS.sh` invocation is required to validate this transport-neutral contract.

**Alternatives considered**:

- Relax the project runtime to the current shell: rejected because it would silently change the repository's declared compatibility.
- Depend on an AWS instance for contract tests: rejected because replay and validation are intentionally CPU/local and should remain reproducible offline.

## Decision 7: Occlusion and deterministic-summary semantics

**Decision**: Emit `TRACK_OCCLUDED` on the transition into `OCCLUDED`; carry continued hidden-frame state through the per-frame `TRACK_UPDATE` records. Mark run completion explicitly as `COMPLETE`, `PARTIAL`, or `FAILED`, and normalize runtime-only `processing_fps` out of repeated replay comparisons.

**Rationale**:

- Transition-only occlusion records avoid duplicating the same state while preserving the exact point at which visibility was lost.
- Explicit partial/failed status prevents an interrupted stream from being presented as a complete run.
- Processing rate depends on execution timing and must not make otherwise identical deterministic replays compare unequal.

**Alternatives considered**:

- Emit an occlusion record on every hidden frame: rejected because it duplicates the per-frame update stream and increases consumer load.
- Compare `processing_fps` as part of replay equality: rejected because wall-clock telemetry is not deterministic evidence.
- Treat all interrupted output as failed and discard it: rejected because identifiable partial evidence is required for replay and diagnosis.

## Decision 8: Frame ordering without a new v1 field

**Decision**: Keep `frame_id` as an internal source/replay coordinate in the initial external event schema. Use nondecreasing `timestamp_ms` plus canonical JSONL line order as the consumer-visible ordering rule; preserve any same-timestamp tie order during replay.

**Rationale**:

- The clarified v1 contract freezes the published event key sets and the existing handoff examples do not expose `frame_id`.
- Line order is already required for a JSONL replay and gives a deterministic tie-break for events from the same frame.
- Internal evidence references can retain frame-level mapping without expanding the downstream event payload.

**Alternatives considered**:

- Add `frame_id` to every v1 event immediately: deferred because it would expand the clarified fixed-key contract without consumer approval.
- Rely on timestamps alone: rejected because multiple tracks can share a timestamp; canonical line order is also required.

## Open items intentionally deferred to implementation planning

- Concrete module names and dependency injection wiring remain implementation tasks, provided they preserve the contracts here.
- The interface team's eventual transport wrapper (API, WebSocket, or other) is an adapter decision; it must not fork the canonical JSONL schema.
- Cloud deployment, authentication, retention, and operational access controls are outside User Story 3 and require a separate deployment/integration plan.
