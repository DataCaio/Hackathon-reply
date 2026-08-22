# Feature Specification: Backend Model Core

**Feature Branch**: `not-created (no before_specify hook configured)`

**Created**: 2026-08-22

**Status**: Draft

**Input**: User description: "Read `PLANO_BACKEND_3_AGENTES.md` and align the Backend/Model Core plan to the project constitution."

## Clarifications

### Session 2026-08-22

- Q: Should every event carry an explicit schema version from the first release, or should versioning be introduced only when the contract changes? → A: Include `schema_version: 1` on every event from the initial release; increment it for breaking changes.
- Q: Should the canonical handoff and replay fixture use one structured event per line in JSONL, or should another transport be normative? → A: Canonical JSONL with one event per line; APIs or streams may wrap the same events.
- Q: Should health, warnings, and processing errors travel as separate structured records, or only in the run summary alongside the battery events? → A: Keep the three battery event types and put health, warnings, and errors in a versioned run-summary/diagnostics record.
- Q: How frequently should active tracks emit `TRACK_UPDATE` records in the canonical JSONL? → A: Emit one update per processed frame for every active track; include state changes in that stream.
- Q: Should each event type require a fixed set of keys even when a field is unavailable, using `null`, or may fields be omitted when not applicable? → A: Fixed keys per event type; unavailable applicable values are `null`; no undeclared fields in the MVP.
- Q: What should the MVP’s numeric uncertainty interval represent for each reported volume estimate? → A: Option A — deterministic, auditable bounds combining plausible catalog volumes with configured measurement-error bounds.
- Q: When only a documented simplified calibration is available, may its absolute volume estimates be used in `BATTERY_COUNTED` events, or must counting wait for a trusted physical reference? → A: Option A — only trusted physical references enable counted absolute volumes; simplified or pixel-only results remain unvalidated and cannot trigger counted-volume events.
- Q: What delivery guarantee should the structured event stream provide when records are retried or a run is replayed? → A: Option B — exactly-once delivery; an interruption fails the run and requires a clean restart.
- Q: What fields should each external event use to prove its identity and order during exactly-once delivery and clean replay? → A: Option A — `run_id`, `event_id`, monotonic `sequence`, and `schema_version` in the contract.
- Q: If a battery remains ambiguous between multiple valid catalog entries but has a finite expected volume and uncertainty interval, should it still count toward the lot? → A: Option A — count with expected volume and uncertainty while retaining the ambiguous candidate set.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Produce a Trustworthy Lot Result (Priority: P1)

As an operations demonstrator, I want to process a selected physical video in both 1080p and 720p so that I receive persistent battery identities, catalog-constrained volume estimates with uncertainty, exactly-once counts, a lot total, and structured events that downstream consumers can use.

**Why this priority**: This is the smallest complete expression of the product claim: batteries are found, followed over time, measured honestly, counted once, and compared across resolutions.

**Independent Test**: Process one explicitly paired 1080p/720p video from start to finish using the same calibrated camera and counting configuration. Verify that both runs finish unattended, emit valid events and summaries, and produce lot count and volume results without duplicate battery contributions.

**Acceptance Scenarios**:

1. **Given** a valid video pair, trusted physical calibration, and a valid catalog, **When** the operator processes both recordings, **Then** each visible battery receives a persistent operational identity, qualifying gate crossings contribute at most once, and each counted volume includes confidence and an uncertainty interval.
2. **Given** a battery that is temporarily hidden and then becomes visible again, **When** it is reacquired with sufficient evidence, **Then** it retains the same operational identity and its prior measurement evidence is preserved.
3. **Given** no trusted physical calibration, **When** the operator starts a run, **Then** the system clearly marks physical volume as unvalidated, does not present absolute volume as trustworthy, and does not emit a counted-volume event with an invented value.
4. **Given** a completed run at each resolution, **When** the operator reviews the comparison, **Then** the result includes the count gap and relative volume gap and identifies any metric that could not be evaluated from available evidence.

---

### User Story 2 - Count Each Battery Exactly Once (Priority: P2)

