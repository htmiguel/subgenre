from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from subgenre.cli import app, main

runner = CliRunner()


def test_version_exits_zero() -> None:
    r = runner.invoke(app, ["--version"])
    assert r.exit_code == 0
    assert "subgenre" in r.stdout


def test_help_lists_commands() -> None:
    r = runner.invoke(app, ["--help"])
    assert r.exit_code == 0
    for name in ("scan", "organize", "status", "setup", "init", "deploy"):
        assert name in r.stdout


def test_no_subcommand_shows_help() -> None:
    r = runner.invoke(app, [])
    assert r.exit_code == 0
    out = r.stdout + (r.stderr or "")
    assert "scan" in out


def test_status_json_valid() -> None:
    r = runner.invoke(app, ["--json", "status"])
    assert r.exit_code == 0
    data = json.loads(r.stdout)
    assert "version" in data
    assert "config_path" in data


def test_status_no_color_no_escapes() -> None:
    r = runner.invoke(app, ["--no-color", "status"])
    assert r.exit_code == 0
    assert "\x1b[" not in r.stdout


def test_scan_json_empty_dir(tmp_path: Path) -> None:
    r = runner.invoke(app, ["--json", "scan", str(tmp_path)])
    assert r.exit_code == 0
    data = json.loads(r.stdout)
    assert data == []


def test_inspect_json_empty_dir(tmp_path: Path) -> None:
    r = runner.invoke(app, ["--json", "inspect", str(tmp_path)])
    assert r.exit_code == 0
    assert json.loads(r.stdout) == []


def test_setup_json_rejects_interactive() -> None:
    r = runner.invoke(app, ["--json", "setup"])
    assert r.exit_code == 2
    assert json.loads(r.stdout)["error"] == "interactive_command"


def test_main_argv_passthrough_version() -> None:
    assert main(["--version"]) == 0


def test_deploy_dry_run_json(tmp_path: Path) -> None:
    src = tmp_path / "src"
    src.mkdir()
    (src / "a.txt").write_text("hi", encoding="utf-8")
    tgt = tmp_path / "tgt"
    r = runner.invoke(app, ["--json", "deploy", str(src), str(tgt), "--dry-run"])
    assert r.exit_code == 0
    data = json.loads(r.stdout)
    assert data["ok"] is True
    assert data["dry_run"] is True
    assert data["copied"] == 1
    assert data["files_planned"] == 1


def test_deploy_copies_with_yes(tmp_path: Path) -> None:
    src = tmp_path / "src"
    src.mkdir()
    (src / "track.flac").write_bytes(b"fake")
    tgt = tmp_path / "tgt"
    r = runner.invoke(app, ["deploy", str(src), str(tgt), "--yes"])
    assert r.exit_code == 0
    assert (tgt / "track.flac").read_bytes() == b"fake"


def test_deploy_conflict_exits_one(tmp_path: Path) -> None:
    src = tmp_path / "src"
    src.mkdir()
    (src / "x.txt").write_text("a", encoding="utf-8")
    tgt = tmp_path / "tgt"
    tgt.mkdir()
    (tgt / "x.txt").write_text("b", encoding="utf-8")
    r = runner.invoke(app, ["deploy", str(src), str(tgt), "--yes"])
    assert r.exit_code == 1


def test_deploy_both_flags_exits_one(tmp_path: Path) -> None:
    src = tmp_path / "s"
    src.mkdir()
    tgt = tmp_path / "t"
    r = runner.invoke(app, ["deploy", str(src), str(tgt), "--yes", "--overwrite", "--skip-existing"])
    assert r.exit_code == 1


def test_copy_improvement_comment_in_module() -> None:
    """Guardrail: copy module documents before/after messaging rationale."""
    from subgenre import copy as copy_mod

    src = Path(copy_mod.__file__).read_text(encoding="utf-8")
    assert "before" in src.lower() and "after" in src.lower()
