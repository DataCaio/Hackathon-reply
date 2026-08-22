"""Compare completed US1 1080p and 720p summary JSON files."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from hackathon_reply.contracts.domain import RunSummary
from hackathon_reply.pipeline import compare_summaries


def _summary(path: Path) -> RunSummary:
    data = json.loads(path.read_text(encoding="utf-8"))
    return RunSummary(
        video_id=str(data["video_id"]),
        resolution=str(data["resolution"]),
        status=str(data["status"]),
        frames_processed=int(data["frames_processed"]),
        lot_count=int(data["lot_count"]),
        lot_volume_l=float(data["lot_volume_l"]),
        unique_tracks=int(data["unique_tracks"]),
        counted_track_ids=tuple(data.get("counted_track_ids", ())),
        observed_rate_fps=float(data["observed_rate_fps"]),
        warnings=tuple(data.get("warnings", ())),
        errors=tuple(data.get("errors", ())),
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--high", type=Path, required=True, help="1080p summary JSON")
    parser.add_argument("--low", type=Path, required=True, help="720p summary JSON")
    parser.add_argument("--pair-id")
    args = parser.parse_args(argv)
    high = _summary(args.high)
    low = _summary(args.low)
    pair_id = args.pair_id or high.video_id
    print(json.dumps(compare_summaries(pair_id, high, low).to_dict(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
