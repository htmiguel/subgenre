from __future__ import annotations

import base64
import re
from pathlib import Path
from typing import Any

from mutagen import File as MutagenFile
from mutagen.flac import FLAC, Picture
from mutagen.id3 import APIC, ID3, TALB, TBPM, TDRC, TIT2, TKEY, TPE1, TPUB, TCON
from mutagen.mp3 import MP3
from mutagen.mp4 import MP4, MP4Cover
from mutagen.oggopus import OggOpus
from mutagen.oggvorbis import OggVorbis

AUDIO_EXTENSIONS = {".mp3", ".flac", ".m4a", ".mp4", ".ogg", ".opus", ".wav", ".aac", ".wma"}

_SKIP_DIR_NAMES = frozenset({".git", ".venv", "venv", "node_modules", "__pycache__"})


def _path_skipped(path: Path) -> bool:
    return any(part in _SKIP_DIR_NAMES for part in path.parts)


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
    if not track:
        return None, None
    m = re.match(r"^(\d+)(?:/(\d+))?$", track.strip())
    if not m:
        return None, None
    return int(m.group(1)), int(m.group(2)) if m.group(2) else None


def read_tags(path: Path) -> dict[str, str | int | None]:
    """Backwards-compatible subset (used by tests / simple callers)."""
    full = read_tags_full(path)
    return {k: full.get(k) for k in ("artist", "album", "title", "track", "disc", "genre")}


def read_tags_full(path: Path) -> dict[str, Any]:
    """Unified tag fields including genre, bpm, key, date, label (best-effort per format)."""
    try:
        audio = MutagenFile(path, easy=True)
    except Exception:
        audio = None
    if audio is None:
        return {
            "artist": None,
            "album": None,
            "title": None,
            "track": None,
            "disc": None,
            "genre": None,
            "bpm": None,
            "key": None,
            "date": None,
            "label": None,
        }

    artist = _first(audio.get("artist"))
    albumartist = _first(audio.get("albumartist"))
    artist = artist or albumartist
    album = _first(audio.get("album"))
    title = _first(audio.get("title"))
    genre = _first(audio.get("genre"))

    track_raw = _first(audio.get("tracknumber"))
    disc_raw = _first(audio.get("discnumber"))
    tr, _total = _normalize_track(track_raw)
    disc, _dt = _normalize_track(disc_raw)

    bpm = _first(audio.get("bpm"))
    key = _first(audio.get("key"))
    date = _first(audio.get("date"))
    label = _first(audio.get("label"))

    ext = path.suffix.lower()
    if ext == ".mp3":
        try:
            id3 = ID3(path)
            if id3.get("TKEY"):
                key = key or _first(id3.get("TKEY").text)
            if id3.get("TBPM"):
                bpm = bpm or _first(id3.get("TBPM").text)
            if id3.get("TPUB"):
                label = label or _first(id3.get("TPUB").text)
            if id3.get("TDRC"):
                date = date or _first(id3.get("TDRC").text)
        except Exception:
            pass
    elif ext in (".m4a", ".mp4"):
        try:
            mp4 = MP4(path)
            tags = mp4.tags or {}
            # ©grp — Grouping sometimes used for label; ©wrk etc.
            if tags.get("\xa9grp"):
                label = label or _first(tags.get("\xa9grp"))
            if tags.get("tmpo"):
                t = tags.get("tmpo")
                if isinstance(t, list) and t:
                    bpm = bpm or str(int(t[0]))
        except Exception:
            pass

    return {
        "artist": artist,
        "album": album,
        "title": title,
        "track": tr,
        "disc": disc,
        "genre": genre,
        "bpm": bpm,
        "key": key,
        "date": date,
        "label": label,
    }


def safe_path_component(name: str | None, fallback: str) -> str:
    if not name:
        name = fallback
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
        if _path_skipped(p):
            continue
        if p.is_file() and p.suffix.lower() in AUDIO_EXTENSIONS:
            if p.name.endswith((".subgenre.json", ".music-organizer.json")):
                continue
            out.append(p)
    return out


def embed_cover(path: Path, image_bytes: bytes, mime: str = "image/jpeg") -> None:
    ext = path.suffix.lower()
    if ext == ".mp3":
        audio = MP3(path, ID3=ID3)
        if audio.tags is None:
            audio.add_tags()
        audio.tags.delall("APIC")
        audio.tags.add(
            APIC(
                encoding=3,
                mime=mime,
                type=3,
                desc="Cover",
                data=image_bytes,
            )
        )
        audio.save()
    elif ext == ".flac":
        audio = FLAC(path)
        audio.clear_pictures()
        pic = Picture()
        pic.type = 3
        pic.mime = mime
        pic.desc = "Cover"
        pic.data = image_bytes
        audio.add_picture(pic)
        audio.save()
    elif ext in (".m4a", ".mp4"):
        audio = MP4(path)
        if audio.tags is None:
            audio.add_tags()
        fmt = MP4Cover.FORMAT_JPEG if "jpeg" in mime else MP4Cover.FORMAT_PNG
        audio.tags["covr"] = [MP4Cover(image_bytes, imageformat=fmt)]
        audio.save()
    elif ext in (".ogg", ".opus"):
        pic = Picture()
        pic.type = 3
        pic.mime = mime
        pic.desc = "Cover"
        pic.data = image_bytes
        b64 = base64.b64encode(pic.write()).decode("ascii")
        if ext == ".opus":
            audio = OggOpus(path)
        else:
            audio = OggVorbis(path)
        audio["METADATA_BLOCK_PICTURE"] = [b64]
        audio.save()
    else:
        raise NotImplementedError(f"Cover embedding not implemented for {ext}")


