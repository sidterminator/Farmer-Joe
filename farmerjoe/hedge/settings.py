"""Hedge settings: config.yaml `hedge:` section + per-crop defaults + overrides."""
from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import yaml

from farmerjoe.config import DEFAULT_CONFIG_PATH


def load_hedge_settings(crop: str, overrides: dict[str, Any] | None = None,
                        path: str | Path | None = None) -> dict[str, Any]:
    """Flat settings dict for `crop` (crop defaults merged under the global hedge keys).
    Non-None overrides win."""
    raw = yaml.safe_load(Path(path or DEFAULT_CONFIG_PATH).read_text())["hedge"]
    crops = raw.pop("crops")
    if crop not in crops:
        raise ValueError(f"no hedge defaults for crop {crop!r}; have {sorted(crops)}")
    s = copy.deepcopy(raw)
    s.update(crops[crop])
    s["crop"] = crop
    s.update({k: v for k, v in (overrides or {}).items() if v is not None})
    return s
