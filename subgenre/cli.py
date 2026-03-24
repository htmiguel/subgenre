from __future__ import annotations

import json
import logging
import os
import sys
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import typer
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TaskProgressColumn, TextColumn, TimeElapsedColumn
from rich.prompt import Confirm
from rich.table import Table

from subgenre import __version__
from subgenre.copy import (
    APP_TAGLINE,
    DEPLOY_CONFIRM,
    ERR_DEPLOY_FLAGS,
    ERR_INTERRUPTED,
    ERR_NO_WATCH_DIR,
    ERR_ORGANIZE_DEST_EXISTS,
    HELP_EPILOG_EXAMPLES,
    ORGANIZE_CONFIRM,
    STATUS_CAPTION,
    STATUS_TITLE,
    SUMMARY_DEPLOY,
    SUMMARY_DONE,
    SUMMARY_ENRICH,
    SUMMARY_ORGANIZE,
    SUMMARY_SCAN,
    SUMMARY_SETUP,
    SUMMARY_WATCH_START,
    WATCH_DEBOUNCE_HINT,
)
from subgenre.deploy_cmd import DeployError, DeployFlagError, iter_files, run_deploy
from subgenre.enrich import enrich_file, enrich_tree
from subgenre.organize import organize_tree
from subgenre.scan import scan_tree
from subgenre.setup_cmd import run_calibrate_only, run_setup
from subgenre.tags import iter_audio_files, read_tags_full
from subgenre.theme import get_symbols, make_console, should_use_color
from subgenre.watch_cmd import watch_folder

# Quieter default imports (urllib3 vs LibreSSL on macOS system Python)
try:
    from urllib3.exceptions import NotOpenSSLWarning
except ImportError:
    NotOpenSSLWarning = None  # type: ignore[misc, assignment]

if NotOpenSSLWarning is not None:
    warnings.filterwarnings("ignore", category=NotOpenSSLWarning)

rich_help = (
    "[accent]subgenre[/accent] — " + APP_TAGLINE + "\n\n" + HELP_EPILOG_EXAMPLES
)


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"subgenre {__version__}")
        raise typer.Exit(0)


@dataclass
class CLIState:
    verbose: bool = False
    no_color: bool = False
    json_output: bool = False


app = typer.Typer(
    name="subgenre",
    help=rich_help,
    rich_markup_mode="rich",
    no_args_is_help=False,
    pretty_exceptions_enable=False,
    context_settings={"help_option_names": ["-h", "--help"]},
    epilog=None,
)


@app.callback(invoke_without_command=True)
def main_callback(
    ctx: typer.Context,
    verbose: bool = typer.Option(False, "--verbose", "-v", help="More log output from libraries."),
    no_color: bool = typer.Option(False, "--no-color", help="Disable ANSI colors (also respects NO_COLOR)."),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Machine-readable output for commands that support it (scan, inspect, organize, enrich, status, deploy).",
    ),
    version: bool = typer.Option(
        False,
        "--version",
        callback=_version_callback,
        is_eager=True,
        help="Print version and exit.",
    ),
) -> None:
    """Local audio: sidecars, genres, MusicBrainz, watch folder."""
    ctx.obj = CLIState(verbose=verbose, no_color=no_color, json_output=json_output)
    level = logging.INFO if verbose else logging.WARNING
    logging.basicConfig(level=level, format="%(message)s")
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())
        raise typer.Exit(0)


def _state(ctx: typer.Context) -> CLIState:
    return ctx.obj  # type: ignore[return-value]


def _console(state: CLIState) -> Any:
    return make_console(no_color=state.no_color)


def _use_unicode(state: CLIState) -> bool:
    return should_use_color(no_color_flag=state.no_color) and sys.stderr.isatty()


def _maybe_spinner(console: Any, message: str, *, active: bool):
    if not active:
        from contextlib import nullcontext

        return nullcontext()
    return console.status(message, spinner="dots")


