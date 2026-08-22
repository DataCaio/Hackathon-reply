# Quickstart: User Story 3 Event Handoff and Replay

This guide validates only the stable event boundary. It does not train a detector, run live tracking, calculate geometry, or control a PLC.

## Prerequisites

- A Python environment satisfying the repository declaration (`>=3.12`); the checked-in `.python-version` recommends 3.14.
- `uv` available to create the project environment.
- The User Story 3 fixture and summary generated at:
  - `tests/fixtures/user_story3/events.jsonl`
  - `tests/fixtures/user_story3/summary.json`
- No GPU, AWS instance, credential, API server, or `AWS.sh` invocation.

The current development shell reports Python 3.13.7 and satisfies the merged repository declaration.

## 1. Install the project test environment

```bash
uv sync
```

Expected result: the project resolves under the declared Python version and installs the test dependencies.

## 2. Run focused contract and replay tests

```bash
uv run pytest tests/contract tests/integration/test_user_story3_replay.py -q
```

Expected result: fixed-key, version, nullability, finite-number, state, cadence, diagnostics, and deterministic-replay tests pass. Tests must also retain Red-Green-Refactor evidence for changed behavior.

## 3. Validate the canonical JSONL fixture

```bash
uv run python scripts/validate_events.py \
  --input tests/fixtures/user_story3/events.jsonl \
  --summary tests/fixtures/user_story3/summary.json
```

Expected result: at least 20 event lines validate; every record has `schema_version: 1`, a fixed key set, finite numbers, valid states, nondecreasing timestamps, and no duplicate counted identity. The summary validates as a versioned `COMPLETE`, `PARTIAL`, or `FAILED` diagnostic record.

## 4. Replay twice and compare canonical results

```bash
uv run python scripts/replay_events.py \
  --input tests/fixtures/user_story3/events.jsonl \
  --summary tests/fixtures/user_story3/summary.json \
  --output /tmp/user-story3-replay-a.jsonl \
  --result /tmp/user-story3-result-a.json

uv run python scripts/replay_events.py \
  --input tests/fixtures/user_story3/events.jsonl \
  --summary tests/fixtures/user_story3/summary.json \
  --output /tmp/user-story3-replay-b.jsonl \
  --result /tmp/user-story3-result-b.json
```

Expected result: the two canonical event outputs and semantic summaries match. Runtime-only `processing_fps` is normalized or excluded from equality. The fixture demonstrates one update per processed frame for each active track, transition-only occlusion, reacquisition, exactly one count, and no count for an unqualified crossing.

## 5. Exercise the consumer boundary

Run the interface contract test against only the published fixture and contract documents:

```bash
uv run pytest tests/contract/test_consumer_fixture.py -q
```

Expected result: the consumer reads the JSONL and summary without importing vision, tracking, geometry, catalog, pipeline, API, or PLC modules. Any wrapper transport is tested as an adapter over the same canonical event objects.

The negative corpus under `tests/fixtures/user_story3/invalid/` is exercised by the integration test and must fail closed for missing/extra keys, schema drift, non-finite values, ordering regressions, invalid identities/states, duplicate counts, inconsistent lots, and a `COMPLETE` summary containing fatal interruption evidence.

## Failure checks

The validator must fail fast and identify the first offending line for:

- a missing or undeclared key;
- a schema version other than `1`;
- a missing `null` value or a numeric zero used where evidence is unavailable;
- `NaN`, `Infinity`, invalid confidence, or an unordered interval;
- timestamp regression or invalid state;
- an empty/non-operational track ID;
- a second `BATTERY_COUNTED` for the same identity;
- a summary whose lot totals disagree with counted events;
- an interrupted stream that is incorrectly labeled `COMPLETE`.

## Handoff checklist

Before the interface consumes the feature, deliver the three examples, the 20-event fixture, the versioned summary/diagnostics example, fixed key and nullability rules, update cadence, state enum, original-frame coordinate semantics, exactly-once semantics, and this replay command.

The release gate is the focused `uv run pytest` command plus two successful validator/replay CLI runs in a Python `>=3.12` environment. Python 3.14 remains the recommended reproducible interpreter from `.python-version`.
