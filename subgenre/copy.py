"""
Central user-facing copy for the CLI.

Copy improvement note (before vs after):
- Before: argparse default "the following arguments are required: command"
- After: short explanation + one concrete next step (see theme + cli error helpers)
"""

from __future__ import annotations

APP_TAGLINE = "Organize and enrich local audio with sidecars, genres, and optional analysis."

# --- Global / meta
HELP_EPILOG_EXAMPLES = """
[accent]Examples[/accent]
  subgenre [info]status[/info]                    # config + environment
  subgenre [info]setup[/info]                     # first-time config (alias: [info]init[/info])
  subgenre [info]scan[/info] ~/Music/inbox
  subgenre [info]organize[/info] ~/Inbox [info]--dest[/info] ~/Music/library
  subgenre [info]deploy[/info] ~/Music/library /Volumes/USB/Mirror [info]--dry-run[/info]
  subgenre [info]watch[/info]                     # uses watch dir from setup
"""

# --- Errors (what failed, likely reason, next step)
ERR_NO_WATCH_DIR = (
    "Watch directory is not configured.\n"
    "[muted]Likely reason:[/muted] setup has not been run, or config was removed.\n"
    "[muted]Fix:[/muted] run [accent]subgenre setup[/accent], then try again."
)

ERR_ORGANIZE_DEST_EXISTS = (
    "Refused to overwrite an existing file in the library.\n"
    "[muted]Likely reason:[/muted] same artist/title already exists at the destination.\n"
    "[muted]Fix:[/muted] remove or rename the file in [accent]--dest[/accent], or pick a different library root."
)

ERR_INTERRUPTED = (
    "Interrupted.\n"
    "[muted]Fix:[/muted] run the same command again when ready."
)

ERR_DEPLOY_FLAGS = (
    "Cannot combine [accent]--overwrite[/accent] and [accent]--skip-existing[/accent].\n"
    "[muted]Fix:[/muted] pick one strategy for files that already exist at the target."
)

# --- Status
STATUS_TITLE = "subgenre status"
STATUS_CAPTION = "Paths use your shell’s home; config follows XDG when set."

# --- Summaries
SUMMARY_DONE = "Done"
SUMMARY_ORGANIZE = "Organize complete"
SUMMARY_SCAN = "Scan complete"
SUMMARY_ENRICH = "Enrich complete"
SUMMARY_WATCH_START = "Watching for new audio"
SUMMARY_SETUP = "Setup finished"
SUMMARY_DEPLOY = "Deploy complete"

# --- Organize
ORGANIZE_CONFIRM = (
    "Move [accent]{n}[/accent] file(s) from [accent]{source}[/accent] "
    "into [accent]{dest}[/accent] (not a copy). Continue?"
)

DEPLOY_CONFIRM = (
    "Copy [accent]{n}[/accent] file(s) from [accent]{source}[/accent] "
    "to [accent]{target}[/accent]? Existing files will stop the run unless you use "
    "[accent]--overwrite[/accent] or [accent]--skip-existing[/accent]."
)

# --- Watch
WATCH_DEBOUNCE_HINT = "[muted]Debounce[/muted] {debounce}s — processing runs after the folder is quiet."
