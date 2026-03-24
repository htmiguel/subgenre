from __future__ import annotations

import time
from typing import Any

import musicbrainzngs
import requests

_USER_AGENT_NAME = "subgenre"
_USER_AGENT_VERSION = "0.4.0"
_USER_AGENT_URL = "https://github.com/local/subgenre"

_MB_DELAY = 1.05


def configure_client() -> None:
    musicbrainzngs.set_useragent(_USER_AGENT_NAME, _USER_AGENT_VERSION, _USER_AGENT_URL)


def _sleep() -> None:
    time.sleep(_MB_DELAY)


def search_recording(artist: str, title: str, *, limit: int = 5) -> list[dict[str, Any]]:
    configure_client()
    _sleep()
    result = musicbrainzngs.search_recordings(artist=artist, recording=title, limit=limit)
    recs = result.get("recording-list") or []
    out: list[dict[str, Any]] = []
    for r in recs:
        rid = r.get("id")
        disambig = r.get("disambiguation") or ""
        score = r.get("ext-score")
        title_out = r.get("title") or ""
        artist_credit = r.get("artist-credit") or []
        names: list[str] = []
        if isinstance(artist_credit, list):
            for ac in artist_credit:
                if isinstance(ac, dict) and ac.get("name"):
                    names.append(str(ac["name"]))
        elif isinstance(artist_credit, dict) and artist_credit.get("name"):
            names.append(str(artist_credit["name"]))
        out.append(
            {
                "id": rid,
                "title": title_out,
                "artists": names,
                "score": score,
                "disambiguation": disambig,
            }
        )
    return out


def _artist_names_from_credit(credit: Any) -> list[str]:
    names: list[str] = []
    if isinstance(credit, list):
        for ac in credit:
            if isinstance(ac, dict) and ac.get("name"):
                names.append(str(ac["name"]))
    elif isinstance(credit, dict) and credit.get("name"):
        names.append(str(credit["name"]))
    return names


def get_recording_with_releases(recording_id: str) -> dict[str, Any]:
    configure_client()
    _sleep()
    rec = musicbrainzngs.get_recording_by_id(
        recording_id,
        includes=["artists", "releases", "tags"],
    )
    releases = rec.get("release-list") or []
    tags = rec.get("tag-list") or []
    genre_names = [str(t.get("name")) for t in tags if isinstance(t, dict) and t.get("name")]
    artists = _artist_names_from_credit(rec.get("artist-credit"))
    return {
        "id": rec.get("id"),
        "title": rec.get("title"),
        "artists": artists,
        "genres": genre_names,
        "releases": releases,
    }


def get_release_detail(release_id: str) -> dict[str, Any]:
    configure_client()
    _sleep()
    rel = musicbrainzngs.get_release_by_id(
        release_id,
        includes=["labels", "release-groups", "recordings", "artist-credits"],
    )
    date = rel.get("date") or ""
    year: int | None = None
    if date and len(date) >= 4 and date[:4].isdigit():
        year = int(date[:4])

    label_name: str | None = None
    catalog: str | None = None
    label_id: str | None = None
    infos = rel.get("label-info-list") or []
    if isinstance(infos, list) and infos:
        first = infos[0]
        if isinstance(first, dict):
            catalog = first.get("catalog-number")
            lab = first.get("label") or {}
            if isinstance(lab, dict):
                label_name = lab.get("name")
                label_id = lab.get("id")

    rg = rel.get("release-group") or {}
    rg_title = rg.get("title") if isinstance(rg, dict) else None

    area_name: str | None = None
    country = rel.get("country")
    if country:
        area_name = str(country)

    return {
        "id": rel.get("id"),
        "title": rel.get("title"),
        "date": date,
        "year": year,
        "label": label_name,
        "label_id": label_id,
        "catalog_number": catalog,
        "label_area": area_name,
        "release_group_title": rg_title,
        "barcode": rel.get("barcode"),
    }


