"""Run the US1 replay-first pipeline from a cached detection JSONL file."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from hackathon_reply.catalog.loader import load_catalog
from hackathon_reply.contracts.domain import CountGate, RunSummary
from hackathon_reply.geometry.calibration import PhysicalCalibration
from hackathon_reply.io.replay import read_detection_jsonl
from hackathon_reply.pipeline import run_replay


def _calibration(path: Path | None) -> PhysicalCalibration:
    if path is None:
        return PhysicalCalibration.untrusted()
    data = json.loads(path.read_text(encoding="utf-8"))
    if not data.get("trusted", False):
        return PhysicalCalibration.untrusted()
    return PhysicalCalibration.trusted_from_scale(
        float(data["mm_per_pixel_x"]),
        float(data["mm_per_pixel_y"]),
    )


def _gate(args: argparse.Namespace) -> CountGate:
    return CountGate(
        (args.gate_x, 0.0),
        (args.gate_x, 1.0),
        args.gate_direction,
    )


def build_parser(description: str = __doc__) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("--detections", type=Path, required=True, help="cached detection JSONL")
    parser.add_argument("--events", type=Path, required=True, help="new JSONL event output")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--calibration", type=Path)
    parser.add_argument("--catalog", type=Path)
    parser.add_argument("--summary", type=Path, help="optional JSON summary output")
    parser.add_argument("--gate-x", type=float, default=0.5)
    parser.add_argument("--gate-direction", choices=("entry_to_exit", "exit_to_entry"), default="entry_to_exit")
    return parser


def run(args: argparse.Namespace) -> RunSummary:
    catalog_entries = load_catalog(args.catalog)[0] if args.catalog else ()
    summary = run_replay(
        read_detection_jsonl(args.detections),
        output_path=args.events,
        run_id=args.run_id,
        calibration=_calibration(args.calibration),
        catalog_entries=catalog_entries,
        count_gate=_gate(args),
    )
    if args.summary:
        args.summary.parent.mkdir(parents=True, exist_ok=True)
        args.summary.write_text(json.dumps(summary.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary.to_dict(), indent=2, sort_keys=True))
    return summary


def main(argv: Sequence[str] | None = None) -> int:
    summary = run(build_parser().parse_args(argv))
    return 0 if summary.status == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