As an operations evaluator, I want battery identity and count decisions to survive occlusion, reverse motion, and repeated visibility so that lot totals remain correct and auditable.

**Why this priority**: Duplicate counting or identity loss directly invalidates the batch result even when segmentation and measurement appear accurate.

**Independent Test**: Replay a deterministic fixture containing one battery that is occluded, reacquired, crosses the gate, and reappears; a second battery that approaches but does not cross; and a short false positive. Verify identity transitions and the final lot invariants without requiring live detection.

**Acceptance Scenarios**:

1. **Given** a confirmed battery moving in the configured direction, **When** its tracked center crosses from the entry side to the exit side of the gate and it has a valid volume estimate, **Then** exactly one counted event is produced and the lot count and volume increase once.
2. **Given** the same battery remains visible or reappears after it has been counted, **When** subsequent observations are processed, **Then** no second counted event is produced.
3. **Given** a battery crosses in the reverse direction or approaches without crossing, **When** its observations are processed, **Then** it does not contribute to the lot.
4. **Given** a short-lived false positive that never becomes a confirmed track, **When** it approaches the gate, **Then** it does not generate a count.

---

### User Story 3 - Consume Stable, Honest Events (Priority: P3)

As an interface integration team member, I want a stable, versioned event boundary and replayable fixture so that the interface and simulated PLC display can integrate without depending on vision, geometry, catalog, or tracking internals.

**Why this priority**: A frozen and independently consumable boundary allows parallel delivery and prevents model or tracker choices from leaking into downstream products.

**Independent Test**: Consume the canonical JSONL fixture of at least 20 events using only the published event contract. Verify fixed keys per event type, event names, required fields, state values, null semantics, numeric validity, ordering, and exactly-once counted identities.

**Acceptance Scenarios**:

1. **Given** a track with incomplete physical evidence, **When** a track update is emitted, **Then** every declared key for that event type is present, unavailable physical fields are null rather than zero, no undeclared field is added, and confidence truthfully reflects the available evidence.
2. **Given** a temporary occlusion, **When** the visible state changes, **Then** downstream consumers receive the permitted state and occlusion information through the structured event boundary.
3. **Given** an additive contract version change approved with the consumer, **When** the new events are delivered, **Then** existing fields retain their names and meanings and compatibility tests demonstrate the decision.
4. **Given** events displayed by a PLC-oriented consumer, **When** the demo is presented, **Then** the display is explicitly identified as simulated and the Model Core never claims or decides real PLC state.
5. **Given** a processing warning or error, **When** the consumer reads the run result, **Then** the versioned run-summary/diagnostics record exposes the condition separately from the three battery event types and identifies whether the output is replayable.
6. **Given** an active track spans multiple processed frames, **When** the consumer replays the canonical JSONL, **Then** it receives one `TRACK_UPDATE` for that track on each processed frame and sees state changes in sequence.

---

### User Story 4 - Audit Measurement and Resolution Evidence (Priority: P4)

As a technical evaluator, I want every volume and robustness claim to be traceable to video, frame, track, calibration, and catalog evidence so that ambiguous identity, missing ground truth, and resolution differences are reported rather than hidden.

**Why this priority**: The product is credible only when its measurements, uncertainty, and limitations can be independently inspected.

**Independent Test**: Evaluate the paired-resolution result against a traceable demo golden set containing manual crossings, 10–20 track intervals, marked occlusions, and catalog labels only where independently verifiable.

**Acceptance Scenarios**:

1. **Given** multiple catalog entries remain plausible, **When** a track estimate is reported, **Then** the result remains ambiguous, lists valid candidates, and does not invent a single identity.
2. **Given** sufficient golden-set evidence for a metric, **When** evaluation runs, **Then** relative volume error, duplicate rate, count error, resolution volume gap, and uncertainty calibration are reported as applicable.
3. **Given** insufficient ground truth for a metric, **When** evaluation runs, **Then** that metric is marked unavailable and one resolution is not substituted as truth for the other.
4. **Given** paired 720p and 1080p recordings of the same physical video, **When** data partitions are reviewed, **Then** the pair belongs to the same train, validation, or test partition and consecutive frames do not leak across partitions.

