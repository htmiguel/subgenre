# subgenre

CLI (`subgenre`, alias **`sg`**) that keeps a **JSON sidecar** next to each track, **organizes** into **genre** folders (or **Low Quality** if lossy bitrate is below 256 kbps), **enriches** from **MusicBrainz** + **Cover Art Archive** + optional **Spotify** + optional **librosa**, **watches** a folder, and can **learn genres** from interactive **setup** calibration.

## Install

On macOS, use **`python3`** (and **`pip` via `python3 -m pip`**). There is usually **no** `python` command unless you install one.

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

### No `python3` at all?

Install Apple’s **Command Line Tools** (includes `/usr/bin/python3`):

```bash
xcode-select --install
```

Or install **Python** from [python.org](https://www.python.org/downloads/) or Homebrew (`brew install python`), then use the `python3` / `pip3` from that install to create `.venv` as above.

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
