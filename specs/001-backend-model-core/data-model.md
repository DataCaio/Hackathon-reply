# Data Model: User Story 3 Event Boundary

This model covers only the records consumed or emitted by the stable event boundary. Upstream detections, tracks, measurements, catalog posteriors, and count-gate internals remain owned by their respective features and enter this boundary through documented adapters.

## 1. Common domain-event envelope

Every battery event is one JSON object with the following fixed keys:

| Field | Type | Rules |
|---|---|---|
| `event` | string | One of `TRACK_UPDATE`, `TRACK_OCCLUDED`, `BATTERY_COUNTED`. |
| `schema_version` | integer | Exactly `1` for the initial contract. Breaking changes increment it. |
| `timestamp_ms` | integer | Source timestamp; nondecreasing in canonical JSONL order. |
| `video_id` | string | Explicit manifest identifier; never inferred from filename casing. |
| `resolution` | string | `720p` or `1080p`. |
| `track_id` | string | Operational UUID in the `battery-xxxx` form; never an internal tracker ID. |

Every event type adds its own fixed keys. All declared keys are present. An unavailable applicable value is `null`; an undeclared key is invalid in the MVP. Numeric values must be finite JSON numbers, never `NaN` or `Infinity`.

## 2. Track update

`TRACK_UPDATE` is emitted once per processed frame for every active track (any track not in `LOST`). Its fixed keys are:

| Field | Type | Rules |
|---|---|---|
| `state` | string | `DETECTED`, `TRACKING`, `OCCLUDED`, `REACQUIRED`, `COUNTED`, or `LOST`; an active update normally has a non-`LOST` state. |
| `bbox` | array[4] or null | Original-frame pixel coordinates `[x_min, y_min, x_max, y_max]` when available; null when the active track has no current box. |
| `mask_confidence` | number or null | Range `[0,1]`; null when no mask confidence exists. |
| `visibility` | number | Range `[0,1]`. |
| `length_mm` | number or null | Physical length when measurement is available. |
| `width_mm` | number or null | Physical width when measurement is available. |
| `geometry_uncertainty_mm` | number or null | Non-negative measurement uncertainty when available. |
| `volume_l` | number or null | Catalog-derived volume in liters; null until valid physical evidence exists. |
| `volume_ci95_l` | array[2] or null | Ordered `[low, high]` interval when volume is available. |
| `volume_confidence` | number | Range `[0,1]`; `0.0` when no usable volume evidence exists. |
| `counted` | boolean | Whether this operational identity has already contributed to the lot. |

The event preserves the latest trustworthy posterior but does not retroactively change a previously emitted `BATTERY_COUNTED` contribution.

## 3. Track occlusion

`TRACK_OCCLUDED` marks a temporary visibility loss and uses these additional fixed keys:

| Field | Type | Rules |
|---|---|---|
| `state` | string | Exactly `OCCLUDED`. |
| `predicted_position` | array[2] or null | Predicted original-frame center when available. |
| `last_volume_l` | number or null | Last trustworthy catalog-derived volume. |
| `volume_confidence` | number | Range `[0,1]`; reflects the last trustworthy evidence. |

An occlusion event is emitted on the transition into `OCCLUDED`, not once per every hidden frame. Subsequent per-frame `TRACK_UPDATE` records carry the `OCCLUDED` state while the track remains active. An occlusion event does not create a new identity, count a battery, or erase the previous posterior.

## 4. Battery counted

`BATTERY_COUNTED` freezes a valid lot contribution and uses these additional fixed keys:

| Field | Type | Rules |
|---|---|---|
| `state` | string | Exactly `COUNTED`. |
| `volume_l` | number | Finite and strictly positive; frozen for the lot. |
| `volume_ci95_l` | array[2] | Ordered interval containing the reported uncertainty. |
| `volume_confidence` | number | Range `[0,1]`. |
| `lot_count` | integer | Current number of unique counted operational identities. |
| `lot_volume_l` | number | Sum of frozen counted volumes within the published numeric tolerance. |

The same `track_id` may have many updates but at most one counted event in a run.

## 5. Run-summary/diagnostics record

The battery JSONL remains limited to the three domain-event types. Each run also produces one versioned JSON summary/diagnostics record:

| Field | Type | Rules |
|---|---|---|
| `summary_schema_version` | integer | Exactly `1` for the initial summary contract. |
| `video_id` | string | Explicit recording identifier. |
| `resolution` | string | `720p` or `1080p`. |
| `frames_processed` | integer | Non-negative count. |
| `lot_count` | integer | Number of unique counted identities. |
| `lot_volume_l` | number or null | Sum of valid frozen volumes; null when absolute volume is unvalidated. |
| `unique_tracks` | integer | Non-negative number of operational identities observed. |
| `counted_track_ids` | array[string] | Unique `battery-xxxx` values, matching `lot_count`. |
| `processing_fps` | number or null | Observed processing rate when measurable. |
| `health_status` | string | `HEALTHY`, `DEGRADED`, or `FAILED`. |
| `run_status` | string | `COMPLETE`, `PARTIAL`, or `FAILED`. |
| `warnings` | array[Diagnostic] | Structured non-fatal conditions. |
| `errors` | array[Diagnostic] | Structured fatal or failed-run conditions. |
| `replayable` | boolean | Whether the recorded evidence can be replayed deterministically. |
| `replay_evidence_refs` | array[string] | Relative artifact references; no credentials or private media contents. |

`Diagnostic` has fixed keys `code` (string), `message` (string), `frame_id` (integer or null), and `recoverable` (boolean). Diagnostics are not battery events and must not be inserted into the canonical battery JSONL. Deterministic replay comparisons normalize or ignore runtime-only `processing_fps`; all other summary fields must match.

## 6. Relationships and invariants

- One run has one summary/diagnostics record and zero or more battery event lines.
- One `track_id` owns an ordered sequence of `TRACK_UPDATE` and optional `TRACK_OCCLUDED` records and at most one `BATTERY_COUNTED` record.
- `counted_track_ids` contains exactly the identities represented by `BATTERY_COUNTED` lines.
- `lot_count` equals the cardinality of `counted_track_ids`; `lot_volume_l` equals the sum of their frozen `volume_l` values when all contributions are valid.
- Event timestamps are nondecreasing in line order. Within equal timestamps, the producer's line order is preserved; replay must not reorder records.
- The validator rejects missing fixed keys, undeclared keys, invalid enums, invalid UUIDs, null counted volumes, non-finite numbers, malformed intervals, timestamp regressions, and duplicate counted identities.
- The summary may report `DEGRADED` or `FAILED` while still remaining structurally valid and replayable when the evidence permits.
- `COMPLETE` means the declared input finished; `PARTIAL` means output stopped with identifiable partial evidence; `FAILED` means a fatal condition prevented a valid completion.
