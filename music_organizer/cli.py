from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from music_organizer import __version__
from music_organizer.mb import search_recording
from music_organizer.organize import apply_moves, plan_moves
from music_organizer.tags import iter_audio_files, read_tags


def _cmd_scan(args: argparse.Namespace) -> int:
    root = Path(args.path).expanduser().resolve()
    rows = []
    for p in iter_audio_files(root):
        tags = read_tags(p)
        rows.append({"path": str(p), **{k: tags[k] for k in ("artist", "album", "title", "track", "disc")}})
    if args.json:
        print(json.dumps(rows, indent=2))
        return 0
    for r in rows:
        rel = r["path"]
        print(
            f"{rel}\n"
            f"  artist: {r['artist']!r}  album: {r['album']!r}  title: {r['title']!r}  "
            f"track: {r['track']!r}  disc: {r['disc']!r}\n"
        )
    print(f"{len(rows)} file(s).")
    return 0


def _cmd_plan(args: argparse.Namespace) -> int:
    source = Path(args.source).expanduser().resolve()
    dest_root = Path(args.dest).expanduser().resolve() if args.dest else source
    plans = plan_moves(source, dest_root)
    for src, dst, tags in plans:
        print(f"{src}\n  -> {dst}\n  tags: {tags}\n")
    print(f"{len(plans)} file(s).")
    return 0


def _cmd_apply(args: argparse.Namespace) -> int:
    source = Path(args.source).expanduser().resolve()
    dest_root = Path(args.dest).expanduser().resolve()
    plans = plan_moves(source, dest_root)
    try:
        applied = apply_moves(plans, copy=args.copy)
    except FileExistsError as e:
        print(e, file=sys.stderr)
        return 1
    for src, dst in applied:
        print(f"{'Copied' if args.copy else 'Moved'}: {src} -> {dst}")
    print(f"Done: {len(applied)} file(s).")
    return 0


def _cmd_enrich(args: argparse.Namespace) -> int:
    root = Path(args.path).expanduser().resolve()
    limit = int(args.limit)
    shown = 0
    for p in iter_audio_files(root):
        tags = read_tags(p)
        artist = tags.get("artist")
        title = tags.get("title")
        if not artist or not title:
            print(f"Skip (need artist+title in tags): {p}")
            continue
        hits = search_recording(str(artist), str(title), limit=limit)
        print(f"\n{p}\n  local: {artist!r} — {title!r}")
        if not hits:
            print("  (no MusicBrainz results)")
            continue
        for i, h in enumerate(hits, 1):
            artists = ", ".join(h["artists"]) if h["artists"] else "?"
            extra = f" [{h['disambiguation']}]" if h.get("disambiguation") else ""
            print(f"  {i}. score={h.get('score')}  {artists} — {h['title']}{extra}  id={h.get('id')}")
        shown += 1
        if args.max_files and shown >= int(args.max_files):
            break
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="music-organizer",
        description="Scan and organize local audio using tags; optional MusicBrainz search.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p_scan = sub.add_parser("scan", help="List audio files and embedded tags")
    p_scan.add_argument("path", help="Directory to scan recursively")
    p_scan.add_argument("--json", action="store_true", help="Print JSON lines")
    p_scan.set_defaults(func=_cmd_scan)

    p_plan = sub.add_parser("plan", help="Show target paths without moving files")
    p_plan.add_argument("source", help="Directory to scan")
    p_plan.add_argument(
        "--dest",
        help="Library root (default: same as source — organizes inside tree)",
        default=None,
    )
    p_plan.set_defaults(func=_cmd_plan)

    p_apply = sub.add_parser("apply", help="Move or copy files into Artist/Album/… layout")
    p_apply.add_argument("source", help="Directory to scan")
    p_apply.add_argument("--dest", required=True, help="Library root for organized output")
    p_apply.add_argument("--copy", action="store_true", help="Copy instead of move")
    p_apply.set_defaults(func=_cmd_apply)

    p_enrich = sub.add_parser(
        "enrich",
        help="Query MusicBrainz for recordings matching local artist+title (read-only; ~1s per file)",
    )
    p_enrich.add_argument("path", help="Directory to scan")
    p_enrich.add_argument("--limit", default="5", help="Max results per file (default 5)")
    p_enrich.add_argument("--max-files", type=int, default=0, help="Stop after N matched files (0 = no limit)")
    p_enrich.set_defaults(func=_cmd_enrich)

    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
