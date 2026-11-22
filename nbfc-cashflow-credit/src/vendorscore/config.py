"""Config loading. One YAML file holds every tunable threshold."""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = Path(os.environ.get("VENDORSCORE_CONFIG", PROJECT_ROOT / "config" / "model_config.yaml"))
DATA_DIR = Path(os.environ.get("VENDORSCORE_DATA_DIR", PROJECT_ROOT / "data"))
ARTIFACT_DIR = Path(os.environ.get("VENDORSCORE_ARTIFACT_DIR", PROJECT_ROOT / "artifacts"))
REPORT_DIR = Path(os.environ.get("VENDORSCORE_REPORT_DIR", PROJECT_ROOT / "reports"))


@lru_cache(maxsize=1)
def load_config(path: str | None = None) -> dict[str, Any]:
    p = Path(path) if path else CONFIG_PATH
    with open(p, encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def ensure_dirs() -> None:
    for d in (DATA_DIR, ARTIFACT_DIR, REPORT_DIR):
        d.mkdir(parents=True, exist_ok=True)
