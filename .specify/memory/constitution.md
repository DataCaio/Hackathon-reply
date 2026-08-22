<!--
Sync Impact Report
- Version change: unversioned scaffold -> 1.0.0
- Modified principles:
  - PRINCIPLE_1_NAME -> I. Architecture-First, Contract-Driven Boundaries
  - PRINCIPLE_2_NAME -> II. SOLID and Clean Code
  - PRINCIPLE_3_NAME -> III. Test-First Development (TDD, NON-NEGOTIABLE)
  - PRINCIPLE_4_NAME -> IV. Evidence-First Vision and Measurement Integrity
  - PRINCIPLE_5_NAME -> V. Observable, Reliable, and Honest Product Behavior
- Added sections:
  - Project Architecture & Technical Constraints
  - Development Workflow & Quality Gates
- Removed sections: none
- Follow-up TODOs: none
-->

# Hackathon Reply Constitution

## Core Principles

### I. Architecture-First, Contract-Driven Boundaries

The system MUST preserve the explicit processing direction:
video -> camera preprocessing -> segmentation -> tracking -> geometry -> catalog
inference -> count gate -> events -> persistence and UI. Each stage MUST own one
coherent decision and expose a documented contract. Dependencies MUST point from
outer adapters toward stable core logic; domain rules MUST NOT depend directly on
FastAPI, Streamlit, storage engines, tracker vendors, or model runtimes.

The vision core, geometry and catalog logic, counting engine, event contract,
backend adapters, persistence adapters, and UI adapters MUST remain separable and
independently testable. API and UI code MUST consume structured contracts rather
than reach into another component's internal state. A contract change MUST include
updated contract tests and an explicit compatibility decision.

Rationale: clear boundaries enable parallel work by the team, safe replacement of
models and infrastructure, and reliable integration of the Model Core with the
Interface.

### II. SOLID and Clean Code

All production code MUST follow SOLID and Clean Code rules:

- Single Responsibility: each module, class, and function MUST have one reason to
  change.
- Open/Closed: new model, catalog, storage, or presentation variants MUST be
  added through stable interfaces or adapters instead of modifying unrelated
  business rules.
- Liskov Substitution: implementations MUST preserve the behavior promised by
  their contracts, including units, error semantics, and state transitions.
- Interface Segregation: consumers MUST depend only on the smallest interface
  that serves their use case.
- Dependency Inversion: core decisions MUST depend on abstractions; concrete
  frameworks, files, databases, and external services MUST be injected at the
  boundary.

Names MUST reveal intent. Functions and classes MUST be small enough to reason
about, side effects MUST be explicit, duplicated business rules MUST be removed,
and comments MUST explain why rather than restate what the code already says.
Hidden global state, magic thresholds, deep call chains, dead code, and speculative
abstractions MUST NOT be introduced. Linting, formatting, type checking, and code
review MUST enforce these rules.

Rationale: readable, replaceable code reduces debugging time and prevents the
hackathon schedule from turning temporary shortcuts into permanent architecture.

### III. Test-First Development (TDD, NON-NEGOTIABLE)

Tests MUST be written before implementation for every feature, bug fix, behavior
change, pipeline rule, and refactor that changes behavior. The author MUST run the
new or changed test and observe a meaningful failure before writing the production
implementation. The implementation MUST then be the smallest change that makes
the test pass, followed by refactoring while the full relevant suite remains
green. This is the required Red-Green-Refactor cycle.

Every change MUST include the appropriate tests:

- unit tests for deterministic geometry, catalog, uncertainty, counting, and
  state-transition rules;
- contract tests for event payloads, API responses, configuration, and persisted
  records;
- integration tests for detector-to-tracker-to-geometry-to-volume flows and
  backend persistence;
- end-to-end tests for the replay path and critical dashboard behavior;
- deterministic model or fixture tests for inference and evaluation code, with
  expensive training kept outside the normal test suite.

No failing test, skipped test, unrecorded test-data leak, or unverified assertion
MAY be hidden to obtain a green build. Each change record MUST preserve enough
evidence to show the test-first failure and the final passing result.

Rationale: TDD converts the vision pipeline's acceptance criteria into executable
contracts and makes fast parallel development safe.

### IV. Evidence-First Vision and Measurement Integrity

The MVP MUST segment batteries per frame, reason over persistent tracks, measure
geometry, infer candidates from the catalog, and aggregate volume per lot. It MUST
NOT train a direct black-box volume regression model as the core solution.

The paired 720p and 1080p recordings of one physical video MUST be treated as a
single split unit. Consecutive frames from one video MUST NOT cross train,
validation, or test boundaries, and paired resolutions MUST never be separated
across those boundaries. Ambiguous catalog identity MUST be reported as
ambiguous with valid candidates; labels MUST NOT be invented.

Every volume result MUST carry an uncertainty representation, such as confidence
and an interval derived from catalog probabilities and measurement quality. The
evaluation MUST report relative volume error, duplicate rate, count error,
resolution volume gap, and uncertainty calibration whenever the available golden
set supports the metric. The golden set MUST be traceable to video, frame, track,
occlusion, and catalog evidence.

Rationale: the product claim is explainable volume estimation that remains useful
across resolutions, not an opaque detector score.

### V. Observable, Reliable, and Honest Product Behavior

