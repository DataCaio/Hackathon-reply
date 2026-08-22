# Hackathon Reply

## User Story 3 event handoff

The stable Model Core boundary is published as three versioned battery events in
canonical UTF-8 JSONL: `TRACK_UPDATE`, `TRACK_OCCLUDED`, and `BATTERY_COUNTED`.
Health, warnings, errors, lot invariants, and replay evidence live in the
versioned `summary.json` sidecar. Consumers use the fixed keys and explicit
`null` semantics without importing detector, tracker, geometry, catalog,
pipeline, API, or PLC modules.

Validate the checked-in fixture with:

```bash
uv run python scripts/validate_events.py \
  --input tests/fixtures/user_story3/events.jsonl \
  --summary tests/fixtures/user_story3/summary.json
```

Replay it with `uv run python scripts/replay_events.py` using the arguments in
[`specs/001-backend-model-core/quickstart.md`](specs/001-backend-model-core/quickstart.md).
The PLC-oriented display is simulated; Model Core never controls or claims real
PLC state. This handoff is CPU/local and does not require AWS, credentials, or
`AWS.sh`.

The merged backend branch also includes the deterministic User Story 2 replay
(`scripts/replay_story2.py`) and User Story 4 catalog/geometry/audit path
(`scripts/audit_story4.py`).
