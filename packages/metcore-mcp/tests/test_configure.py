"""Tests for the ``hopenmind-mcp configure`` flow.

The tests redirect the client ``config_path`` callables to temporary
files so no real user config is touched.

SPDX-License-Identifier: Apache-2.0 OR LicenseRef-HopenMind-Commercial
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from metcore_mcp import clients as clients_mod
from metcore_mcp import configure


# ──────────────────────────────────────────────────────────────────────────────
#  Helpers
# ──────────────────────────────────────────────────────────────────────────────

def _fake_client(tmp_path: Path, slug: str, schema: str,
                 display: str = "Fake Client") -> clients_mod.MCPClient:
    cfg = tmp_path / f"{slug}.json"
    return clients_mod.MCPClient(
        slug=slug,
        display_name=display,
        config_path=lambda: cfg,
        schema=schema,
        docs_url="https://example.invalid",
    )


# ──────────────────────────────────────────────────────────────────────────────
#  Registry sanity
# ──────────────────────────────────────────────────────────────────────────────

def test_registry_slugs_unique():
    slugs = [c.slug for c in clients_mod.CLIENTS]
    assert len(slugs) == len(set(slugs)), f"duplicate slugs: {slugs}"


def test_registry_paths_resolve():
    for c in clients_mod.CLIENTS:
        p = c.config_path()
        assert isinstance(p, Path)


def test_get_client_known():
    c = clients_mod.get_client("claude-desktop")
    assert c.display_name == "Claude Desktop"


def test_get_client_unknown():
    with pytest.raises(KeyError):
        clients_mod.get_client("not-a-client")


# ──────────────────────────────────────────────────────────────────────────────
#  apply() — creation / update / idempotence / backup
# ──────────────────────────────────────────────────────────────────────────────

def test_apply_creates_fresh_config_mcpservers(tmp_path):
    c = _fake_client(tmp_path, "fresh", clients_mod.SCHEMA_MCPSERVERS)
    r = configure.apply(c)
    assert r.action == "created"
    assert r.backup is None
    data = json.loads(c.config_path().read_text(encoding="utf-8"))
    assert data == {"mcpServers": {"metcore": {"command": "metcore-mcp", "args": []}}}


def test_apply_creates_fresh_config_servers_typed(tmp_path):
    c = _fake_client(tmp_path, "vscode-like", clients_mod.SCHEMA_SERVERS_TYPED)
    r = configure.apply(c)
    assert r.action == "created"
    data = json.loads(c.config_path().read_text(encoding="utf-8"))
    assert data == {"servers": {"metcore": {"type": "stdio", "command": "metcore-mcp", "args": []}}}


def test_apply_preserves_existing_keys(tmp_path):
    c = _fake_client(tmp_path, "existing", clients_mod.SCHEMA_MCPSERVERS)
    c.config_path().parent.mkdir(parents=True, exist_ok=True)
    c.config_path().write_text(json.dumps({
        "theme": "dark",
        "mcpServers": {"other-tool": {"command": "other"}},
    }), encoding="utf-8")

    r = configure.apply(c)
    # Either 'created' (no prior hopenmind entry) or 'updated' (different prior
    # entry) is acceptable — what matters is the file was written and other
    # keys were preserved.
    assert r.action in ("created", "updated")
    assert r.backup is not None
    assert r.backup.exists()

    data = json.loads(c.config_path().read_text(encoding="utf-8"))
    assert data["theme"] == "dark"
    assert data["mcpServers"]["other-tool"] == {"command": "other"}
    assert data["mcpServers"]["metcore"]["command"] == "metcore-mcp"


def test_apply_idempotent(tmp_path):
    c = _fake_client(tmp_path, "idem", clients_mod.SCHEMA_MCPSERVERS)
    configure.apply(c)
    r = configure.apply(c)
    assert r.action == "already-configured"
    assert r.backup is None


def test_apply_dry_run_does_not_write(tmp_path):
    c = _fake_client(tmp_path, "dryrun", clients_mod.SCHEMA_MCPSERVERS)
    r = configure.apply(c, dry_run=True)
    assert r.action == "dry-run"
    assert not c.config_path().exists()


def test_apply_rejects_invalid_json(tmp_path):
    c = _fake_client(tmp_path, "broken", clients_mod.SCHEMA_MCPSERVERS)
    c.config_path().parent.mkdir(parents=True, exist_ok=True)
    c.config_path().write_text("{not-json", encoding="utf-8")
    with pytest.raises(RuntimeError, match="valid JSON"):
        configure.apply(c)


# ──────────────────────────────────────────────────────────────────────────────
#  list_clients smoke test
# ──────────────────────────────────────────────────────────────────────────────

def test_list_clients_runs(capsys):
    rc = configure.list_clients()
    assert rc == 0
    captured = capsys.readouterr()
    assert "Known MCP clients" in captured.out
    for c in clients_mod.CLIENTS:
        assert c.slug in captured.out
