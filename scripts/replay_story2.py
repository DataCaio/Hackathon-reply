#!/usr/bin/env python3
"""Run the deterministic User Story 2 backup replay and write its evidence."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from hackathon_reply.counting.counter import CounterConfig
from hackathon_reply.counting.gate import CountGate
from hackathon_reply.replay import ReplayRunner
from hackathon_reply.story2_fixture import acceptance_fixture
from hackathon_reply.vision.tracker import IoUTracker, TrackerConfig


def build_runner() -> ReplayRunner:
    return ReplayRunner(
        tracker=IoUTracker(
            TrackerConfig(
                min_confirmed_hits=3,
                max_age_frames=4,
                max_match_distance_px=100,
                size_similarity_threshold=0.45,
            )
        ),
        gate=CountGate.vertical(normalized_x=0.5, flow_direction="positive"),
        counter_config=CounterConfig(),
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--events", type=Path, required=True)
    parser.add_argument("--summary", type=Path, required=True)
    args = parser.parse_args()

    result = build_runner().run(acceptance_fixture())
    if len(result.events) < 20:
        raise RuntimeError("the canonical Story 2 fixture must emit at least 20 events")
    result.write_events(str(args.events))
    args.summary.parent.mkdir(parents=True, exist_ok=True)
    args.summary.write_text(json.dumps(result.summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result.summary, sort_keys=True))


if __name__ == "__main__":
    main()