### Edge Cases

- A frame contains no battery: the frame produces no detections and the run continues without an error.
- A mask or contour is missing, degenerate, too small, truncated by the region boundary, or strongly occluded: the measurement is rejected or down-weighted without erasing better evidence already accumulated for the track.
- A battery is rotated: length and width orientation are treated as interchangeable for catalog matching.
- The camera reference is absent or unreliable: pixel-space processing may continue for demonstration, but validated millimeter dimensions and absolute liters remain unavailable and the limitation is prominent.
- A catalog row contains a locale-specific decimal, non-positive dimensions, or malformed data: valid locale-specific values are normalized explicitly; invalid rows are rejected and reported rather than silently corrected.
- Multiple catalog rows have identical dimensions: repeated dimensions do not create an artificial probability advantage, while associated categories remain traceable.
- A video filename differs only by letter case or a pair is missing: the explicit pair manifest is authoritative and validation fails before processing instead of guessing a filename.
- Paired videos disagree on frame count, duration, frame rate, or physical identity: the pair is rejected for comparative evaluation.
- A timestamp regresses or a frame identifier does not start at zero: the run fails with a diagnostic that identifies the first invalid record.
- A battery crosses the gate in reverse, stays beyond it for many frames, or reappears after counting: no duplicate contribution is made.
- Occlusion exceeds the configured reacquisition window: the track becomes lost with explicit evidence; a later observation must not silently inherit identity without satisfying the documented reacquisition rule.
- A volume is zero, negative, non-finite, or lacks a valid uncertainty representation: it cannot produce a counted-volume event.
- Event delivery is interrupted or a record cannot be serialized: the run fails explicitly, partial evidence remains identifiable, and recovery requires a clean replay rather than resuming partial output.
- No golden-set label exists for catalog identity or volume: the label is recorded as ambiguous or the metric as unavailable, never inferred from another resolution.

## Requirements *(mandatory)*

### Scope

**In scope**:

- Battery segmentation or detection from paired 1080p and 720p recordings.
- Persistent tracking, occlusion and reacquisition states, directed exactly-once counting, and lot aggregation.
- Calibrated length and width measurement, catalog-constrained volume estimation, ambiguity, confidence, and uncertainty.
- Structured domain events, deterministic replay, run summaries, paired-resolution evaluation, traceable evidence, and a release-ready handoff to downstream consumers.

**Out of scope**:

- API servers, user interfaces, database adapters, VLM behavior, and PLC control logic.
- Real PLC or hardware integration; any PLC-oriented display is simulated by another feature.
- Direct black-box volume regression, three-dimensional reconstruction, appearance-based re-identification, distributed training, and optimization work that delays the stable replay path.
- Invented physical calibration, invented catalog labels, or unsupported accuracy claims.

### Functional Requirements

