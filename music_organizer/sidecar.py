from __future__ import annotations

import json
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1
SIDECAR_SUFFIX = ".music-organizer.json"


def sidecar_path(audio_path: Path) -> Path:
    """Sidecar lives next to the audio file: `track.flac` -> `track.music-organizer.json`."""
    return audio_path.with_name(audio_path.stem + SIDECAR_SUFFIX)


def load_sidecar(audio_path: Path) -> dict[str, Any]:
    p = sidecar_path(audio_path)
    if not p.is_file():
        return {}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def save_sidecar(audio_path: Path, data: dict[str, Any]) -> None:
    p = sidecar_path(audio_path)
    out = {"schema_version": SCHEMA_VERSION, **data}
    p.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


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