def fetch_label_area(label_id: str) -> str | None:
    configure_client()
    _sleep()
    try:
        lab = musicbrainzngs.get_label_by_id(label_id, includes=["area-rels"])
    except Exception:
        return None
    area = lab.get("area") if isinstance(lab, dict) else None
    if isinstance(area, dict) and area.get("name"):
        return str(area["name"])
    return None


def pick_preferred_release(releases: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not releases:
        return None
    # Prefer official albums / singles with earliest date
    def sort_key(r: dict[str, Any]) -> tuple[int, str]:
        status = (r.get("status") or "").lower()
        prim = 0 if status == "official" else 1
        date = r.get("date") or "9999"
        return (prim, date)

    official = [r for r in releases if isinstance(r, dict) and r.get("id")]
    if not official:
        return None
    return sorted(official, key=sort_key)[0]


def fetch_cover_art_bytes(release_id: str, timeout: float = 45.0) -> tuple[bytes, str] | None:
    url = f"https://coverartarchive.org/release/{release_id}"
    time.sleep(0.3)
    try:
        r = requests.get(url, timeout=timeout)
        if r.status_code != 200:
            return None
        data = r.json()
    except (OSError, ValueError):
        return None
    images = data.get("images") or []
    front = None
    for img in images:
        if isinstance(img, dict) and img.get("front"):
            front = img
            break
    if front is None and images:
        front = images[0]
    if not isinstance(front, dict):
        return None
    thumb = front.get("image") or front.get("thumbnails", {}).get("large")
    if not thumb:
        return None
    try:
        ir = requests.get(str(thumb), timeout=timeout)
        if ir.status_code != 200:
            return None
        mime = ir.headers.get("Content-Type", "image/jpeg")
        return ir.content, mime.split(";")[0].strip()
    except OSError:
        return None


def lookup_track_bundle(artist: str, title: str) -> dict[str, Any] | None:
    """
    Search recording, pick first hit, load release + label + cover.
    Returns a dict suitable for merging into sidecar `track` / `cover` / sources.
    """
    if artist.strip():
        hits = search_recording(artist, title, limit=3)
    else:
        configure_client()
        _sleep()
        result = musicbrainzngs.search_recordings(recording=title, limit=3)
        recs = result.get("recording-list") or []
        hits = []
        for r in recs:
            if not isinstance(r, dict):
                continue
            ac = r.get("artist-credit") or []
            names: list[str] = []
            if isinstance(ac, list):
                for x in ac:
                    if isinstance(x, dict) and x.get("name"):
                        names.append(str(x["name"]))
            hits.append(
                {
                    "id": r.get("id"),
                    "title": r.get("title") or "",
                    "artists": names,
                    "score": r.get("ext-score"),
                    "disambiguation": r.get("disambiguation") or "",
                }
            )
    if not hits or not hits[0].get("id"):
        return None
    rid = str(hits[0]["id"])
    rec = get_recording_with_releases(rid)
    rel_pick = pick_preferred_release(rec.get("releases") or [])
    if not rel_pick or not rel_pick.get("id"):
        return None
    release_id = str(rel_pick["id"])
    detail = get_release_detail(release_id)
    label_area = detail.get("label_area")
    lid = detail.get("label_id")
    if lid and not label_area:
        label_area = fetch_label_area(str(lid)) or label_area

    cover = fetch_cover_art_bytes(release_id)
    artists_join = ", ".join(rec.get("artists") or []) or artist
    genre = None
    if rec.get("genres"):
        genre = rec["genres"][0]

    out: dict[str, Any] = {
        "track": {
            "artist": artists_join,
            "title": rec.get("title") or title,
            "album": detail.get("title") or rel_pick.get("title"),
            "genre": genre,
            "label": detail.get("label"),
            "label_area": label_area,
            "label_id": lid,
            "catalog_number": detail.get("catalog_number"),
            "year": detail.get("year"),
            "date": detail.get("date"),
            "musicbrainz_recording_id": rid,
            "musicbrainz_release_id": release_id,
        },
        "sources": ["musicbrainz"],
    }
    if cover:
        out["cover"] = {"embedded": False, "bytes_ready": True, "mime": cover[1]}
        out["_cover_bytes"] = cover[0]
        out["_cover_mime"] = cover[1]
    return out