Tracking MUST use a persistent Battery UUID independent of any internal tracker
ID. A track MUST pass the configured count gate before it is counted, and the same
UUID MUST contribute to the lot exactly once. Occlusion MUST be represented as a
state transition with reacquisition evidence rather than treated as object loss.

Every externally visible state change MUST be emitted through a versioned,
structured event contract. Critical paths MUST expose health, errors, confidence,
uncertainty, and replayable evidence. Thresholds MUST be configuration-driven and
the UI MUST make warnings and pauses understandable to an operator.

The PLC is simulated. The UI, API, documentation, and pitch MUST label it as a
simulation and MUST NOT imply real hardware integration. The VLM assistant MAY
explain structured results and uncertainty, but MUST NOT perform segmentation,
tracking, volume calculation, or count-gate decisions.

Rationale: trustworthy behavior is more valuable than an impressive but
irreproducible demo, especially when uncertainty can affect operational action.

## Project Architecture & Technical Constraints

The canonical MVP architecture consists of these boundaries:

- camera preprocessing: ROI, calibration, perspective correction, and canonical
  image space;
- vision: YOLO-Seg masks and confidence;
- tracking: ByteTrack integration, persistent UUIDs, occlusion, and reacquisition;
- geometry: mask contour, rotated rectangle, pixel-to-millimeter conversion, and
  measurement quality;
- catalog: probabilistic L/W matching, candidate posterior, expected volume, and
  uncertainty;
- counting and metrics: count gate, exactly-once lot aggregation, RVE, duplicate
  rate, count error, RVG, and calibration checks;
- integration: JSON events, FastAPI endpoints, persistence, and replay;
- interface: Streamlit dashboard, annotated video, operator controls, and VLM
  explanations.

The planned technology choices are YOLO-Seg, ByteTrack, Python, FastAPI,
Streamlit, and SQLite or JSONL persistence. Replacing one of these choices MUST
preserve the boundary contracts and MUST be justified by tests and an architecture
decision record. The repository SHOULD keep configuration, data, models, source
boundaries, scripts, and tests visibly separated; tests MUST remain outside
production modules.

The available data consists of five unique 1080p videos, five perfectly paired
720p videos, battery dimensions, and conveyor or tray measurements. There are no
ready-made labels, no real PLC, and no individual mass measurements. The core
challenge MUST therefore remain focused on battery detection, tracking, geometry,
catalog-constrained volume, uncertainty, and resolution robustness.

## Development Workflow & Quality Gates

Work MUST move through the following sequence:

1. State the behavior, contract, metric, or acceptance criterion.
2. Write the failing unit, contract, integration, or end-to-end test.
3. Run the test and record the failure.
4. Implement the smallest SOLID-compatible change.
5. Run the focused tests, then the full relevant suite.
6. Refactor for Clean Code while tests remain green.
7. Evaluate on traceable fixtures and the paired-resolution comparison.
8. Review the diff for boundary violations, duplicate counting, uncertainty loss,
   security, and demo stability.

Before merge, the change MUST pass the applicable test suite, linting and
formatting, type or static checks, contract compatibility checks, and review of
the test-first evidence. Vision changes MUST include reproducible evaluation
metrics; API or event changes MUST include contract tests; UI changes MUST include
critical-state coverage for loading, error, uncertainty, warning, pause, and
replay behavior.

The MVP priority order is P0 demo existence, P1 quality and robustness, and P2
stretch work. P2 work MUST NOT delay a stable P0 path. A feature MUST be cut when
it does not improve volume, tracking, resolution robustness, or the explainable
demo, or when it threatens replay stability. After the demo code freeze, the team
MUST use the known replay path and MUST NOT introduce a new model, large
dependency, or architecture refactor.

The Definition of Done requires at least one complete video replay, battery
detection, persistent IDs, demonstrated occlusion handling, exactly-once count,
catalog-derived volume, uncertainty, 720p and 1080p execution, RVG calculation,
real event delivery to the interface, an explicitly simulated PLC display, and a
known demo replay with a backup recording.

## Governance

This constitution is the project's governing quality contract. It supersedes
conflicting development habits and MUST be read by every implementation,
planning, review, and testing workflow. The constitution is stored at
`.specify/memory/constitution.md`; changes to application code MUST NOT weaken it
silently.

Amendments MUST be proposed as a reviewed change to this file, include a Sync
Impact Report, explain the effect on existing work, and update affected specs,
plans, tasks, and tests through the appropriate Spec Kit workflow. A deviation is
not a waiver: any rule that must change requires an approved constitution
amendment before the dependent implementation is merged.

Versioning follows Semantic Versioning:

- MAJOR for removing or redefining a non-negotiable principle;
- MINOR for adding a principle or materially expanding governance;
- PATCH for clarifications, wording, or non-semantic corrections.

Every pull request or equivalent review MUST verify architecture boundaries,
SOLID and Clean Code compliance, test-first evidence, relevant quality gates, and
the project's measurement and honesty requirements. Reviewers MUST reject changes
that implement first and test later, bypass the count gate, leak paired-video
data, hide uncertainty, or present simulated functionality as real.

**Version**: 1.0.0 | **Ratified**: 2026-08-22 | **Last Amended**: 2026-08-22