- **FR-001**: The system MUST use an explicit manifest to identify the five 1080p/720p video pairs, including case-sensitive filenames, and MUST NOT derive pair names by convention.
- **FR-002**: The system MUST validate that each selected pair represents the same physical recording and is aligned by frame identifier, duration, and frame rate before using it for resolution comparison.
- **FR-003**: The system MUST recognize a single vision class, `battery`, for this feature.
- **FR-004**: The system MUST preserve the decision order: frame-level battery segmentation, persistent track reasoning, physical measurement, catalog inference, directed count decision, lot aggregation, and external event emission.
- **FR-005**: Each processing stage MUST expose a documented, independently testable contract and MUST NOT expose vendor-specific model, tracker, or image-processing objects beyond its boundary.
- **FR-006**: Detection boxes and mask polygons MUST use coordinates from the original frame; boxes MUST use the ordered semantics `[x_min, y_min, x_max, y_max]`.
- **FR-007**: Regions of interest, count gates, and flow direction MUST remain consistent across both resolutions through resolution-independent coordinates.
- **FR-008**: Frame identifiers MUST begin at zero, and event timestamps derived from the recording MUST be monotonic within a run.
- **FR-009**: A frame with no battery MUST yield an empty detection result and MUST NOT terminate processing.
- **FR-010**: Every confirmed battery track MUST receive a persistent operational identifier in the form `battery-xxxx`, independent of any internal tracker identifier.
- **FR-011**: Track state MUST be one of `DETECTED`, `TRACKING`, `OCCLUDED`, `REACQUIRED`, `COUNTED`, or `LOST`, and every transition MUST have documented entry conditions.
- **FR-012**: Temporary loss of detection MUST transition an eligible track to `OCCLUDED`; it MUST NOT create a new battery identity by itself.
- **FR-013**: Reacquisition MUST require traceable motion and size evidence, retain the operational identifier, and preserve the last trustworthy volume posterior.
- **FR-014**: A track MUST be counted only when it crosses the configured gate in the valid direction, has not already been counted, and has a finite positive expected volume estimate with a valid uncertainty interval. An ambiguous catalog identity does not by itself block counting; the counted event MUST retain the valid candidate set and MUST NOT invent a unique identity.
- **FR-015**: A counted track MUST contribute to its lot exactly once even if it remains visible, becomes occluded, is reacquired, or reappears later in the same run.
- **FR-016**: The volume and uncertainty committed at the count event MUST be frozen for the lot; later track updates MUST NOT retroactively change that contribution in the MVP.
- **FR-017**: For every completed run, the lot count MUST equal the number of unique counted events and the lot volume MUST equal the sum of their frozen volumes within the published numeric tolerance.
- **FR-018**: Physical length and width MUST be reported as validated millimeters and volume as validated liters only when a trusted physical reference supports those units.
- **FR-019**: When trusted physical calibration is unavailable, the system MUST expose the limitation, MUST label any simplified-calibration or pixel-only estimate as unvalidated, MUST NOT claim validated absolute volume, and MUST NOT emit a counted-volume event from that fallback.
- **FR-020**: Measurement quality MUST reflect mask confidence, visibility, contour validity, boundary truncation, and stability over time; a low-quality frame MUST contribute less evidence without erasing stronger prior observations.
- **FR-021**: Length and width orientation MUST be treated as equivalent during catalog matching.
- **FR-022**: Catalog ingestion MUST explicitly normalize valid locale-specific decimals, require positive dimensions, create stable catalog identities, report rejected rows, collapse exact dimension duplicates for probability purposes, and preserve all associated categories.
- **FR-023**: Catalog inference MUST accumulate evidence by track, rank all plausible dimension candidates, and retain ambiguity when evidence does not justify a unique catalog identity.
- **FR-024**: Volume MUST be derived from catalog dimensions and candidate probabilities, never from a direct opaque volume prediction.
- **FR-025**: Every available volume result MUST include a confidence value from 0 to 1 and a deterministic, auditable uncertainty interval that combines plausible catalog volumes with configured measurement-error bounds; when no usable physical observation exists, physical values MUST be unavailable and volume confidence MUST be 0.
- **FR-026**: The external contract MUST support `TRACK_UPDATE`, `TRACK_OCCLUDED`, and `BATTERY_COUNTED` events without allowing the Model Core to emit or decide `PLC_STATE`.
- **FR-027**: A `TRACK_UPDATE` MUST be emitted once per processed frame for every active track (any track not in `LOST`) and MUST identify the recording, resolution, timestamp, track, state, original-frame box, visibility, available measurement and volume evidence, uncertainty, confidence, and whether the track has been counted.
- **FR-028**: A `TRACK_OCCLUDED` event MUST identify the track, predicted position when available, last trustworthy volume when available, and its confidence.
- **FR-029**: A `BATTERY_COUNTED` event MUST identify the track, frozen positive volume, uncertainty interval, current lot count, current lot volume, and any retained ambiguous catalog candidate set.
- **FR-030**: Each event type MUST use a fixed set of declared keys; every declared key MUST be present, unavailable applicable physical values MUST be null rather than zero, undeclared fields MUST NOT be added in the MVP, and all emitted numbers MUST be valid finite numeric values.
- **FR-031**: Every event MUST contain a `run_id`, an `event_id` unique within that run, a monotonically increasing `sequence` within that run, and `schema_version: 1` from the initial release. Events MUST be serialized one per canonical JSONL line and delivered exactly once per run; APIs or streams MAY wrap them without changing their meaning, additive changes MUST be approved with the consumer, and breaking changes MUST increment the schema version.
- **FR-032**: External state changes MUST be replayable through a clean new run; an interrupted run MUST fail explicitly and its partial output MUST NOT be treated as a completed stream. Critical paths MUST expose errors, warnings, health status, confidence, uncertainty, and evidence through a versioned run-summary/diagnostics record beside the canonical JSONL; diagnostics MUST NOT be encoded as battery events.
- **FR-033**: The same downstream tracking, measurement, counting, and event behavior MUST be usable with live detections or a cached deterministic replay source.
- **FR-034**: Replay MUST operate without loading a trained detector or requiring specialized acceleration and MUST produce the same summary on repeated runs over the same inputs and configuration.
- **FR-035**: Processing MUST fail before or at the first invalid input when configuration is missing, a video and declared resolution disagree, timestamps regress, events cannot be represented, volumes are invalid, or a track would be counted twice.
- **FR-036**: Every run MUST produce a versioned run-summary/diagnostics record containing the recording and resolution, frames processed, lot count, lot volume, unique tracks, counted track identities, observed processing rate, health status, warnings, errors, and replay-evidence references.
- **FR-037**: Paired-resolution comparison MUST report count gap and relative volume gap for the same physical video under the same canonical camera and gate configuration.
- **FR-038**: Relative volume error, duplicate rate, count error, resolution volume gap, and uncertainty calibration MUST be evaluated whenever the traceable golden set supports them; unsupported metrics MUST be marked `not_available`.
- **FR-039**: The golden set MUST trace manual count, relevant frame intervals, 10–20 operational tracks, marked occlusions, and catalog or volume truth only where independently verifiable.
- **FR-040**: Paired 720p and 1080p recordings of one physical video MUST remain in the same data partition, and consecutive frames from a physical video MUST NOT cross training, validation, or test boundaries.
- **FR-041**: Videos 01–03 MUST form the training partition, video 04 the validation partition, and video 05 the test partition for this feature.
- **FR-042**: The downstream handoff MUST include the three event examples, each carrying `schema_version: 1`, fixed key sets, a canonical fixture of at least 20 events, a versioned run-summary/diagnostics example, state definitions, null semantics, original-frame coordinate semantics, `run_id`, `event_id`, sequence definitions, one `TRACK_UPDATE` per processed frame for each active track, exactly-once delivery/count semantics, compatibility policy, and clean replay instructions.
- **FR-043**: Downstream consumers MUST be able to process the handoff without importing or depending on internal vision, geometry, catalog, or tracker state.
- **FR-044**: Configuration thresholds and operational choices MUST be explicit, reviewable, and free of hidden global state or unexplained magic values.
- **FR-045**: The final release evidence MUST identify the integrated revision, contributing work, active detector mode, artifact checksums, data partitions, configuration, exact demo procedure, known limitations, and freeze time without storing private videos, raw frames, credentials, or large runtime caches in version control.

