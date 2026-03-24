# music-organizer

CLI that keeps a **JSON sidecar** next to each track (`Artist Title.music-organizer.json`), **organizes** into **genre** folders (or **Low Quality** if lossy bitrate is below 256 kbps), **enriches** from **MusicBrainz** + **Cover Art Archive** + optional **Spotify** + optional **librosa**, and can **watch** a folder and auto-run **scan** when new audio appears.

## Install

```bash
cd ~/projects/music-organizer
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e .
# For local tempo/key/spectral-style analysis (EchoNest-ish fallbacks):
pip install -e ".[audio]"
```

## Commands

### `organize`

1. Refreshes each file’s sidecar from **embedded tags** + **technical audio** (bitrate, lossless, length, …).
2. Optionally runs **Spotify + librosa** (`--no-features` skips that).
3. Moves (or `--copy`) into `--dest`:

   - **`Low Quality/`** — lossy codec and `bitrate_kbps < 256` (FLAC/WAV-style lossless is never sent here).
   - **`<Genre>/`** — from the `genre` field after enrichment/tags (`Unknown Genre` if missing).
   - Filename: **`Artist - Title.ext`**
4. Moves the **sidecar** next to the audio file in the new location.

```bash
music-organizer organize ~/Downloads/inbox --dest ~/Music/library
music-organizer organize ~/Downloads/inbox --dest ~/Music/library --copy --no-features
```

### `enrich`

When anything important is missing, pulls data from the network and **writes tags + sidecar**:

- **MusicBrainz** — artist, title, album, year, genre (tag), label, recording/release IDs; **label area** from release country or label entity when available.
- **Cover Art Archive** — front art embedded (MP3/FLAC/M4A).
- **Spotify Web API** (optional) — danceability, energy, valence, **tempo**, **key**, etc. (needs catalog match).

Set:

```bash
export SPOTIFY_CLIENT_ID=...
export SPOTIFY_CLIENT_SECRET=...
```

- **librosa** (optional extra `.[audio]`) — local **tempo** + **key** estimate and a simple **energy** proxy if Spotify is unavailable.

```bash
music-organizer enrich ~/Music/some-album
music-organizer enrich ~/Music/track.mp3 --dry-run
```

Run **`enrich` before `organize`** if you need genre/label/year filled from the web.

### `scan`

Writes/updates the sidecar from **tags + technical audio + Spotify + librosa** — **no MusicBrainz** (use `enrich` for that). Same pipeline the watcher uses.

```bash
music-organizer scan ~/Music/inbox
music-organizer scan ~/Music/inbox --no-features
```

### `watch`

Recursively watches a directory; after **`--debounce`** seconds of quiet (default **2**), each new **audio** file gets **`scan`** (with features if installed).

```bash
music-organizer watch ~/Music/inbox --debounce 2.0
```

### `inspect`

Print embedded tags only — **does not** write sidecars.

## Sidecar shape (high level)

- **`track`** — artist, title, album, genre, label, `label_area`, year, ids, BPM, key, …  
- **`audio`** — `bitrate_kbps`, `lossless`, `length_seconds`, …  
- **`features`** — Spotify-style metrics when available; librosa **tempo** / **key** / **energy** when not.  
- **`cover`** — `embedded` flag.  
- **`sources`** — e.g. `tags`, `musicbrainz`, `spotify`, `librosa`.

## Git

Feature work lives on branch **`music-organizer`** (see `git branch`).

## Notes

- **Spotify** features need a **matching track** in Spotify’s catalog; local-only files still get **librosa** when the extra is installed.
- **librosa** loading of some formats may need **ffmpeg** on your PATH.
- Be polite: MusicBrainz is rate-limited; bulk `enrich` is intentionally throttled.
