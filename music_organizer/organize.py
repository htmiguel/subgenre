from __future__ import annotations

import shutil
from pathlib import Path

from music_organizer.tags import iter_audio_files, proposed_relative_path, read_tags


def plan_moves(source_dir: Path, library_root: Path | None = None) -> list[tuple[Path, Path, dict]]:
    """Return list of (src, dest_absolute, tags) for each audio file."""
    source_dir = source_dir.resolve()
    root = (library_root or source_dir).resolve()
    plans: list[tuple[Path, Path, dict]] = []
    for src in iter_audio_files(source_dir):
        tags = read_tags(src)
        rel = proposed_relative_path(src, tags)
        dest = root / rel
        plans.append((src, dest, tags))
    return plans


def apply_moves(
    plans: list[tuple[Path, Path, dict]],
    *,
    copy: bool = False,
) -> list[tuple[Path, Path]]:
    """Execute moves or copies; creates parent dirs. Returns (src, dest) applied."""
    done: list[tuple[Path, Path]] = []
    for src, dest, _tags in plans:
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.resolve() == src.resolve():
            continue
        if dest.exists():
            raise FileExistsError(f"Refusing to overwrite existing file: {dest}")
        if copy:
            shutil.copy2(src, dest)
        else:
            shutil.move(str(src), str(dest))
        done.append((src, dest))
    return done
