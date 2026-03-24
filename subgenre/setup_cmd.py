from __future__ import annotations

import random
import sys
from pathlib import Path

from subgenre.config_store import (
    config_path,
    get_watch_dir,
    load_config,
    record_genre_calibration,
    resolve_genre,
    save_config,
)
from subgenre.sidecar import load_sidecar
from subgenre.tags import iter_audio_files, read_tags_full


def _prompt_line(prompt: str, default: str | None = None) -> str:
    if default:
        tip = f" [{default}]"
    else:
        tip = ""
    try:
        line = input(f"{prompt}{tip}: ").strip()
    except EOFError:
        line = ""
    if not line and default is not None:
        return default
    return line


def _propose_genre(path: Path) -> tuple[str, dict]:
    tags = read_tags_full(path)
    side = load_sidecar(path)
    tr = side.get("track") or {}
    tag_g = tags.get("genre") if isinstance(tags.get("genre"), str) else None
    side_g = tr.get("genre") if isinstance(tr.get("genre"), str) else None
    artist = tags.get("artist") if isinstance(tags.get("artist"), str) else None
    album = tags.get("album") if isinstance(tags.get("album"), str) else None
    merged_g = tag_g or side_g
    proposed = resolve_genre(artist, album, merged_g)
    return proposed, {
        "artist": artist,
        "album": album,
        "title": tags.get("title"),
        "tag_genre": tag_g,
    }


def run_calibration(watch_path: Path) -> int:
    """Interactive genre calibration for up to 10 random files under watch_path."""
    files = iter_audio_files(watch_path)
    if len(files) < 1:
        print("No audio files found under the watch directory; skipping calibration.")
        return 0

    k = min(10, len(files))
    sample = random.sample(files, k=k)
    print(f"Calibration: {k} random file(s) from {watch_path}\n")

    for i, path in enumerate(sample, 1):
        proposed, meta = _propose_genre(path)
        artist = meta.get("artist")
        album = meta.get("album")
        title = meta.get("title") or path.stem
        print(f"--- {i}/{k} ---")
        print(f"  File: {path}")
        print(f"  Artist: {artist or '(unknown)'}")
        print(f"  Album:  {album or '(unknown)'}")
        print(f"  Title:  {title}")
        print(f"  Proposed genre: {proposed}")
        try:
            raw = input("  Genre [Enter = keep, or type a new genre]: ").strip()
        except EOFError:
            raw = ""
        final = raw if raw else proposed
        record_genre_calibration(
            artist=artist,
            album=album,
            proposed=proposed,
            final=final,
            path=str(path),
        )
        print(f"  Recorded → {final!r}\n")

    print("Calibration saved. Future scans/organize steps use these genres when matching artist/album.")
    return 0


def run_calibrate_only() -> int:
    """Re-run calibration using watch_dir from config."""
    wp = get_watch_dir()
    if not wp:
        print("No watch_dir in config. Run:  subgenre setup", file=sys.stderr)
        return 1
    return run_calibration(wp)


def run_setup(*, calibration: bool | None = None) -> int:
    """
    Interactive: watch directory, optional genre calibration on random files.
    """
    print("subgenre setup — configure watch folder and optional genre calibration.\n")
    cfg = load_config()
    current = cfg.get("watch_dir")
    default_watch = ""
    if current:
        default_watch = str(Path(str(current)).expanduser())
    wd_guess = get_watch_dir()
    if wd_guess and not default_watch:
        default_watch = str(wd_guess)

    wd = _prompt_line("Directory to watch (new files get scan + features)", default_watch or None)
    if not wd:
        print("No directory given; aborting.", file=sys.stderr)
        return 1
    watch_path = Path(wd).expanduser().resolve()
    if not watch_path.is_dir():
        print(f"Not a directory: {watch_path}", file=sys.stderr)
        return 1

    cfg["watch_dir"] = str(watch_path)
    save_config(cfg)
    print(f"Saved watch directory → {config_path()}")
    print(f"  watch_dir = {watch_path}\n")

    if calibration is None:
        cal = _prompt_line("Run calibration (10 random tracks, confirm or edit genre)?", "n").lower()
        calibration = cal in ("y", "yes")

    if not calibration:
        print("You can calibrate later with:  subgenre setup --calibrate")
        return 0

    return run_calibration(watch_path)
