"""Explicit alias for the US1 cached-detection replay runner."""

from __future__ import annotations

try:
    from run_video import main
except ImportError:  # pragma: no cover - supports ``python -m scripts.replay_detections``
    from scripts.run_video import main


if __name__ == "__main__":
    raise SystemExit(main())
