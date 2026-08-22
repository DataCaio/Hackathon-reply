"""Shared helpers for published-contract tests."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest


FEATURE_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_ROOT = FEATURE_ROOT / "tests" / "fixtures" / "user_story3"


@pytest.fixture
def fixture_root() -> Path:
    return FIXTURE_ROOT


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    )
