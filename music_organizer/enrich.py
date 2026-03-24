from __future__ import annotations

from pathlib import Path
from typing import Any

from music_organizer.audio_info import analyze_file
from music_organizer.features_local import analyze_local
from music_organizer.mb import lookup_track_bundle
from music_organizer.sidecar import deep_merge, load_sidecar, save_sidecar
from music_organizer.spotify_audio import fetch_spotify_features
from music_organizer.tags import embed_cover, has_embedded_cover, read_tags_full, write_tags


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


def _missing_core(track: dict[str, Any], path: Path) -> list[str]:
    missing: list[str] = []
    if not track.get("artist"):
        missing.append("artist")
    if not track.get("title"):
        missing.append("title")
    if not track.get("label"):
        missing.append("label")
    if track.get("year") is None and not track.get("date"):
        missing.append("year")
    if not track.get("label_area"):
        missing.append("label_area")
    if not track.get("bpm"):
        missing.append("bpm")
    if not track.get("key"):
        missing.append("key")
    if not has_embedded_cover(path):
        missing.append("cover")
    return missing


def _strip_internal(bundle: dict[str, Any]) -> dict[str, Any]:
    clean = {k: v for k, v in bundle.items() if not str(k).startswith("_")}
    if "cover" in clean and isinstance(clean["cover"], dict):
        c = dict(clean["cover"])
        c.pop("bytes_ready", None)
        clean["cover"] = c
    return clean


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
    if not out.get("source"):
        out["source"] = (spotify or {}).get("source") or (local or {}).get("source") or "none"
    return out


def enrich_file(path: Path, *, dry_run: bool = False) -> dict[str, Any]:
    """
    Fill missing cover, MusicBrainz fields, BPM/key/year/label/location; write tags + sidecar.
    """
    path = path.resolve()
    tags = read_tags_full(path)
    base = load_sidecar(path)
    track = dict(base.get("track") or {})
    track.update(_tags_to_track(tags))

    sources = list(base.get("sources") or [])
    if "tags" not in sources:
        sources.append("tags")

    artist_guess = str(track.get("artist") or "")
    title_guess = str(track.get("title") or path.stem)

    missing_before = _missing_core(track, path)

    mb_payload: dict[str, Any] | None = None
    if missing_before and title_guess:
        mb_payload = lookup_track_bundle(artist_guess, title_guess)
        if mb_payload:
            if "musicbrainz" not in sources:
                sources.append("musicbrainz")
            t_up = mb_payload.get("track") or {}
            for k, v in t_up.items():
                if v is not None and (track.get(k) in (None, "", [])):
                    track[k] = v

    cover_bytes = mb_payload.get("_cover_bytes") if mb_payload else None
    cover_mime = str((mb_payload.get("_cover_mime") if mb_payload else None) or "image/jpeg")

    if cover_bytes and not has_embedded_cover(path) and not dry_run:
        embed_cover(path, cover_bytes, mime=str(cover_mime))

    # Spotify / librosa for missing bpm, key, EchoNest-style features
    need_audio = (
        not track.get("bpm")
        or not track.get("key")
        or not base.get("features")
    )
    spo = None
    if need_audio and track.get("artist") and track.get("title"):
        spo = fetch_spotify_features(str(track["artist"]), str(track["title"]))
        if spo and "spotify" not in sources:
            sources.append("spotify")
    loc = analyze_local(path) if need_audio else None
    if loc and "librosa" not in sources:
        sources.append("librosa")

    feats = _merge_features(base.get("features"), spo, loc)
    if feats.get("tempo") is not None and not track.get("bpm"):
        track["bpm"] = int(round(float(feats["tempo"])))
    if feats.get("key") and not track.get("key"):
        track["key"] = str(feats["key"])

    audio = analyze_file(path)
    cov = dict(base.get("cover") or {})
    cov["embedded"] = has_embedded_cover(path)

    bundle = deep_merge(
        base,
        {
            "track": track,
            "audio": audio,
            "features": feats,
            "cover": cov,
            "sources": sources,
        },
    )
    out = _strip_internal(bundle)

    if not dry_run:
        write_fields = {
            "title": track.get("title"),
            "artist": track.get("artist"),
            "album": track.get("album"),
            "genre": track.get("genre"),
            "date": str(track.get("year")) if track.get("year") else track.get("date"),
            "bpm": track.get("bpm"),
            "key": track.get("key"),
            "label": track.get("label"),
        }
        write_fields = {k: v for k, v in write_fields.items() if v is not None}
        if write_fields:
            write_tags(path, write_fields)
        save_sidecar(path, out)

    return out


def enrich_tree(root: Path, *, dry_run: bool = False) -> list[Path]:
    from music_organizer.tags import iter_audio_files

    done: list[Path] = []
    for p in iter_audio_files(root):
        enrich_file(p, dry_run=dry_run)
        done.append(p)
    return done
