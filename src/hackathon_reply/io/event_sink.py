"""Exactly-once JSONL event output for one clean run."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TextIO

from hackathon_reply.contracts.events import EventEnvelope


class EventDeliveryError(RuntimeError):
    """Raised when a run cannot deliver a valid exactly-once event stream."""


class ExactlyOnceEventSink:
    """Write one immutable, ordered JSONL stream for a single run."""

    def __init__(self, path: str | Path, *, run_id: str) -> None:
        if not run_id:
            raise EventDeliveryError("run_id is required")
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.completion_path = Path(str(self.path) + ".complete")
        if self.completion_path.exists():
            raise EventDeliveryError("completion marker exists; start with a clean output path")
        try:
            self._handle: TextIO = self.path.open("x", encoding="utf-8", newline="\n")
        except FileExistsError as exc:
            raise EventDeliveryError("output exists; start a clean run with a new output path") from exc
        self.run_id = run_id
        self._next_sequence = 0
        self._last_timestamp_ms = -1
        self._event_ids: set[str] = set()
        self._closed = False
        self._completed = False

    def write(self, event: EventEnvelope) -> None:
        if self._closed:
            raise EventDeliveryError("event sink is closed")
        if event.run_id != self.run_id:
            raise EventDeliveryError("event run_id does not match sink run_id")
        if event.event_id in self._event_ids:
            raise EventDeliveryError("duplicate event_id")
        if event.sequence != self._next_sequence:
            raise EventDeliveryError("event sequence is not contiguous")
        if event.timestamp_ms < self._last_timestamp_ms:
            raise EventDeliveryError("event timestamp is not monotonic")
        try:
            self._handle.write(event.to_json() + "\n")
            self._handle.flush()
        except (OSError, TypeError, ValueError) as exc:
            self._closed = True
            self._handle.close()
            raise EventDeliveryError("event delivery failed; run must be replayed cleanly") from exc
        self._event_ids.add(event.event_id)
        self._next_sequence += 1
        self._last_timestamp_ms = event.timestamp_ms

    @property
    def next_sequence(self) -> int:
        """Return the next contiguous sequence number for a new event."""

        return self._next_sequence

    @property
    def is_complete(self) -> bool:
        return self._completed

    def complete(self) -> None:
        """Commit a clean stream with a sidecar marker after all events flush."""

        if self._closed:
            raise EventDeliveryError("event sink is closed")
        try:
            self._handle.flush()
            with self.completion_path.open("x", encoding="utf-8", newline="\n") as marker:
                marker.write(
                    json.dumps(
                        {"run_id": self.run_id, "event_count": self._next_sequence},
                        sort_keys=True,
                    )
                    + "\n"
                )
        except (OSError, TypeError, ValueError) as exc:
            raise EventDeliveryError("event stream could not be committed cleanly") from exc
        self._completed = True

    def close(self) -> None:
        if not self._closed:
            self._handle.flush()
            self._handle.close()
            self._closed = True

    def __enter__(self) -> "ExactlyOnceEventSink":
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        try:
            if exc_type is None and not self._closed:
                self.complete()
        finally:
            self.close()
