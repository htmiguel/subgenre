from __future__ import annotations

from pathlib import Path
from typing import Any

from mutagen import File as MutagenFile


def _mime(audio: Any) -> str:
    m = getattr(audio, "mime", None) or []
    return m[0] if m else ""


def analyze_file(path: Path) -> dict[str, Any]:
    """
    Bitrate (kbps) for lossy codecs; lossless flag; channels; length seconds.
    Lossless formats omit meaningful bitrate for the low-quality rule.
    """
    path = path.resolve()
    try:
        audio = MutagenFile(path)
    except Exception:
        audio = None
    if audio is None:
        return {
            "bitrate_kbps": None,
            "lossless": False,
            "channels": None,
            "length_seconds": None,
            "format": None,
        }

    mime = _mime(audio)
    info = getattr(audio, "info", None)
    length = float(getattr(info, "length", 0) or 0) or None
    channels = getattr(info, "channels", None)

    lossless = False
    if "flac" in mime or path.suffix.lower() == ".flac":
        lossless = True
    elif "wav" in mime or path.suffix.lower() == ".wav":
        lossless = True
    elif path.suffix.lower() == ".m4a" or "mp4" in mime:
        # ALAC vs AAC — check bits_per_sample on info if available
        bps = getattr(info, "bits_per_sample", None)
        if bps and int(bps) > 16:
            lossless = True
        # mutagen doesn't always expose ALAC clearly; heuristic: bitrate 0 or very high
        br = getattr(info, "bitrate", None)
        if br is None and mime and "alac" in str(type(info)).lower():
            lossless = True

    bitrate_kbps: int | None = None
    br = getattr(info, "bitrate", None) if info else None
    if br is not None and not lossless:
        try:
            bitrate_kbps = max(1, int(round(int(br) / 1000)))
        except (TypeError, ValueError):
            bitrate_kbps = None

    return {
        "bitrate_kbps": bitrate_kbps,
        "lossless": lossless,
        "channels": channels,
        "length_seconds": length,
        "format": mime or path.suffix.lower().lstrip("."),
    }


def is_low_quality(audio: dict[str, Any], threshold_kbps: int = 256) -> bool:
    if audio.get("lossless"):
        return False
    br = audio.get("bitrate_kbps")
    if br is None:
        return False
    return int(br) < threshold_kbps
