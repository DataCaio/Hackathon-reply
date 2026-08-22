# Contract: Run Summary and Diagnostics

**Status**: Normative companion record for User Story 3

## Purpose and boundary

This record reports run-level health, warnings, errors, lot totals, and replay evidence without expanding the battery event enum. It is emitted once per run beside the canonical battery JSONL and may be consumed independently by the interface.

## Fixed keys

| Key | Type | Constraint |
|---|---|---|
| `summary_schema_version` | integer | Exactly `1` for the initial summary contract. |
| `video_id` | string | Explicit manifest identifier. |
| `resolution` | string | `720p` or `1080p`. |
| `frames_processed` | integer | Non-negative. |
| `lot_count` | integer | Equals unique counted identities. |
| `lot_volume_l` | number or null | Null when validated absolute volume is unavailable. |
| `unique_tracks` | integer | Non-negative. |
| `counted_track_ids` | array[string] | Unique `battery-xxxx` values. |
| `processing_fps` | number or null | Observed rate; deterministic replay may set this to null. |
| `health_status` | string | `HEALTHY`, `DEGRADED`, or `FAILED`. |
| `run_status` | string | `COMPLETE`, `PARTIAL`, or `FAILED`. |
| `warnings` | array[Diagnostic] | Non-fatal structured conditions. |
| `errors` | array[Diagnostic] | Fatal or failed-run structured conditions. |
| `replayable` | boolean | Whether the available evidence can be replayed deterministically. |
| `replay_evidence_refs` | array[string] | Relative, non-sensitive evidence references. |

Each `Diagnostic` has the fixed keys `code`, `message`, `frame_id`, and `recoverable`. `frame_id` may be `null` when the condition is run-level rather than frame-level.

## Invariants

- `lot_count` equals the number of unique values in `counted_track_ids`.
- A `COMPLETE` run has no fatal errors; a `PARTIAL` run identifies missing or interrupted evidence; a `FAILED` run identifies the first fatal condition when known.
- `FAILED` or `PARTIAL` does not imply that all emitted JSONL is invalid. `replayable` states whether the partial evidence can be safely replayed.
- Runtime telemetry such as `processing_fps` is not used when comparing deterministic replay summaries; canonical replay comparisons ignore or normalize that field.
- Diagnostics never appear as `TRACK_UPDATE`, `TRACK_OCCLUDED`, or `BATTERY_COUNTED` lines.
- When battery events are present, the validator cross-checks `counted_track_ids`, `lot_count`, `unique_tracks`, and `lot_volume_l` against the event stream's frozen count records.
- The summary itself is strict: missing or undeclared keys, invalid statuses, non-finite numbers, and invalid identity lists fail contract validation.

## Example

```json
{
  "summary_schema_version": 1,
  "video_id": "video_03",
  "resolution": "720p",
  "frames_processed": 21,
  "lot_count": 1,
  "lot_volume_l": 7.94,
  "unique_tracks": 1,
  "counted_track_ids": ["battery-0017"],
  "processing_fps": 34.2,
  "health_status": "HEALTHY",
  "run_status": "COMPLETE",
  "warnings": [
    {
      "code": "SIMULATED_PLC_DISPLAY",
      "message": "PLC-oriented display is simulated; Model Core does not control hardware.",
      "frame_id": null,
      "recoverable": true
    }
  ],
  "errors": [],
  "replayable": true,
  "replay_evidence_refs": ["events/video_03_720p.jsonl"]
}
```