### Constitutional Quality Constraints

- **CQ-001 — Architecture-first boundaries**: The Model Core MUST remain separable into camera preprocessing, vision, tracking, geometry, catalog inference, counting and metrics, and integration contracts. Dependencies MUST point toward stable core rules, and downstream features MUST consume only structured contracts.
- **CQ-002 — SOLID and Clean Code**: Each production unit MUST have one coherent responsibility, depend on the smallest useful abstraction, expose side effects, avoid duplicated business rules, and remain replaceable without changing unrelated domain behavior.
- **CQ-003 — Test-first development**: Every behavior, defect correction, or behavior-changing refactor MUST begin with a meaningful failing test, proceed with the smallest passing change, and retain recorded Red-Green-Refactor evidence.
- **CQ-004 — Required verification**: Applicable unit, contract, integration, deterministic model/fixture, and end-to-end replay tests MUST pass together with formatting, linting, static/type checks, compatibility checks, and review of test-first evidence before merge.
- **CQ-005 — Evidence integrity**: Training, validation, and test evidence MUST remain traceable and leakage-free; ambiguous catalog identity and unsupported metrics MUST stay explicit.
- **CQ-006 — Honest behavior**: The product MUST distinguish validated physical results from fallbacks, expose uncertainty and operational warnings, and identify all PLC behavior as simulated.
- **CQ-007 — P0 protection**: Stable replay, persistent identity, exactly-once counting, catalog-derived volume, uncertainty, both resolutions, resolution comparison, immutable release evidence, and demo backup MUST NOT be cut to make room for stretch work.