def cmd_status(ctx: typer.Context) -> None:
    """Show config path, watch directory, and Python environment."""
    state = _state(ctx)
    console = _console(state)
    from subgenre.config_store import config_path, get_watch_dir

    cp = config_path()
    wd = get_watch_dir()
    sym = get_symbols(prefer_unicode=_use_unicode(state))

    data: dict[str, Any] = {
        "version": __version__,
        "config_path": str(cp),
        "config_exists": cp.is_file(),
        "watch_dir": str(wd) if wd else None,
        "python": sys.version.split()[0],
        "platform": sys.platform,
    }

    if state.json_output:
        typer.echo(json.dumps(data, indent=2))
        raise typer.Exit(0)

    table = Table(title=STATUS_TITLE, caption=STATUS_CAPTION, show_header=True, header_style="accent")
    table.add_column("Check", style="info", no_wrap=True)
    table.add_column("Result", style="default")

    cfg_status = f"{sym.ok} found" if data["config_exists"] else f"{sym.warn} missing (will be created on setup)"
    table.add_row("Config file", str(cp))
    table.add_row("Config readable", cfg_status)
    if wd:
        table.add_row("Watch directory", str(wd))
    else:
        table.add_row("Watch directory", f"{sym.warn} not set — run [accent]subgenre setup[/accent]")

    table.add_row("Python", data["python"])
    table.add_row("Platform", data["platform"])
    table.add_row("Version", __version__)

    console.print()
    console.print(table)
    console.print()


def _cmd_setup_impl(ctx: typer.Context, *, calibrate: bool) -> None:
    state = _state(ctx)
    if state.json_output:
        typer.echo(
            json.dumps(
                {
                    "error": "interactive_command",
                    "command": "setup" if not calibrate else "setup_calibrate",
                    "message": "Setup is interactive. Omit --json, or run in a terminal.",
                },
                indent=2,
            )
        )
        raise typer.Exit(2)
    code = run_calibrate_only() if calibrate else run_setup()
    if code != 0:
        raise typer.Exit(code)
    console = _console(state)
    if not state.json_output:
        console.print(f"[success]{SUMMARY_SETUP}[/success]")


def cmd_setup(ctx: typer.Context, calibrate: bool = typer.Option(False, "--calibrate", help="Calibration only")) -> None:
    """Configure watch directory and optional genre calibration."""
    _cmd_setup_impl(ctx, calibrate=calibrate)


def cmd_init(ctx: typer.Context, calibrate: bool = typer.Option(False, "--calibrate", help="Calibration only")) -> None:
    """Alias for [accent]setup[/accent] — first-time config and calibration."""
    _cmd_setup_impl(ctx, calibrate=calibrate)


def cmd_scan(
    ctx: typer.Context,
    path: Path = typer.Argument(..., help="Directory to scan recursively", exists=True, file_okay=False),
    no_features: bool = typer.Option(False, "--no-features", help="Tags + bitrate only (skip Spotify/librosa)."),
) -> None:
    """Write sidecar: tags + audio + optional Spotify/librosa (no MusicBrainz)."""
    state = _state(ctx)
    console = _console(state)
    root = path.expanduser().resolve()
    json_mode = state.json_output
    spin = not json_mode and should_use_color(no_color_flag=state.no_color)

    with _maybe_spinner(console, "Scanning audio…", active=spin):
        scan_tree(root, features=not no_features)

    from subgenre.sidecar import load_sidecar

    if json_mode:
        rows = []
        for p in iter_audio_files(root):
            rows.append({"path": str(p), **load_sidecar(p)})
        typer.echo(json.dumps(rows, indent=2, default=str))
        raise typer.Exit(0)

    console.print(Panel.fit(f"[success]{SUMMARY_SCAN}[/success] — [muted]{root}[/muted]", border_style="green"))
    for p in iter_audio_files(root):
        bundle = load_sidecar(p)
        console.print(f"[accent]{p}[/accent]\n{json.dumps(bundle, indent=2, default=str)}\n")
    console.print(f"[muted]{SUMMARY_DONE}.[/muted]")


