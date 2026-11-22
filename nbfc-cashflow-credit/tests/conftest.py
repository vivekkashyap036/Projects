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


@pytest.fixture(scope="session")
def full_tables():
    """The full seeded synthetic dataset (same as the shipped build)."""
    return synth.generate()


@pytest.fixture(scope="session")
def trained(full_tables):
    """(scorer, train_df, test_df) fitted exactly as the shipped model is."""
    from vendorscore import model

    df = model.build_dataset(full_tables)
    tr, te = model.split(df)
    return model.fit_logreg(tr), tr, te
