#!/usr/bin/env python3
"""Validate a canonical Story 3 JSONL stream and its run summary."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from hackathon_reply.contracts.serialization import SerializationError, validate_run


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path, help="canonical UTF-8 JSONL event stream")
    parser.add_argument("--summary", required=True, type=Path, help="versioned run-summary JSON")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = validate_run(args.input, args.summary)
    except (OSError, SerializationError, ValueError) as exc:
        print(f"validation failed: {exc}", file=sys.stderr)
        return 1
    print(
        f"validated {result.event_count} events; "
        f"types={','.join(sorted(result.event_types))}; "
        f"counted={len(result.counted_track_ids)}; "
        f"run_status={result.summary['run_status']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
