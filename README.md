# Hackathon Reply backend

This branch contains the merged backend work for User Stories 1–4:

- US1: replay-first paired-resolution processing, trusted calibration, catalog-derived volume with uncertainty, persistent identity, exactly-once lot counting, and comparison.
- US2: deterministic tracking/counting replay in `scripts/replay_story2.py`.
- US3: versioned canonical event handoff, diagnostics, consumer fixture, validator, and replay in `scripts/validate_events.py` and `scripts/replay_events.py`.
- US4: catalog, geometry, metrics, and audit path in `scripts/audit_story4.py`.

## US1 replay quickstart

Install the project and development checks with Python 3.14:

```powershell
uv sync --extra dev
```

Run the trusted deterministic fixture:

```powershell
python scripts/run_video.py `
  --detections tests/fixtures/user_story_1/detections.jsonl `
  --events artifacts/us1-1080-events.jsonl `
  --summary artifacts/us1-1080-summary.json `
  --run-id us1-1080 `
  --calibration tests/fixtures/user_story_1/trusted_calibration.json `
  --catalog tests/fixtures/user_story_1/catalog.csv
```

Run the 720p fixture with the same command and `detections_720p.jsonl`, then compare the summaries:

```powershell
python scripts/compare_resolutions.py `
  --high artifacts/us1-1080-summary.json `
  --low artifacts/us1-720-summary.json
```

Each successful US1 event stream has a `.jsonl.complete` sidecar. An interrupted or failed run has no completion marker and must be replayed to a new output path; output is never resumed.

Without trusted physical calibration, processing and identity tracking may continue, but millimeter dimensions and absolute liters remain unavailable and no `BATTERY_COUNTED` event is emitted.

## US3 event handoff

The stable Model Core boundary is published as three versioned battery events in canonical UTF-8 JSONL: `TRACK_UPDATE`, `TRACK_OCCLUDED`, and `BATTERY_COUNTED`. Health, warnings, errors, lot invariants, and replay evidence live in the versioned summary sidecar. Consumers use fixed keys and explicit `null` semantics without importing detector, tracker, geometry, catalog, pipeline, API, or PLC modules.

Validate the checked-in US3 fixture with:

```bash
uv run python scripts/validate_events.py \
  --input tests/fixtures/user_story3/events.jsonl \
  --summary tests/fixtures/user_story3/summary.json
```

Replay it using the arguments in [`specs/001-backend-model-core/quickstart.md`](specs/001-backend-model-core/quickstart.md). PLC-oriented behavior is simulated; Model Core never controls or claims real PLC state. The handoff is CPU/local and requires no AWS, credentials, or `AWS.sh`.

## Verification

```powershell
python -m pytest -q -p no:cacheprovider
ruff check src tests scripts
mypy --explicit-package-bases src/hackathon_reply scripts
```

Raw videos, model weights, generated frames, replay outputs, credentials, and runtime caches are excluded from version control.
