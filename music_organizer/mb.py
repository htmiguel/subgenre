from __future__ import annotations

import time
from typing import Any

import musicbrainzngs

_USER_AGENT_NAME = "music-organizer"
_USER_AGENT_VERSION = "0.1.0"
_USER_AGENT_URL = "https://github.com/local/music-organizer"


def configure_client() -> None:
    musicbrainzngs.set_useragent(_USER_AGENT_NAME, _USER_AGENT_VERSION, _USER_AGENT_URL)


def search_recording(artist: str, title: str, *, limit: int = 5) -> list[dict[str, Any]]:
    """Search MusicBrainz recordings; respects ~1 req/s politeness."""
    configure_client()
    time.sleep(1.0)
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
                    names.append(ac["name"])
        elif isinstance(artist_credit, dict) and artist_credit.get("name"):
            names.append(artist_credit["name"])
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