def write_tags(path: Path, fields: dict[str, Any]) -> None:
    """Write common textual tags + optional numeric bpm. Skips None values."""
    ext = path.suffix.lower()
    title = fields.get("title")
    artist = fields.get("artist")
    album = fields.get("album")
    genre = fields.get("genre")
    date = fields.get("date")  # year string YYYY
    bpm = fields.get("bpm")
    key = fields.get("key")
    label = fields.get("label")

    if ext == ".mp3":
        audio = MP3(path, ID3=ID3)
        if audio.tags is None:
            audio.add_tags()
        tags = audio.tags
        if title:
            tags["TIT2"] = TIT2(encoding=3, text=str(title))
        if artist:
            tags["TPE1"] = TPE1(encoding=3, text=str(artist))
        if album:
            tags["TALB"] = TALB(encoding=3, text=str(album))
        if genre:
            tags["TCON"] = TCON(encoding=3, text=str(genre))
        if date:
            tags["TDRC"] = TDRC(encoding=3, text=str(date)[:4])
        if bpm is not None:
            tags["TBPM"] = TBPM(encoding=3, text=str(int(float(bpm))))
        if key:
            tags["TKEY"] = TKEY(encoding=3, text=str(key)[:32])
        if label:
            tags["TPUB"] = TPUB(encoding=3, text=str(label))
        audio.save()
    elif ext == ".flac":
        audio = FLAC(path)
        if title:
            audio["TITLE"] = str(title)
        if artist:
            audio["ARTIST"] = str(artist)
        if album:
            audio["ALBUM"] = str(album)
        if genre:
            audio["GENRE"] = str(genre)
        if date:
            audio["DATE"] = str(date)[:4]
        if bpm is not None:
            audio["BPM"] = str(int(float(bpm)))
        if key:
            audio["INITIALKEY"] = str(key)
        if label:
            audio["ORGANIZATION"] = str(label)
        audio.save()
    elif ext in (".m4a", ".mp4"):
        audio = MP4(path)
        if audio.tags is None:
            audio.add_tags()
        t = audio.tags
        if title:
            t["\xa9nam"] = [str(title)]
        if artist:
            t["\xa9ART"] = [str(artist)]
        if album:
            t["\xa9alb"] = [str(album)]
        if genre:
            t["\xa9gen"] = [str(genre)]
        if date:
            t["\xa9day"] = [str(date)[:4]]
        if bpm is not None:
            t["tmpo"] = [int(float(bpm))]
        # key: custom ----:com.apple.iTunes:initialkey
        if key:
            t["----:com.apple.iTunes:initialkey"] = [str(key).encode("utf-8")]
        if label:
            t["\xa9grp"] = [str(label)]
        audio.save()
    elif ext in (".ogg", ".opus"):
        if ext == ".opus":
            audio = OggOpus(path)
        else:
            audio = OggVorbis(path)
        if title:
            audio["TITLE"] = str(title)
        if artist:
            audio["ARTIST"] = str(artist)
        if album:
            audio["ALBUM"] = str(album)
        if genre:
            audio["GENRE"] = str(genre)
        if date:
            audio["DATE"] = str(date)[:4]
        if bpm is not None:
            audio["BPM"] = str(int(float(bpm)))
        if key:
            audio["INITIALKEY"] = str(key)
        if label:
            audio["ORGANIZATION"] = str(label)
        audio.save()
    else:
        # Fallback: easy tags where mutagen supports them
        audio = MutagenFile(path, easy=True)
        if audio is None:
            return
        if title:
            audio["title"] = str(title)
        if artist:
            audio["artist"] = str(artist)
        if album:
            audio["album"] = str(album)
        if genre:
            audio["genre"] = str(genre)
        if date:
            audio["date"] = str(date)[:4]
        audio.save()


def has_embedded_cover(path: Path) -> bool:
    ext = path.suffix.lower()
    try:
        if ext == ".mp3":
            id3 = ID3(path)
            return any(str(k).startswith("APIC") for k in id3.keys())
        if ext == ".flac":
            fl = FLAC(path)
            return bool(fl.pictures)
        if ext in (".m4a", ".mp4"):
            mp = MP4(path)
            return bool(mp.tags and mp.tags.get("covr"))
        if ext in (".ogg", ".opus"):
            if ext == ".opus":
                o = OggOpus(path)
            else:
                o = OggVorbis(path)
            return bool(o.get("METADATA_BLOCK_PICTURE"))
    except Exception:
        return False
    return False
