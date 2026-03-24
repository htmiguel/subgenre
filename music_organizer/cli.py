from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from music_organizer import __version__
from music_organizer.enrich import enrich_file, enrich_tree
from music_organizer.organize import organize_tree
from music_organizer.scan import scan_tree
from music_organizer.tags import iter_audio_files, read_tags_full
from music_organizer.watch_cmd import watch_folder


def _cmd_scan(args: argparse.Namespace) -> int:
    root = Path(args.path).expanduser().resolve()
    scan_tree(root, features=not args.no_features)
    if args.json:
        rows = []
        for p in iter_audio_files(root):
            from music_organizer.sidecar import load_sidecar

            rows.append({"path": str(p), **load_sidecar(p)})
        print(json.dumps(rows, indent=2, default=str))
        return 0
    for p in iter_audio_files(root):
        from music_organizer.sidecar import load_sidecar

        bundle = load_sidecar(p)
        print(f"{p}\n{json.dumps(bundle, indent=2, default=str)}\n")
    return 0


def _cmd_organize(args: argparse.Namespace) -> int:
    source = Path(args.source).expanduser().resolve()
    dest = Path(args.dest).expanduser().resolve()
    try:
        pairs = organize_tree(
            source,
            dest,
            copy=args.copy,
            with_features=not args.no_features,
        )
    except FileExistsError as e:
        print(e, file=sys.stderr)
        return 1
    for src, dst in pairs:
        print(f"{'Copied' if args.copy else 'Moved'}: {src} -> {dst}")
    print(f"Done: {len(pairs)} file(s).")
    return 0


def _cmd_enrich(args: argparse.Namespace) -> int:
    root = Path(args.path).expanduser().resolve()
    if root.is_file():
        enrich_file(root, dry_run=args.dry_run)
        print(root)
        return 0
    enrich_tree(root, dry_run=args.dry_run)
    n = len(iter_audio_files(root))
    print(f"Enriched {n} file(s) under {root}.")
    return 0


def _cmd_watch(args: argparse.Namespace) -> int:
    watch_folder(Path(args.path), debounce_s=float(args.debounce))
    return 0


def _cmd_inspect(args: argparse.Namespace) -> int:
    """Lightweight tag-only listing (no sidecar write)."""
    root = Path(args.path).expanduser().resolve()
    rows = []
    for p in iter_audio_files(root):
        tags = read_tags_full(p)
        rows.append({"path": str(p), **tags})
    if args.json:
        print(json.dumps(rows, indent=2))
        return 0
    for r in rows:
        print(f"{r['path']}\n  { {k: r[k] for k in r if k != 'path'} }\n")
    print(f"{len(rows)} file(s).")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="music-organizer",
        description="Organize by genre / bitrate, enrich from MusicBrainz + Spotify + librosa, watch folder.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p_scan = sub.add_parser("scan", help="Write sidecar: tags + audio + Spotify/librosa features (no MusicBrainz)")
    p_scan.add_argument("path", help="Directory to scan recursively")
    p_scan.add_argument("--json", action="store_true", help="Print merged sidecar JSON after scan")
    p_scan.add_argument(
        "--no-features",
        action="store_true",
        help="Skip Spotify + librosa (tags + bitrate only)",
    )
    p_scan.set_defaults(func=_cmd_scan)

    p_org = sub.add_parser(
        "organize",
        help="Refresh sidecar, then move into dest / [Genre|Low Quality] / Artist - Title.ext",
    )
    p_org.add_argument("source", help="Directory to read audio from")
    p_org.add_argument("--dest", required=True, help="Library root")
    p_org.add_argument("--copy", action="store_true", help="Copy instead of move")
    p_org.add_argument(
        "--no-features",
        action="store_true",
        help="Sidecar refresh without Spotify/librosa (faster)",
    )
    p_org.set_defaults(func=_cmd_organize)

    p_en = sub.add_parser(
        "enrich",
        help="Fill missing tags from MusicBrainz + cover; BPM/key/features from Spotify + librosa; write sidecar",
    )
    p_en.add_argument("path", help="Audio file or directory")
    p_en.add_argument("--dry-run", action="store_true", help="Fetch and print logic only (no writes)")
    p_en.set_defaults(func=_cmd_enrich)

    p_w = sub.add_parser(
        "watch",
        help="Watch a folder; new audio files trigger scan (tags + audio + features) after debounce",
    )
    p_w.add_argument("path", help="Directory to watch (recursive)")
    p_w.add_argument("--debounce", default="2.0", help="Seconds of quiet before processing (default 2)")
    p_w.set_defaults(func=_cmd_watch)

    p_in = sub.add_parser("inspect", help="Print embedded tags only (does not write sidecars)")
    p_in.add_argument("path", help="Directory to scan")
    p_in.add_argument("--json", action="store_true")
    p_in.set_defaults(func=_cmd_inspect)

    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.WARNING)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
