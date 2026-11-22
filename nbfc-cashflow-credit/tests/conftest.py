from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from vendorscore.data import synth  # noqa: E402


@pytest.fixture(scope="session")
def small_tables():
    """A small synthetic sample for fast tests (seeded)."""
    return synth.generate(n_vendors=1500, seed=7)
