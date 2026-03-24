# subgenre

CLI (`subgenre`, alias **`sg`**) that keeps a **JSON sidecar** next to each track, **organizes** into **genre** folders (or **Low Quality** if lossy bitrate is below 256 kbps), **enriches** from **MusicBrainz** + **Cover Art Archive** + optional **Spotify** + optional **librosa**, **watches** a folder, and can **learn genres** from interactive **setup** calibration.

## Install

On macOS, install **Python with Homebrew** (do not rely on Xcode or Apple Command Line Tools as your main Python source).

### Prerequisites

1. **[Homebrew](https://brew.sh/)** — if it is not installed yet:

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

Follow the post-install notes (e.g. add Homebrew to your `PATH` on Apple Silicon).

2. **Python 3**:

```bash
brew install python
```

Use `python3` and `python3 -m pip` from this install (or from [python.org](https://www.python.org/downloads/) if you prefer an installer). There is often **no** bare `python` on PATH unless you configure it.

3. **Optional**
   - **ffmpeg** — recommended if you use the `[audio]` extras (`librosa`), for formats that need decoding: `brew install ffmpeg`
   - **Node.js** — not required for subgenre; install only if you want it for other tooling: `brew install node`

### Project venv

```bash
cd ~/projects/subgenre

# If a previous venv is broken (e.g. `python` / `python3` missing inside the venv), recreate:
# rm -rf .venv

python3 -m venv .venv
.venv/bin/python3 -m pip install -U pip setuptools wheel
.venv/bin/python3 -m pip install -e .
.venv/bin/python3 -m pip install -e ".[audio]"   # optional: local tempo/key analysis
```

Always call the CLI with the venv interpreter so you never depend on `activate`:

```bash
.venv/bin/subgenre --help
.venv/bin/sg --help
```

## Setup & learned genres

First run **setup** to choose the directory to watch and optionally calibrate **10 random** tracks: you see a **proposed genre** (from tags, sidecar, and any prior rules) and can **keep or edit** it. Choices are stored under **`~/.config/subgenre/config.json`** (`genre_by_artist`, `genre_by_artist_album`) and applied on future **`scan`**, **`enrich`**, and **`organize`** (calibration overrides raw tags when present).

```bash
subgenre setup
# or
sg setup

# Re-run only calibration (uses saved watch_dir):
subgenre setup --calibrate
```

**Watch** with no path uses the directory from setup:

```bash
subgenre watch
```

Config file: `~/.config/subgenre/config.json` (or `$XDG_CONFIG_HOME/subgenre/config.json`).

## Commands

### `organize`

Moves into `--dest/<Genre|Low Quality>/Artist - Title.ext` (see earlier design). Genre comes from tags + **learned calibration**.

```bash
subgenre organize ~/Downloads/inbox --dest ~/Music/library
sg organize ~/Downloads/inbox --dest ~/Music/library --copy --no-features
```

### `enrich` / `scan` / `watch` / `inspect`

Same behavior as before; use `subgenre` or `sg` as the command name.

```bash
subgenre scan ~/Music/inbox
subgenre watch              # uses watch_dir from setup
subgenre watch ~/Other --debounce 2.0
```

## Sidecar

Metadata JSON next to each track: **`*.subgenre.json`**. Older libraries may still have **`*.music-organizer.json`**; the tool reads both and removes the legacy file after the next save.

## Notes

- **Spotify** requires `SPOTIFY_CLIENT_ID` / `SPOTIFY_CLIENT_SECRET` for catalog features.
- **librosa** may need **ffmpeg** for some formats.
- MusicBrainz is rate-limited.
