from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path
from typing import Any

CONFIG_VERSION = 2
CONFIG_NAME = "config.json"


def config_dir() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME", "").strip()
    if base:
        root = Path(base)
    else:
        root = Path.home() / ".config"
    d = root / "subgenre"
    return d


def config_path() -> Path:
    return config_dir() / CONFIG_NAME


def _normalize(s: str | None) -> str:
    if not s:
        return ""
    t = str(s).strip().lower()
    t = re.sub(r"\s+", " ", t)
    return t


def artist_album_key(artist: str | None, album: str | None) -> str:
    return f"{_normalize(artist)}::{_normalize(album)}"


def default_config() -> dict[str, Any]:
    return {
        "version": CONFIG_VERSION,
        "watch_dir": None,
        "genre_by_artist": {},
        "genre_by_artist_album": {},
        "calibration_history": [],
    }


def load_config() -> dict[str, Any]:
    p = config_path()
    if not p.is_file():
        return default_config()
    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            return default_config()
    except (OSError, json.JSONDecodeError):
        return default_config()
    out = default_config()
    out.update(raw)
    out.setdefault("genre_by_artist", {})
    out.setdefault("genre_by_artist_album", {})
    out.setdefault("calibration_history", [])
    if not isinstance(out["genre_by_artist"], dict):
        out["genre_by_artist"] = {}
    if not isinstance(out["genre_by_artist_album"], dict):
        out["genre_by_artist_album"] = {}
    if not isinstance(out["calibration_history"], list):
        out["calibration_history"] = []
    return out


def save_config(cfg: dict[str, Any]) -> None:
    d = config_dir()
    d.mkdir(parents=True, exist_ok=True)
    cfg = dict(cfg)
    cfg["version"] = CONFIG_VERSION
    p = config_path()
    p.write_text(json.dumps(cfg, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def get_watch_dir() -> Path | None:
    cfg = load_config()
    w = cfg.get("watch_dir")
    if not w:
        return None
    path = Path(str(w)).expanduser().resolve()
    return path if path.is_dir() else None


def resolve_genre(artist: str | None, album: str | None, tag_genre: str | None) -> str:
    """
    Prefer explicit calibration (artist+album, then artist), then embedded tag genre.
    """
    cfg = load_config()
    g_aa = cfg.get("genre_by_artist_album") or {}
    g_a = cfg.get("genre_by_artist") or {}

    aa = artist_album_key(artist, album)
    if aa != "::" and aa in g_aa and isinstance(g_aa[aa], str) and g_aa[aa].strip():
        return g_aa[aa].strip()

    an = _normalize(artist)
    if an and an in g_a and isinstance(g_a[an], str) and g_a[an].strip():
        return g_a[an].strip()

    if tag_genre and str(tag_genre).strip():
        return str(tag_genre).strip()

    return "Unknown Genre"


def apply_learned_genre_to_track(track: dict[str, Any]) -> None:
    """Set track['genre'] from calibration + tags (mutates in place)."""
    g = resolve_genre(
        track.get("artist") if isinstance(track.get("artist"), str) else None,
        track.get("album") if isinstance(track.get("album"), str) else None,
        track.get("genre") if isinstance(track.get("genre"), str) else None,
    )
    track["genre"] = g


def record_genre_calibration(
    *,
    artist: str | None,
    album: str | None,
    proposed: str,
    final: str,
    path: str | None = None,
) -> None:
    """Persist user genre choice for future runs."""
    cfg = load_config()
    g_aa = dict(cfg.get("genre_by_artist_album") or {})
    g_a = dict(cfg.get("genre_by_artist") or {})
    hist = list(cfg.get("calibration_history") or [])

    fin = (final or proposed or "").strip() or "Unknown Genre"
    prop = (proposed or "").strip() or "Unknown Genre"

    an = _normalize(artist)
    if an:
        g_a[an] = fin
    aa = artist_album_key(artist, album)
    if aa != "::":
        g_aa[aa] = fin

    hist.append(
        {
            "path": path,
            "artist": artist,
            "album": album,
            "proposed": prop,
            "final": fin,
            "ts": int(time.time()),
        }
    )
    hist = hist[-200:]

    cfg["genre_by_artist"] = g_a
    cfg["genre_by_artist_album"] = g_aa
    cfg["calibration_history"] = hist
    save_config(cfg)
