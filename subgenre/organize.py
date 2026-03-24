from __future__ import annotations

import shutil
from pathlib import Path

from subgenre.audio_info import is_low_quality
from subgenre.scan import collect_metadata
from subgenre.sidecar import sidecar_path
from subgenre.tags import iter_audio_files, safe_path_component


LOW_QUALITY_FOLDER = "Low Quality"


def destination_path(library_root: Path, audio_path: Path, bundle: dict) -> Path:
    """Genre bucket or Low Quality; filename `Artist - Title.ext`."""
    library_root = library_root.resolve()
    track = bundle.get("track") or {}
    audio = bundle.get("audio") or {}

    if is_low_quality(audio):
        bucket = LOW_QUALITY_FOLDER
    else:
        genre = track.get("genre")
        bucket = safe_path_component(genre if isinstance(genre, str) else None, "Unknown Genre")

    artist = safe_path_component(track.get("artist") if isinstance(track.get("artist"), str) else None, "Unknown Artist")
    title = safe_path_component(track.get("title") if isinstance(track.get("title"), str) else None, audio_path.stem)
    ext = audio_path.suffix.lower() or audio_path.suffix
    return library_root / bucket / f"{artist} - {title}{ext}"


def organize_tree(
    source: Path,
    dest: Path,
    *,
    copy: bool = False,
    with_features: bool = False,
) -> list[tuple[Path, Path]]:
    """
    Refresh sidecar (tags + audio; optional analysis), then move each audio file + sidecar
    into `dest / [Genre|Low Quality] / Artist - Title.ext`.
    """
    source = source.resolve()
    dest = dest.resolve()
    applied: list[tuple[Path, Path]] = []

    for src in iter_audio_files(source):
        collect_metadata(src, features=with_features)
        # Reload bundle from disk after collect_metadata wrote it
        from subgenre.sidecar import load_sidecar

        bundle = load_sidecar(src)
        dst_audio = destination_path(dest, src, bundle)
        dst_audio.parent.mkdir(parents=True, exist_ok=True)

        if dst_audio.resolve() == src.resolve():
            continue
        if dst_audio.exists():
            raise FileExistsError(f"Refusing to overwrite existing file: {dst_audio}")

        sc_src = sidecar_path(src)
        sc_dst = sidecar_path(dst_audio)

        if copy:
            shutil.copy2(src, dst_audio)
            if sc_src.is_file():
                shutil.copy2(sc_src, sc_dst)
        else:
            shutil.move(str(src), str(dst_audio))
            if sc_src.is_file():
                if sc_dst.exists():
                    sc_dst.unlink()
                shutil.move(str(sc_src), str(sc_dst))

        applied.append((src, dst_audio))

    return applied