### Verification Coverage

- **FR-001–FR-009** are accepted through the paired-video validation flow, original-coordinate checks, and empty-frame scenario in User Story 1.
- **FR-010–FR-017** are accepted through the deterministic occlusion, reacquisition, directed-crossing, false-positive, and repeat-visibility fixture in User Story 2.
- **FR-018–FR-025** are accepted through calibrated synthetic cases, at least 10 reviewed real observations, catalog normalization cases, and ambiguity checks in User Story 4.
- **FR-026–FR-035** are accepted through the 20-event consumer fixture, invalid-record cases, and two-run deterministic replay in User Story 3.
- **FR-036–FR-045** are accepted through the full paired-resolution run, golden-set audit, downstream handoff rehearsal, and release-evidence review in User Stories 1, 3, and 4.
- **CQ-001–CQ-007** are accepted through boundary review, compatibility checks, recorded Red-Green-Refactor evidence, applicable quality gates, evidence audit, and demo-claim review before merge.

### Key Entities

- **Video Pair**: Two aligned recordings of the same physical scene at 1080p and 720p, with explicit filenames, partition assignment, duration, frame count, frame rate, and camera identity.
- **Frame Metadata**: Recording identity, resolution, zero-based frame identifier, monotonic timestamp, original dimensions, and camera identity for one observation point.
- **Battery Detection**: One frame-level battery hypothesis with original-frame box, mask polygon, confidence, and class.
- **Battery Track**: Persistent operational identity, lifecycle state, observation history, predicted position, visibility, counted flag, and accumulated evidence for one physical battery.
- **Frame Measurement**: Length, width, geometric uncertainty, and quality evidence derived from one eligible track observation.
- **Catalog Entry**: Stable identity, positive length, width, and height, plus all categories associated with an exact dimension set.
- **Catalog Candidate Set**: Ranked candidate entries and their normalized probabilities for one battery track, including explicit ambiguity.
- **Volume Estimate**: Expected liters, uncertainty interval, confidence, and supporting measurement quality for one track.
- **Count Gate**: Resolution-independent line, valid flow direction, and crossing semantics that authorize a single lot contribution.
- **Lot**: Unique counted track identities, frozen per-track volumes, current item count, and accumulated volume.
- **Domain Event**: Version-compatible external record with run and event identities, monotonic sequence, and schema version, representing a track update, occlusion, or exactly-once count without exposing internal library objects.
- **Run Summary**: Processing outcome and health for one recording, including frames processed, unique tracks, counted tracks, lot totals, and observed rate.
- **Resolution Comparison**: Paired 1080p/720p outcome containing count gap, relative volume gap, metric availability, and links to source summaries.
- **Golden-Set Evidence**: Traceable manual crossing, frame interval, track, occlusion, and independently verified catalog or volume annotations.
- **Release Evidence**: Immutable manifest, checksums, configuration identity, revisions, active fallback status, known limitations, and reproducible demo/replay procedure.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: At least one complete physical video and its paired resolution finish in a single unattended execution each, and the two full runs complete within the 40-minute real-execution window allocated by the delivery plan on the target demo environment.
- **SC-002**: In every validated run, 100% of counted operational identifiers appear in exactly one counted event, the lot count equals the number of those unique identifiers, and lot volume equals the sum of their frozen volumes within the published tolerance.
- **SC-003**: The deterministic acceptance fixture yields exactly one count for the battery that crosses, zero counts for the battery that does not cross, preserves one identity across the defined occlusion and reacquisition, rejects the short false positive, and produces an identical summary across two consecutive replays.
- **SC-004**: 100% of reported volume results are finite and positive and include confidence in the range 0–1 plus an ordered uncertainty interval; 100% of unsupported physical results are null and cannot trigger a counted-volume event.
- **SC-005**: 100% of delivered event records pass the published fixed-key contract checks, carry the declared schema version, use monotonic timestamps, contain no non-finite numbers, obey null semantics, contain no undeclared fields, and contain no empty track identity.
- **SC-006**: A 1080p/720p pair produces both count gap and relative volume gap; all evidence-dependent metrics are either computed from traceable truth or explicitly marked unavailable in 100% of cases.
- **SC-007**: An audit sample of 10–20 tracks is traceable to video, frame range, operational identity, occlusion evidence, count decision, and available catalog evidence, with no invented label.
- **SC-008**: At least 10 real observations and all calibrated synthetic cases are reviewable for physical dimension evidence; truncated or invalid cases are visibly rejected or assigned lower quality.
- **SC-009**: The interface team can consume the canonical JSONL fixture of at least 20 events and the versioned run-summary/diagnostics record, then replay a real event stream with one `TRACK_UPDATE` per processed frame for each active track using only the external contract, with zero dependencies on internal model or tracker objects.
- **SC-010**: A cached sequence of 300–900 frames can be replayed without specialized acceleration or a trained detector, and replay remains available as the demonstrated backup path after code freeze.
- **SC-011**: In a technical rehearsal, an operator can start the selected run, validate its result, and start the backup replay in under 10 minutes using the documented procedures and without changing source code.
- **SC-012**: 100% of demo-facing outputs that refer to PLC behavior identify it as simulated, and 100% of runs without trusted physical calibration visibly state that absolute volume is unvalidated.
- **SC-013**: Before merge, every changed behavior has recorded failing-then-passing test evidence and all applicable tests, contract checks, static checks, and review gates pass with no hidden skips or failures.

