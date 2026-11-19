"""Functional tests for the `pod` CLI (Click) — happy paths, exit codes, errors."""

import importlib.machinery
import importlib.util
import sqlite3
from pathlib import Path

import pytest
from click.testing import CliRunner

from db import database, migrate
import tunnel

POD_PATH = Path(__file__).resolve().parent.parent / "pod"


def _load_pod_module():
    """The CLI lives in the extensionless `pod` file — load it explicitly."""
    loader = importlib.machinery.SourceFileLoader("pod_cli", str(POD_PATH))
    spec = importlib.util.spec_from_loader("pod_cli", loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


pod_cli = _load_pod_module()


@pytest.fixture
def runner(tmp_path, monkeypatch) -> CliRunner:
    db_path = tmp_path / "pods.db"
    monkeypatch.setattr(database, "DB_PATH", db_path)
    # keep `status`/`restore` hermetic: no real PID file, no tunnel probing
    monkeypatch.setattr(pod_cli, "PID_FILE", tmp_path / "pod.pid")
    monkeypatch.setattr(tunnel, "get_tunnel_url", lambda: None)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    migrate.run(connection=conn)
    conn.close()
    return CliRunner()


def invoke(runner, args):
    result = runner.invoke(pod_cli.cli, args)
    assert result.exit_code == 0, f"{args} failed: {result.output} {result.exception}"
    return result


# --- happy path per command -------------------------------------------------


def test_migrate(runner):
    result = invoke(runner, ["migrate"])
    assert "Schema up to date." in result.output


def test_backup(runner, tmp_path):
    result = invoke(runner, ["backup", "--path", "backups"])
    assert "Backup completed:" in result.output
    assert list((tmp_path / "backups").glob("pods-*.db"))


def test_restore(runner, tmp_path):
    invoke(runner, ["backup", "--path", "backups"])
    backup_file = list((tmp_path / "backups").glob("pods-*.db"))[0]

    result = invoke(runner, ["restore", "--path", str(backup_file)])
    assert "Restore completed" in result.output


def test_completion(runner, monkeypatch):
    monkeypatch.setenv("SHELL", "/usr/bin/zsh")
    result = invoke(runner, ["completion"])
    assert "zshrc" in result.output


def test_status(runner):
    result = invoke(runner, ["status"])
    assert "Server:" in result.output


def test_doctor(runner):
    result = invoke(runner, ["doctor"])
    # exit 0 either way — doctor reports issues instead of failing
    assert "All checks passed!" in result.output or "Issues found:" in result.output


def test_server_stop_without_server(runner):
    result = invoke(runner, ["server", "stop"])
    assert "No server is running." in result.output


def test_version(runner):
    result = invoke(runner, ["--version"])
    assert "pod, version" in result.output


# --- error cases ------------------------------------------------------------


def test_unknown_command_exits_2(runner):
    result = runner.invoke(pod_cli.cli, ["bogus"])
    assert result.exit_code == 2


def test_restore_missing_file_exits_2(runner, tmp_path):
    result = runner.invoke(
        pod_cli.cli, ["restore", "--path", str(tmp_path / "does-not-exist.db")]
    )
    assert result.exit_code == 2
    assert "Invalid value" in result.output
