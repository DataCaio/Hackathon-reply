# Contract: User Story 3 Replay

## Inputs

Replay consumes:

1. A canonical UTF-8 JSONL battery-event stream conforming to [events.md](events.md).
2. One versioned run-summary/diagnostics record conforming to [diagnostics.md](diagnostics.md).

The replay consumer does not load a detector, GPU model, tracker vendor, geometry implementation, catalog, API server, or PLC adapter.

## Behavior

- Read one line at a time and preserve canonical line order, including ties at the same timestamp.
- Validate fixed keys, schema versions, finite numeric values, state values, nullability, timestamp order, and exactly-once counted identities.
- Surface the first invalid record with its line number, event type, track ID when available, and diagnostic code.
- Preserve valid partial evidence when an input ends early. The producer/summary must explicitly mark that run `PARTIAL`; replay preserves that status and never guesses `COMPLETE` from an abruptly short stream.
- Produce the same canonical event sequence and semantic summary on repeated runs with the same inputs and configuration.
- Normalize or exclude runtime-only `processing_fps` when comparing deterministic replay summaries.

The reference implementation writes a canonical replay JSONL file and a result JSON file containing the event count, event/type and identity sets, and the normalized summary. It uses only the standard library and does not load a detector, tracker, GPU, cloud SDK, or PLC adapter.

## Acceptance fixtures

The User Story 3 fixture must contain at least 20 events and cover:

- fixed-key `TRACK_UPDATE` records with unavailable physical values represented as `null`;
- one update per processed frame for an active track;
- a transition-only `TRACK_OCCLUDED` record followed by hidden-frame updates;
- reacquisition evidence and a `REACQUIRED` state;
- exactly one `BATTERY_COUNTED` record with a frozen volume and interval;
- continued visibility after counting without a second counted record;
- a terminal loss transition or an explicit partial-run diagnostic;
- a versioned summary with health, warning/error arrays, lot invariants, and replay evidence.

## Consumer boundary

The consumer test imports only the published contracts and fixture files. It must not import internal detector, tracker, geometry, catalog, pipeline, or PLC modules. A wrapper transport may be tested separately, but it must hand the same canonical event objects to the consumer contract.