## Assumptions

- The source inventory remains five aligned 1080p/720p pairs totaling 44,788 frames per resolution and approximately 24.9 minutes per resolution.
- The raw catalog remains available with 95 rows, 67 unique dimension triples, 11 categories, and one known comma-decimal height that must be parsed explicitly.
- A trusted conveyor or tray dimension and four physical reference points will be supplied within the initial calibration window. If they are not, the documented simplified-calibration or pixel-only fallback applies for non-validated inspection only and cannot authorize a counted-volume event.
- The same physical camera viewpoint and conveyor geometry apply to each paired-resolution comparison.
- The external consumer will approve any additive event version field before it is introduced; existing event names, fields, and meanings remain frozen until that compatibility decision.
- API delivery, persistence, dashboard presentation, VLM explanations, and simulated PLC display are being delivered by separate features; this feature ends at validated structured events, summaries, evidence, and handoff.
- Large/private media, learned weights, generated frames, runtime caches, and credentials remain external to version control and are referenced through controlled manifests and checksums.
- The five-hour delivery window makes the deterministic replay path the acceptance baseline; model, tracker, or calibration improvements may replace fallbacks only when they preserve contracts and do not threaten P0 stability.
- Target users are the operations demonstrator, technical evaluator, and downstream interface integration team; no public end-user workflow is introduced by this backend feature.

### Dependencies

- Read access to the ten source recordings, the raw battery catalog, and their explicit pair manifest.
- A trustworthy physical reference for the target camera, or an explicitly documented fallback that disables validated absolute-volume claims.
- A target execution environment capable of completing the full paired run within the allocated delivery window and preserving replay evidence.
- Timely confirmation from the interface team for event compatibility, fixture consumption, update cadence, and any additive version field.
- Separate interface and simulated-PLC features that consume the published events without expanding this feature into presentation or control logic.
