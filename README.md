# music-organizer

CLI to **scan** downloaded audio, **inspect** embedded tags, **preview** a tidy folder layout (`Artist/Album/NN Title.ext`), optionally **look up** recordings on MusicBrainz, and **apply** moves or copies into a library folder.

## Setup

```bash
cd ~/projects/music-organizer
python3 -m venv .venv
source .venv/bin/activate   # or `.venv\Scripts\activate` on Windows
pip install -e .
```

## Commands

| Command | Purpose |
|--------|---------|
| `music-organizer scan <dir>` | List each audio file and its tag fields (`--json` for machine-readable). |
| `music-organizer plan <dir> [--dest <library>]` | Show where files would go; default `--dest` is the same as the source tree. |
| `music-organizer apply <dir> --dest <library>` | Move (or `--copy`) into the organized layout. Refuses to overwrite existing files. |
| `music-organizer enrich <dir>` | For each file that already has **artist** and **title** in tags, query MusicBrainz (~1 request/second). Does not write tags yet—shows candidates so you can decide next steps. |

Supported extensions include `.mp3`, `.flac`, `.m4a`, `.ogg`, `.opus`, `.wav`, and a few others.

## Git branches

- `main` — scaffold.
- `music-organizer` — feature work for this tool.

## Next ideas

- Write tags from a chosen MusicBrainz match (`enrich --apply` with confirmation).
- Filename-based guessing when tags are empty.
- AcoustID / Chromaprint for unidentified files.