def cmd_organize(
    ctx: typer.Context,
    source: Path = typer.Argument(..., help="Directory to read audio from", exists=True, file_okay=False),
    dest: Path = typer.Option(..., "--dest", help="Library root (genre folders created here)", path_type=Path),
    copy: bool = typer.Option(False, "--copy", help="Copy instead of move"),
    no_features: bool = typer.Option(False, "--no-features", help="Faster sidecar refresh without Spotify/librosa"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation when moving files (not --copy)."),
) -> None:
    """Refresh sidecars, then move or copy into dest / [Genre|Low Quality] / Artist - Title.ext"""
    state = _state(ctx)
    console = _console(state)
    src = source.expanduser().resolve()
    dst = dest.expanduser().resolve()
    json_mode = state.json_output

    n_files = len(iter_audio_files(src))
    if not copy and sys.stdin.isatty() and not yes:
        msg = ORGANIZE_CONFIRM.format(n=n_files, source=src, dest=dst)
        if not Confirm.ask(
            msg,
            default=False,
            console=console,
        ):
            console.print("[warning]Cancelled.[/warning]")
            raise typer.Exit(1)

    try:
        pairs = organize_tree(
            src,
            dst,
            copy=copy,
            with_features=not no_features,
        )
    except FileExistsError:
        console.print(f"[error]{ERR_ORGANIZE_DEST_EXISTS}[/error]")
        raise typer.Exit(1)

    action = "copy" if copy else "move"
    if json_mode:
        typer.echo(
            json.dumps(
                {
                    "ok": True,
                    "action": action,
                    "count": len(pairs),
                    "pairs": [{"from": str(a), "to": str(b)} for a, b in pairs],
                },
                indent=2,
            )
        )
        raise typer.Exit(0)

    table = Table(title=SUMMARY_ORGANIZE, show_header=True, header_style="accent")
    table.add_column("Action", style="info")
    table.add_column("From", overflow="fold")
    table.add_column("To", overflow="fold")
    verb = "Copied" if copy else "Moved"
    for s, d in pairs:
        table.add_row(verb, str(s), str(d))
    if not pairs:
        console.print(Panel.fit("[muted]No audio files to organize.[/muted]", border_style="dim"))
    else:
        console.print()
        console.print(table)
    console.print(f"[success]{SUMMARY_DONE}:[/success] [accent]{len(pairs)}[/accent] file(s).")


def cmd_enrich(
    ctx: typer.Context,
    path: Path = typer.Argument(..., help="Audio file or directory", exists=True),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show work only; no writes"),
) -> None:
    """Fill tags from MusicBrainz + art; optional Spotify + librosa; write sidecar."""
    state = _state(ctx)
    console = _console(state)
    root = path.expanduser().resolve()
    json_mode = state.json_output
    spin = not json_mode and should_use_color(no_color_flag=state.no_color)

    if root.is_file():
        with _maybe_spinner(console, "Enriching file…", active=spin):
            enrich_file(root, dry_run=dry_run)
        if json_mode:
            typer.echo(json.dumps({"path": str(root), "files": 1, "dry_run": dry_run}, indent=2))
            raise typer.Exit(0)
        console.print(Panel.fit(f"[success]{SUMMARY_ENRICH}[/success] — [accent]{root}[/accent]", border_style="green"))
        return

    with _maybe_spinner(console, "Enriching tree…", active=spin):
        enrich_tree(root, dry_run=dry_run)
    n = len(iter_audio_files(root))
    if json_mode:
        typer.echo(json.dumps({"path": str(root), "files": n, "dry_run": dry_run}, indent=2))
        raise typer.Exit(0)
    console.print(
        Panel.fit(
            f"[success]{SUMMARY_ENRICH}[/success] — [accent]{n}[/accent] file(s) under [accent]{root}[/accent].",
            border_style="green",
        )
    )


def cmd_watch(
    ctx: typer.Context,
    path: Path | None = typer.Argument(
        None,
        help="Directory to watch (default: directory from setup)",
        exists=True,
        file_okay=False,
    ),
    debounce: str = typer.Option("2.0", "--debounce", help="Seconds of quiet before processing"),
) -> None:
    """Watch a folder; new audio triggers scan after debounce."""
    state = _state(ctx)
    console = _console(state)
    if path is None:
        from subgenre.config_store import get_watch_dir

        wd = get_watch_dir()
        if not wd:
            console.print(f"[error]{ERR_NO_WATCH_DIR}[/error]")
            raise typer.Exit(1)
        watch_path = wd
    else:
        watch_path = path.expanduser().resolve()

    if not state.json_output:
        console.print(
            Panel.fit(
                f"[info]{SUMMARY_WATCH_START}[/info]\n[accent]{watch_path}[/accent]\n"
                + WATCH_DEBOUNCE_HINT.format(debounce=debounce),
                title="Watch",
                border_style="info",
            )
        )
    watch_folder(watch_path, debounce_s=float(debounce))


def _format_bytes(n: int) -> str:
    if n < 1024:
        return f"{n} B"
    if n < 1024**2:
        return f"{n / 1024:.1f} KB"
    if n < 1024**3:
        return f"{n / 1024**2:.1f} MB"
    return f"{n / 1024**3:.1f} GB"


def cmd_deploy(
    ctx: typer.Context,
    source: Path = typer.Argument(..., help="Library root to copy from", exists=True, file_okay=False),
    target: Path = typer.Argument(..., help="Destination root (created as needed)"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Plan only: no writes"),
    overwrite: bool = typer.Option(False, "--overwrite", help="Replace files that already exist at target"),
    skip_existing: bool = typer.Option(
        False,
        "--skip-existing",
        help="Skip source files when the target path already exists",
    ),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation before copying"),
) -> None:
    """Mirror the whole library tree to another path (backup, drive, staging)."""
    state = _state(ctx)
    console = _console(state)
    json_mode = state.json_output
    src = source.expanduser().resolve()
    tgt = target.expanduser().resolve()

    try:
        n_files = len(iter_files(src))
    except OSError as e:
        console.print(f"[error]Could not read source tree: {e}[/error]")
        raise typer.Exit(1)

    if not dry_run and n_files > 0 and sys.stdin.isatty() and not yes:
        msg = DEPLOY_CONFIRM.format(n=n_files, source=src, target=tgt)
        if not Confirm.ask(msg, default=False, console=console):
            console.print("[warning]Cancelled.[/warning]")
            raise typer.Exit(1)

    use_progress = (
        not json_mode
        and not dry_run
        and sys.stderr.isatty()
        and n_files > 0
    )
    result = None
    try:
        if use_progress:
            rich_progress = Progress(
                SpinnerColumn(),
                TextColumn("[bold]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                TimeElapsedColumn(),
                console=console,
                transient=False,
            )
            task_id: int | None = None

            def hook(idx: int, total: int, path: Path) -> None:
                nonlocal task_id
                if task_id is None:
                    task_id = rich_progress.add_task("Deploying…", total=total)
                rich_progress.update(task_id, completed=idx, description=str(path.name)[:52])

            with rich_progress:
                result = run_deploy(
                    src,
                    tgt,
                    dry_run=dry_run,
                    overwrite=overwrite,
                    skip_existing=skip_existing,
                    progress_hook=hook,
                )
        else:
            result = run_deploy(
                src,
                tgt,
                dry_run=dry_run,
                overwrite=overwrite,
                skip_existing=skip_existing,
                progress_hook=None,
            )
    except DeployFlagError:
        console.print(f"[error]{ERR_DEPLOY_FLAGS}[/error]")
        raise typer.Exit(1)
    except DeployError as e:
        console.print(f"[error]{e}[/error]")
        raise typer.Exit(1)

    assert result is not None
    ok = len(result.errors) == 0
    payload: dict[str, Any] = {
        "ok": ok,
        "dry_run": dry_run,
        "source": str(src),
        "target": str(tgt),
        "files_planned": result.files_planned,
        "copied": result.copied,
        "skipped": result.skipped,
        "bytes": result.bytes_copied,
        "errors": result.errors,
    }

    if json_mode:
        typer.echo(json.dumps(payload, indent=2))
        raise typer.Exit(0 if ok else 1)

    summary = Table(title=SUMMARY_DEPLOY, show_header=False, header_style="accent")
    summary.add_column("Key", style="info")
    summary.add_column("Value", overflow="fold")
    mode = "Dry run" if dry_run else "Copied"
    summary.add_row("Mode", mode)
    summary.add_row("Files (planned)", str(result.files_planned))
    summary.add_row("Files (transferred)" if not dry_run else "Files (would copy)", str(result.copied))
    if result.skipped:
        summary.add_row("Skipped", str(result.skipped))
    summary.add_row("Data", _format_bytes(result.bytes_copied))
    if result.errors:
        summary.add_row("Path issues", str(len(result.errors)))

    console.print()
    console.print(Panel(summary, border_style="green" if ok else "yellow"))
    if result.errors:
        console.print("[warning]Some paths were skipped (unsafe relative path).[/warning]")
    console.print(f"[success]{SUMMARY_DONE}.[/success]" if ok else "[warning]Finished with issues.[/warning]")
    if not ok:
        raise typer.Exit(1)


def cmd_inspect(
    ctx: typer.Context,
    path: Path = typer.Argument(..., help="Directory to scan", exists=True, file_okay=False),
) -> None:
    """Print embedded tags only (does not write sidecars)."""
    state = _state(ctx)
    console = _console(state)
    root = path.expanduser().resolve()
    rows: list[dict[str, Any]] = []
    for p in iter_audio_files(root):
        tags = read_tags_full(p)
        rows.append({"path": str(p), **tags})

    if state.json_output:
        typer.echo(json.dumps(rows, indent=2))
        raise typer.Exit(0)

    table = Table(title="Embedded tags", show_header=True, header_style="accent")
    table.add_column("File", overflow="fold", style="accent")
    table.add_column("Tags", overflow="fold")
    for r in rows:
        tag_view = {k: r[k] for k in r if k != "path"}
        table.add_row(str(r["path"]), str(tag_view))
    console.print()
    console.print(table)
    console.print(f"[muted]{len(rows)} file(s).[/muted]")


# Register commands (explicit names + init alias)
app.command("status")(cmd_status)
app.command("setup")(cmd_setup)
app.command("init")(cmd_init)
app.command("scan")(cmd_scan)
app.command("organize")(cmd_organize)
app.command("enrich")(cmd_enrich)
app.command("watch")(cmd_watch)
app.command("deploy")(cmd_deploy)
app.command("inspect")(cmd_inspect)


def main(argv: list[str] | None = None) -> int:
    """Entry point for setuptools and tests."""
    changed = False
    old_argv: list[str] | None = None
    if argv is not None:
        old_argv = sys.argv[:]
        sys.argv = ["subgenre", *argv]
        changed = True
    try:
        app()
        return 0
    except SystemExit as e:
        code = e.code
        if code is None:
            return 0
        if isinstance(code, int):
            return code
        return 1
    except KeyboardInterrupt:
        c = make_console(no_color=bool(os.environ.get("NO_COLOR")))
        c.print(f"[warning]{ERR_INTERRUPTED}[/warning]")
        return 130
    finally:
        if changed and old_argv is not None:
            sys.argv = old_argv


if __name__ == "__main__":
    raise SystemExit(main())
