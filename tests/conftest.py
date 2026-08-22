"""Repository-wide fixtures shared by contract and integration tests."""

from __future__ import annotations

from pathlib import Path

import pytest


FEATURE_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_ROOT = FEATURE_ROOT / "tests" / "fixtures" / "user_story3"


@pytest.fixture
def fixture_root() -> Path:
    return FIXTURE_ROOT
