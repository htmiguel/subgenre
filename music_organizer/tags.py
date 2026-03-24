from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from mutagen import File as MutagenFile

AUDIO_EXTENSIONS = {".mp3", ".flac", ".m4a", ".mp4", ".ogg", ".opus", ".wav", ".aac", ".wma"}


def _first(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, list):
        if not value:
            return None
        value = value[0]
    s = str(value).strip()
    return s or None


def _normalize_track(track: str | None) -> tuple[int | None, int | None]:
    """Return (track, total) from '3', '3/12', etc."""
    if not track:
        return None, None
    m = re.match(r"^(\d+)(?:/(\d+))?$", track.strip())
    if not m:
        return None, None
    return int(m.group(1)), int(m.group(2)) if m.group(2) else None


def read_tags(path: Path) -> dict[str, str | int | None]:
    """Read a small unified tag set from any format mutagen supports."""
    audio = MutagenFile(path, easy=True)
    if audio is None:
        return {
            "artist": None,
            "album": None,
            "title": None,
            "track": None,
            "disc": None,
        }

    artist = _first(audio.get("artist"))
    albumartist = _first(audio.get("albumartist"))
    artist = artist or albumartist

    album = _first(audio.get("album"))
    title = _first(audio.get("title"))

    track_raw = _first(audio.get("tracknumber"))
    disc_raw = _first(audio.get("discnumber"))

    tr, _total = _normalize_track(track_raw)
    disc, _dt = _normalize_track(disc_raw)

    return {
        "artist": artist,
        "album": album,
        "title": title,
        "track": tr,
        "disc": disc,
    }


def safe_path_component(name: str | None, fallback: str) -> str:
    """Strip characters unsafe on common filesystems."""
    if not name:
        name = fallback
    # Windows + Unix problem characters
    cleaned = re.sub(r'[<>:"/\\|?\x00-\x1f]', "_", name)
    cleaned = cleaned.strip()
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned or fallback


def iter_audio_files(root: Path) -> list[Path]:
    root = root.resolve()
    if not root.is_dir():
        return []
    out: list[Path] = []
    for p in sorted(root.rglob("*")):
        if p.is_file() and p.suffix.lower() in AUDIO_EXTENSIONS:
            out.append(p)
    return out


def proposed_relative_path(path: Path, tags: dict[str, str | int | None]) -> Path:
    """Target path under library root: Artist/Album/NN Title.ext"""
    artist = safe_path_component(tags.get("artist") if isinstance(tags.get("artist"), str) else None, "Unknown Artist")
    album = safe_path_component(tags.get("album") if isinstance(tags.get("album"), str) else None, "Unknown Album")

    title = tags.get("title")
    title_str = title if isinstance(title, str) and title.strip() else path.stem
    title_str = safe_path_component(title_str, path.stem)

    ext = path.suffix.lower() or path.suffix
    disc = tags.get("disc")
    track = tags.get("track")

    parts_prefix = ""
    if disc is not None and isinstance(disc, int) and disc > 0:
        parts_prefix = f"{disc:d}-"
    if track is not None and isinstance(track, int) and track > 0:
        name = f"{parts_prefix}{track:02d} {title_str}{ext}"
    else:
        name = f"{parts_prefix}{title_str}{ext}" if parts_prefix else f"{title_str}{ext}"

    return Path(artist) / Path(album) / name
