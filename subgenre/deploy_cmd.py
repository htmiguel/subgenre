"""Mirror a library tree to a target path (backup / external drive / staging)."""

from __future__ import annotations

import shutil
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

ProgressHook = Callable[[int, int, Path], None]


class DeployError(Exception):
    """User-facing deploy failure."""


class DeployFlagError(DeployError):
    """Invalid combination of CLI flags."""


@dataclass
class DeployResult:
    """Totals after a deploy (or dry-run)."""

    copied: int = 0
    skipped: int = 0
    bytes_copied: int = 0
    files_planned: int = 0
    errors: list[str] = field(default_factory=list)


def _forbidden_overlap(source: Path, target: Path) -> str | None:
    """Return error message if paths would recurse or alias; else None."""
    src = source.resolve()
    dst = target.resolve()
    if src == dst:
        return "Source and target are the same path."
    try:
        dst.relative_to(src)
        return "Target cannot be inside the source tree (would copy into itself)."
    except ValueError:
        pass
    try:
        src.relative_to(dst)
        return "Source cannot be inside the target tree (risk of overwriting the library you are reading)."
    except ValueError:
        pass
    return None


def iter_files(root: Path) -> list[Path]:
    root = root.resolve()
    return sorted(p for p in root.rglob("*") if p.is_file())


def run_deploy(
    source: Path,
    target: Path,
    *,
    dry_run: bool = False,
    overwrite: bool = False,
    skip_existing: bool = False,
    progress_hook: ProgressHook | None = None,
) -> DeployResult:
    if overwrite and skip_existing:
        raise DeployFlagError("Use either --overwrite or --skip-existing, not both.")

    source = source.expanduser().resolve()
    target = target.expanduser().resolve()
    if not source.is_dir():
        raise DeployError(f"Source is not a directory: {source}")

    msg = _forbidden_overlap(source, target)
    if msg:
        raise DeployError(msg)

    files = iter_files(source)
    out = DeployResult(files_planned=len(files))
    tgt_root = target.resolve()
    total = len(files)

    for idx, src_file in enumerate(files, start=1):
        rel = src_file.relative_to(source)
        dst_file = (target / rel).resolve()
        try:
            dst_file.relative_to(tgt_root)
        except ValueError:
            out.errors.append(f"Unsafe path (traversal): {rel}")
            if progress_hook:
                progress_hook(idx, total, src_file)
            continue

        if dst_file.exists() or dst_file.is_symlink():
            if skip_existing:
                out.skipped += 1
                if progress_hook:
                    progress_hook(idx, total, src_file)
                continue
            if not overwrite:
                raise DeployError(
                    f"Destination already exists: {dst_file}\n"
                    "Likely reason: a previous deploy or duplicate layout.\n"
                    "Fix: pass --overwrite to replace, or --skip-existing to leave files as-is."
                )

        try:
            sz = src_file.stat().st_size
        except OSError:
            sz = 0

        if dry_run:
            out.copied += 1
            out.bytes_copied += sz
            if progress_hook:
                progress_hook(idx, total, src_file)
            continue

        dst_file.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src_file, dst_file)
        out.copied += 1
        out.bytes_copied += sz
        if progress_hook:
            progress_hook(idx, total, src_file)

    return out
