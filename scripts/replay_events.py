#!/usr/bin/env python3
"""Replay a canonical Story 3 event stream without a detector or GPU."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from hackathon_reply.replay import ReplayError, replay_to_files


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path, help="canonical UTF-8 JSONL event stream")
    parser.add_argument("--summary", required=True, type=Path, help="versioned run-summary JSON")
    parser.add_argument("--output", required=True, type=Path, help="canonical replay JSONL output")
    parser.add_argument("--result", required=True, type=Path, help="semantic replay result JSON output")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = replay_to_files(args.input, args.summary, args.output, args.result)
    except (OSError, ReplayError, ValueError) as exc:
        print(f"replay failed: {exc}", file=sys.stderr)
        return 1
    print(
        f"replayed {result.event_count} events; "
        f"summary={args.result}; "
        f"run_status={result.semantic_summary['run_status']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
