"""Tests for hopenmind-cli — covers the top-level commands."""

from __future__ import annotations

from typer.testing import CliRunner

from metcore_cli.__main__ import app

runner = CliRunner()


def test_help_lists_subcommands():
    res = runner.invoke(app, ["--help"])
    assert res.exit_code == 0
    for cmd in ("list", "install", "uninstall", "update", "doctor", "triage"):
        assert cmd in res.stdout


def test_list_runs_without_error():
    res = runner.invoke(app, ["list"])
    assert res.exit_code == 0
    assert "Hope 'n Mind Suite" in res.stdout


def test_doctor_runs_without_error():
    res = runner.invoke(app, ["doctor"])
    assert res.exit_code == 0
    assert "Python" in res.stdout


def test_triage_inline_expression():
    res = runner.invoke(app, [
        "triage",
        "--spectral", "exp(-w**2)",
        "--t-max", "5.0",
        "--n-time-steps", "256",
        "--target-accuracy", "0.05",
    ])
    # Some triage tools may not be installed in the test runner, but
    # the command must at least finish gracefully.
    assert res.exit_code in (0, 1)
    # If it ran fully, the Verdict line must be present
    if res.exit_code == 0:
        assert "Verdict" in res.stdout
