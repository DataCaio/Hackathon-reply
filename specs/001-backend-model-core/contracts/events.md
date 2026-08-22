# Contract: Battery Domain Events

**Status**: Normative for User Story 3

## Boundary

The Model Core emits exactly three battery event types:

- `TRACK_UPDATE`
- `TRACK_OCCLUDED`
- `BATTERY_COUNTED`

The interface and simulated PLC display consume these records. They do not import detector, tracker, geometry, catalog, or internal state objects. The Model Core never emits or decides `PLC_STATE`.

## Canonical serialization

- The normative handoff is UTF-8 JSONL.
- Each line contains exactly one complete JSON object.
- Blank lines, comments, `NaN`, `Infinity`, and malformed JSON are invalid.
- Every record carries `schema_version: 1` in the initial release.
- APIs or streams may wrap the same objects but must not alter field meaning or create a second schema.
- Fixed keys are required per event type. Every declared key must be present; unavailable applicable values are `null`; undeclared keys are invalid in the MVP.
- The reference validator reads one line at a time, reports the first invalid line with its diagnostic code, and rejects non-finite numbers before serialization.

## Common fixed envelope

Every event contains:

| Key | Constraint |
|---|---|
| `event` | One of the three event names above. |
| `schema_version` | Integer `1` until a breaking contract change. |
| `timestamp_ms` | Nondecreasing source timestamp in line order. |
| `video_id` | Explicit manifest identifier. |
| `resolution` | `720p` or `1080p`. |
| `track_id` | Operational ID matching `battery-xxxx`. |

## Fixed event keys

### `TRACK_UPDATE`

The common envelope plus:

`state`, `bbox`, `mask_confidence`, `visibility`, `length_mm`, `width_mm`, `geometry_uncertainty_mm`, `volume_l`, `volume_ci95_l`, `volume_confidence`, and `counted`.

`bbox` is `[x_min, y_min, x_max, y_max]` in original-frame pixels when available, or `null` when the active track has no current box. Physical fields may also be `null`; confidence and visibility remain bounded in `[0,1]`. Emit one update per processed frame for every active track (any track not in `LOST`). A final state transition to `LOST` may be emitted once, after which no further updates are emitted for that track.

### `TRACK_OCCLUDED`

The common envelope plus:

`state`, `predicted_position`, `last_volume_l`, and `volume_confidence`.

`state` is exactly `OCCLUDED`. Position and last volume may be `null` when unavailable. This record preserves identity and posterior evidence; it never counts a battery.

Emit `TRACK_OCCLUDED` on the transition into `OCCLUDED`. While the track remains active but hidden, continue emitting the per-frame `TRACK_UPDATE` records with `state: "OCCLUDED"`; do not repeat the transition event for every hidden frame.

### `BATTERY_COUNTED`

The common envelope plus:

`state`, `volume_l`, `volume_ci95_l`, `volume_confidence`, `lot_count`, and `lot_volume_l`.

`state` is exactly `COUNTED`. `volume_l` must be finite and strictly positive; the interval must be ordered; and the same `track_id` must not produce another counted record in the same run.

## Ordering and compatibility

- The producer writes records in processed-frame order.
- Timestamps may tie for records from the same frame; line order is preserved and replay must not reorder ties.
- A consumer must reject a timestamp regression, duplicate count identity, invalid state, missing fixed key, undeclared key, invalid numeric value, or invalid interval.
- A terminal transition to `LOST` may be represented by one final `TRACK_UPDATE`; no updates are emitted after the track is lost.
- Additive changes require interface approval and updated contract tests. The current v1 validator remains strict about undeclared keys until that fixed-key revision is delivered. Breaking changes increment `schema_version` and require a compatibility decision before delivery. The executable compatibility decisions are recorded under `tests/fixtures/user_story3/compat/`.

## Minimal examples

The examples below are illustrative records; the fixed key set is normative.

```json
{"event":"TRACK_UPDATE","schema_version":1,"timestamp_ms":123456,"video_id":"video_03","resolution":"720p","track_id":"battery-0017","state":"TRACKING","bbox":[410,205,502,291],"mask_confidence":0.94,"visibility":0.82,"length_mm":241.5,"width_mm":174.3,"geometry_uncertainty_mm":3.1,"volume_l":7.94,"volume_ci95_l":[7.41,8.05],"volume_confidence":0.83,"counted":false}
{"event":"TRACK_OCCLUDED","schema_version":1,"timestamp_ms":123490,"video_id":"video_03","resolution":"720p","track_id":"battery-0017","state":"OCCLUDED","predicted_position":[615,320],"last_volume_l":7.94,"volume_confidence":0.83}
{"event":"BATTERY_COUNTED","schema_version":1,"timestamp_ms":123620,"video_id":"video_03","resolution":"720p","track_id":"battery-0017","state":"COUNTED","volume_l":7.94,"volume_ci95_l":[7.41,8.05],"volume_confidence":0.83,"lot_count":1,"lot_volume_l":7.94}
```
