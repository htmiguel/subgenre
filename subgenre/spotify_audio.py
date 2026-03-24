from __future__ import annotations

import base64
import os
import time
from typing import Any

import requests

SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"
SPOTIFY_API = "https://api.spotify.com/v1"


def _credentials() -> tuple[str, str] | None:
    cid = os.environ.get("SPOTIFY_CLIENT_ID", "").strip()
    secret = os.environ.get("SPOTIFY_CLIENT_SECRET", "").strip()
    if not cid or not secret:
        return None
    return cid, secret


def get_access_token() -> str | None:
    creds = _credentials()
    if not creds:
        return None
    cid, secret = creds
    auth = base64.b64encode(f"{cid}:{secret}".encode()).decode()
    try:
        r = requests.post(
            SPOTIFY_TOKEN_URL,
            headers={"Authorization": f"Basic {auth}"},
            data={"grant_type": "client_credentials"},
            timeout=30,
        )
        if r.status_code != 200:
            return None
        return str(r.json().get("access_token"))
    except OSError:
        return None


def search_track_id(artist: str, title: str, token: str) -> str | None:
    q = f'artist:"{artist}" track:"{title}"'
    try:
        r = requests.get(
            f"{SPOTIFY_API}/search",
            headers={"Authorization": f"Bearer {token}"},
            params={"q": q, "type": "track", "limit": 1},
            timeout=30,
        )
        if r.status_code != 200:
            return None
        items = (r.json().get("tracks") or {}).get("items") or []
        if not items:
            return None
        return str(items[0].get("id"))
    except OSError:
        return None


def audio_features(track_id: str, token: str) -> dict[str, Any] | None:
    time.sleep(0.15)
    try:
        r = requests.get(
            f"{SPOTIFY_API}/audio-features/{track_id}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=30,
        )
        if r.status_code != 200:
            return None
        return dict(r.json())
    except OSError:
        return None


def fetch_spotify_features(artist: str, title: str) -> dict[str, Any] | None:
    """
    EchoNest-like features from Spotify Web API (catalog match required).
    Returns a normalized `features` dict for the sidecar.
    """
    token = get_access_token()
    if not token:
        return None
    tid = search_track_id(artist, title, token)
    if not tid:
        return None
    raw = audio_features(tid, token)
    if not raw or raw.get("id") is None:
        return None
    key_names = ("C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B")
    k = raw.get("key")
    mode = raw.get("mode")
    key_str = None
    if isinstance(k, int) and 0 <= k < 12:
        ks = key_names[k]
        if mode == 0:
            key_str = f"{ks} minor"
        elif mode == 1:
            key_str = f"{ks} major"
        else:
            key_str = ks
    return {
        "spotify_track_id": raw.get("id"),
        "danceability": raw.get("danceability"),
        "energy": raw.get("energy"),
        "loudness": raw.get("loudness"),
        "speechiness": raw.get("speechiness"),
        "acousticness": raw.get("acousticness"),
        "instrumentalness": raw.get("instrumentalness"),
        "liveness": raw.get("liveness"),
        "valence": raw.get("valence"),
        "tempo": raw.get("tempo"),
        "key": key_str,
        "key_pitch_class": k,
        "mode": mode,
        "time_signature": raw.get("time_signature"),
        "source": "spotify",
    }
