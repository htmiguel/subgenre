from __future__ import annotations

import json
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1
SIDECAR_SUFFIX = ".subgenre.json"
LEGACY_SIDECAR_SUFFIX = ".music-organizer.json"


def sidecar_path(audio_path: Path) -> Path:
    """Sidecar next to audio: `track.flac` -> `track.subgenre.json`."""
    return audio_path.with_name(audio_path.stem + SIDECAR_SUFFIX)


def _legacy_sidecar_path(audio_path: Path) -> Path:
    return audio_path.with_name(audio_path.stem + LEGACY_SIDECAR_SUFFIX)


def load_sidecar(audio_path: Path) -> dict[str, Any]:
    for p in (sidecar_path(audio_path), _legacy_sidecar_path(audio_path)):
        if not p.is_file():
            continue
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
        except (OSError, json.JSONDecodeError):
            continue
    return {}


def save_sidecar(audio_path: Path, data: dict[str, Any]) -> None:
    p = sidecar_path(audio_path)
    out = {"schema_version": SCHEMA_VERSION, **data}
    p.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    leg = _legacy_sidecar_path(audio_path)
    if leg.is_file() and leg.resolve() != p.resolve():
        try:
            leg.unlink()
        except OSError:
            pass


def deep_merge(base: dict[str, Any], updates: dict[str, Any]) -> dict[str, Any]:
    """Shallow-merge top-level keys; nested `track` / `audio` / `features` dicts merge one level."""
    result = dict(base)
    for k, v in updates.items():
        if k in ("track", "audio", "features", "cover", "sources") and isinstance(v, dict) and isinstance(result.get(k), dict):
            merged = dict(result[k])
            merged.update(v)
            result[k] = merged
        elif v is not None:
            result[k] = v
    return result
