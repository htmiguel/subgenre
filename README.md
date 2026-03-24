# subgenre

CLI (`subgenre`, alias **`sg`**) that keeps a **JSON sidecar** next to each track, **organizes** into **genre** folders (or **Low Quality** if lossy bitrate is below 256 kbps), **enriches** from **MusicBrainz** + **Cover Art Archive** + optional **Spotify** + optional **librosa**, **watches** a folder, and can **learn genres** from interactive **setup** calibration.

**Interface:** [Typer](https://typer.tiangolo.com/) + [Rich](https://rich.readthedocs.io/) — structured help, tables/panels for summaries, spinners for long steps, and consistent exit codes. Requires **Python 3.11+**.

## Install

On macOS, use a current **Python 3.11+** (Homebrew `brew install python`, [python.org](https://www.python.org/downloads/), or pyenv). Apple’s `/usr/bin/python3` may be older than 3.11.

### Project venv (optional if you use `bin/subgenre`)

Manual setup — same end result the launcher performs automatically:

```bash
cd ~/projects/subgenre

# If a previous venv is broken, recreate:
# rm -rf .venv

python3 -m venv .venv
.venv/bin/python3 -m pip install -U pip setuptools wheel
.venv/bin/python3 -m pip install -e .
.venv/bin/python3 -m pip install -e ".[audio]"   # optional: librosa / local analysis
```

**Dev / tests** (optional):

```bash
.venv/bin/python3 -m pip install -e ".[dev]"
.venv/bin/python3 -m pytest
```

### Use from any Terminal (no manual venv step)

Add the repo’s **`bin/`** (not `.venv/bin`) to your **`PATH`**. The **`bin/subgenre`** launcher creates **`~/projects/subgenre/.venv`**, installs the package with **pip**, and runs the real CLI whenever something is missing or **`pyproject.toml`** changed.

Put this in **`~/.zshrc`** (change the path if your clone lives elsewhere):

```bash
export PATH="$HOME/projects/subgenre/bin:$PATH"
```

Then open a new tab or `source ~/.zshrc` and run:

```bash
subgenre --help
sg --help
```

**First run** may take a minute (network + pip). Later runs skip install unless dependencies changed.

**Optional librosa stack:** set once (or add to `.zshrc`):

```bash
export SUBGENRE_INSTALL_AUDIO=1
```

The next launch will reinstall with the `[audio]` extra when the bootstrap fingerprint changes (toggle the var, or delete `.venv/.subgenre-bootstrap-stamp`).

**Direct venv** (if you prefer not to use the launcher):

```bash
.venv/bin/subgenre --help
.venv/bin/sg --help
```

### Optional system tools

- **ffmpeg** — recommended with `[audio]` for formats librosa decodes via ffmpeg: `brew install ffmpeg`

## Global options

| Option | Purpose |
|--------|---------|
| `--verbose` / `-v` | More library log output |
| `--no-color` | No ANSI (also respects `NO_COLOR`) |
| `--json` | Machine-readable output where supported (`status`, `scan`, `inspect`, `organize`, `enrich`, `deploy`) |
| `--version` | Print version and exit |

Running **`subgenre`** with no subcommand prints help (exit 0).

## Commands (overview)

| Command | Purpose |
|---------|---------|
| `status` | Config path, watch dir, Python — health-style summary |
| `setup` | Interactive config + optional calibration |
| `init` | **Alias for `setup`** |
| `scan` | Sidecar: tags + audio + optional features |
| `organize` | Refresh sidecars, then move/copy into `--dest` layout |
| `enrich` | MusicBrainz + art + optional Spotify/librosa |
| `watch` | Watch folder; debounced scan on new files |
| `deploy` | Mirror the whole library tree to another path (backup / drive / staging) |
| `inspect` | Print embedded tags only (no sidecar writes) |

## Setup & learned genres

First run **setup** (or **`init`**) to choose the watch directory and optionally calibrate **10 random** tracks. Rules live in **`~/.config/subgenre/config.json`** (or `$XDG_CONFIG_HOME/subgenre/config.json`).

```bash
subgenre setup
subgenre setup --calibrate
```

**Watch** with no path uses the directory from setup:

```bash
subgenre watch
```

## Examples

```bash
subgenre status
subgenre --json status | jq .

subgenre scan ~/Music/inbox
subgenre organize ~/Downloads/inbox --dest ~/Music/library
subgenre organize ~/Inbox --dest ~/Music/library --copy --yes
subgenre enrich ~/Music/album
subgenre watch ~/Other --debounce 2.0

# Full-tree mirror (preserves genre folders + sidecars + any other files)
subgenre deploy ~/Music/library /Volumes/Backup/Music --dry-run
subgenre deploy ~/Music/library /Volumes/Backup/Music --yes
subgenre deploy ~/Music/library /Volumes/Backup/Music --skip-existing --yes
```

**Organize (move)** asks for confirmation in a TTY unless you pass **`--yes`** / **`-y`** or use **`--copy`**.

**Deploy** copies every file under the source root into the target, keeping relative paths. It refuses if the target sits inside the source (or the reverse). If a file already exists at the destination, use **`--overwrite`** to replace it or **`--skip-existing`** to leave it and continue. A TTY prompts before copying unless you pass **`--yes`**.

## Sidecar

Metadata JSON next to each track: **`*.subgenre.json`**. Older trees may still have **`*.music-organizer.json`**; the tool reads both and removes the legacy file after the next save.

## Notes

- **Spotify** requires `SPOTIFY_CLIENT_ID` / `SPOTIFY_CLIENT_SECRET` for catalog features.
- **librosa** may need **ffmpeg** for some formats.
- MusicBrainz is rate-limited.

## UX / copy rationale

- **Centralized strings** (`subgenre/copy.py`) and **semantic styles** (`subgenre/theme.py`) keep tone consistent and avoid ad-hoc ANSI in command code.
- **Color** is used for meaning (success / warning / error / info), not decoration; **`--no-color`** and non-TTY output disable styling.
- **Errors** spell out what failed, a likely cause, and a concrete next step (see `copy.py` and organize/watch paths in `cli.py`).
- **Before → after:** the default argparse line *“the following arguments are required: command”* is replaced by Typer’s guided help and, for domain errors, short panels/messages with fixes — documented in `copy.py`.
