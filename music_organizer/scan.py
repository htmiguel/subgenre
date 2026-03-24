from __future__ import annotations

from pathlib import Path
from typing import Any

from music_organizer.audio_info import analyze_file
from music_organizer.features_local import analyze_local
from music_organizer.sidecar import deep_merge, load_sidecar, save_sidecar
from music_organizer.spotify_audio import fetch_spotify_features
from music_organizer.tags import has_embedded_cover, read_tags_full


def _tags_to_track(tags: dict[str, Any]) -> dict[str, Any]:
    t: dict[str, Any] = {}
    for k in (
        "artist",
        "album",
        "title",
        "track",
        "disc",
        "genre",
        "bpm",
        "key",
        "date",
        "label",
    ):
        if tags.get(k) is not None:
            t[k] = tags[k]
    if t.get("date") and not t.get("year"):
        y = str(t["date"])[:4]
        if y.isdigit():
            t["year"] = int(y)
    return t


def _merge_features(
    existing: dict[str, Any] | None,
    spotify: dict[str, Any] | None,
    local: dict[str, Any] | None,
) -> dict[str, Any]:
    out: dict[str, Any] = dict(existing or {})
    if spotify:
        out.update({k: v for k, v in spotify.items() if v is not None})
    if local:
        if out.get("tempo") is None and local.get("tempo") is not None:
            out["tempo"] = local["tempo"]
        if out.get("key") is None and local.get("key"):
            out["key"] = local["key"]
        if out.get("energy") is None and local.get("energy_proxy") is not None:
            out["energy"] = local["energy_proxy"]
        if out.get("source") == "spotify" and local.get("source"):
            out["local_refine"] = local["source"]
    if not out.get("source"):
        out["source"] = (local or {}).get("source") or (spotify or {}).get("source") or "none"
    return out


def _strip_internal(bundle: dict[str, Any]) -> dict[str, Any]:
    clean = {k: v for k, v in bundle.items() if not str(k).startswith("_")}
    if "cover" in clean and isinstance(clean["cover"], dict):
        c = dict(clean["cover"])
        c.pop("bytes_ready", None)
        clean["cover"] = c
    return clean


def collect_metadata(path: Path, *, features: bool = True) -> dict[str, Any]:
    """
    Merge tags, audio analysis, optional Spotify + librosa features into sidecar.
    Does not call MusicBrainz (use `enrich` for that).
    """
    path = path.resolve()
    tags = read_tags_full(path)
    audio = analyze_file(path)
    base = load_sidecar(path)

    track = dict(base.get("track") or {})
    track.update(_tags_to_track(tags))

    sources = list(base.get("sources") or [])
    if "tags" not in sources:
        sources.append("tags")

    bundle: dict[str, Any] = {
        "track": track,
        "audio": audio,
        "sources": sources,
    }

    cov = dict(base.get("cover") or {})
    cov["embedded"] = has_embedded_cover(path)
    bundle["cover"] = cov

    if features:
        artist = track.get("artist")
        title = track.get("title")
        spo = None
        if artist and title:
            spo = fetch_spotify_features(str(artist), str(title))
            if spo and "spotify" not in sources:
                sources.append("spotify")
        loc = analyze_local(path)
        if loc and loc.get("source") == "librosa" and "librosa" not in sources:
            sources.append("librosa")
        bundle["features"] = _merge_features(base.get("features"), spo, loc)
        bundle["sources"] = sources

    merged = deep_merge(base, bundle)
    merged = _strip_internal(merged)
    save_sidecar(path, merged)
    return merged


def scan_tree(root: Path, *, features: bool = True) -> list[Path]:
    from music_organizer.tags import iter_audio_files

    touched: list[Path] = []
    for p in iter_audio_files(root):
        collect_metadata(p, features=features)
        touched.append(p)
    return touched
