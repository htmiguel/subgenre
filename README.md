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

# subgenre

CLI (`subgenre`, alias **`sg`**) that keeps a **JSON sidecar** next to each track, **organizes** into **genre** folders (or **Low Quality** if lossy bitrate is below 256 kbps), **enriches** from **MusicBrainz** + **Cover Art Archive** + optional **Spotify** + optional **librosa**, **watches** a folder, and can **learn genres** from interactive **setup** calibration.

**Interface:** [Typer](https://typer.tiangolo.com/) + [Rich](https://rich.readthedocs.io/). Needs **Python 3.11+** on your PATH (the launcher uses it automatically).

**To run `subgenre` from any folder:** add one line to **`~/.zshrc`** (step 3 below). After that, you can open Terminal, stay in your home folder, `~/Music`, or anywhere else—no `cd` into the repo.

## First-time setup (happy path)

Do this once per machine.

### 1. Python 3.11+

macOS: Apple’s built-in Python is often too old. Use Homebrew (or [python.org](https://www.python.org/downloads/)):

```bash
brew install python
```

Check: `python3 --version` should show **3.11** or newer.

### 2. Clone the repo (if you don’t have it yet)

```bash
git clone https://github.com/htmiguel/subgenre.git ~/projects/subgenre
```

Use any folder you like; **step 3** must use that same folder in the PATH line.

### 3. Add `subgenre` to your PATH (`~/.zshrc`) — **run from any directory**

This is the step that makes **`subgenre`** and **`sg`** work from **anywhere** in Terminal (you never need `cd` into the project to run the command).

1. **Open your zsh config file** (create it if it doesn’t exist):

   ```bash
   nano ~/.zshrc
   ```

   Or open `~/.zshrc` in your editor (Cursor, VS Code, etc.). On macOS with zsh, this file is **`~/.zshrc`**, not `bash_profile`.

2. **Paste this line** at the **bottom** of the file (change the path if you didn’t clone to `~/projects/subgenre`):

   ```bash
   # subgenre — callable from any directory (uses repo bin/ launcher + auto .venv)
   export PATH="$HOME/projects/subgenre/bin:$PATH"
   ```

   If your clone lives elsewhere, only change the middle part, e.g.  
   `export PATH="$HOME/code/subgenre/bin:$PATH"`.

3. **If you already set PATH as one long line**  
   Some dotfiles end with something like  
   `export PATH="/usr/bin:/opt/homebrew/bin:…"`  
   That line **replaces** the entire PATH, so anything you added **above** it disappears.

   **Do one of these:**

   - **Easiest:** Paste the subgenre `export PATH="$HOME/projects/subgenre/bin:$PATH"` line **after** that long `export PATH=…` (so it runs last and wins), **or**
   - **Alternative:** Add **`$HOME/projects/subgenre/bin`** (or the full path to `…/subgenre/bin`) **into** that long path string, with colons between entries.

4. **Reload zsh** so the change applies:

   ```bash
   source ~/.zshrc
   ```

   New Terminal tabs/windows will pick it up automatically.

5. **Confirm** you can run from a random directory:

   ```bash
   cd ~
   command -v subgenre
   subgenre --version
   ```

   You should see a path ending in **`subgenre/bin/subgenre`**.

**What this does:** The **`bin/subgenre`** script lives in the repo. Putting **`…/subgenre/bin`** on PATH lets the shell find it from any folder. That script creates **`.venv`**, runs **pip** when needed, then starts the real CLI—you don’t run `venv`/`pip` by hand for normal use.

**Optional (aliases):** If you prefer not to touch PATH, you can instead add:

```bash
alias subgenre="$HOME/projects/subgenre/bin/subgenre"
alias sg="$HOME/projects/subgenre/bin/sg"
```

Still use your real clone path. Aliases also work from any directory after `source ~/.zshrc`.

### 4. First real run

```bash
subgenre --help
```

The **first** `subgenre` run may take **~1 minute** (downloads packages; needs internet). Later runs are quick unless **`pyproject.toml`** changes.

### 5. Configure the tool

```bash
subgenre setup
```

(`sg` is the same program as `subgenre`.)

---

### Optional: tempo/key analysis (librosa)

```bash
export SUBGENRE_INSTALL_AUDIO=1
```

Add that to `~/.zshrc` if you want it every time, then run `subgenre` once so it reinstalls with the **`[audio]`** extra. For some formats you’ll want **`brew install ffmpeg`**.

### Troubleshooting

| Problem | What to try |
|--------|-------------|
| `command not found: subgenre` | PATH line missing, wrong path, or it’s **above** a full `PATH=` reset — move subgenre **after** that line (see step 3). |
| Python too old | Install newer Python; ensure `python3.11` (or `python3.12`, …) is on PATH before Apple’s `python3`. |
| Broken old venv | Delete **`subgenre/.venv`** and run `subgenre --help` again. |

### Advanced: manual venv (no launcher)

```bash
cd ~/projects/subgenre
python3 -m venv .venv
.venv/bin/python3 -m pip install -U pip setuptools wheel
.venv/bin/python3 -m pip install -e .
.venv/bin/subgenre --help
```

Optional: `.venv/bin/python3 -m pip install -e ".[audio]"` and **`pip install -e ".[dev]"`** + **`pytest`** for development.

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
