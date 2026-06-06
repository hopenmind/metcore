"""Registry of known MCP client configurations.

Each entry describes how to write the Hope 'n Mind MCP server entry into
a popular MCP client's config file. The registry is data-driven so new
clients can be added without touching the configure flow.

Two config schemas exist in the wild:
  * ``mcpServers`` dict — Claude Desktop, Claude Code, Cursor, OpenCode,
    Gemini CLI, Windsurf, Cline.
  * ``servers`` dict with a typed entry — VS Code / GitHub Copilot.

A client is considered installed if ANY of its candidate presence paths
exists. This avoids false negatives when a client stores data under more
than one convention (e.g. Cursor ships both ``~/.cursor/`` and
``%APPDATA%/Cursor/``; Windsurf uses ``.codeium/`` on Linux but
``%APPDATA%/Windsurf/`` on Windows in recent versions).

SPDX-License-Identifier: Apache-2.0 OR LicenseRef-HopenMind-Commercial
"""

from __future__ import annotations

import glob
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable


# ──────────────────────────────────────────────────────────────────────────────
#  Path helpers — per-OS conventions
# ──────────────────────────────────────────────────────────────────────────────

def _home() -> Path:
    return Path.home()


def _appdata() -> Path:
    """Windows %APPDATA% (falls back to ~/.config on non-Windows)."""
    v = os.environ.get("APPDATA")
    if v:
        return Path(v)
    return _home() / ".config"


def _localappdata() -> Path:
    """Windows %LOCALAPPDATA% (falls back to ~/.local/share elsewhere)."""
    v = os.environ.get("LOCALAPPDATA")
    if v:
        return Path(v)
    return _home() / ".local" / "share"


# ── Config-file path getters (where we write) ────────────────────────────────

def _claude_desktop_path() -> Path:
    if sys.platform == "darwin":
        return _home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
    if sys.platform == "win32":
        return _appdata() / "Claude" / "claude_desktop_config.json"
    return _home() / ".config" / "Claude" / "claude_desktop_config.json"


def _claude_code_path() -> Path:
    return _home() / ".claude.json"


def _cursor_global_path() -> Path:
    return _home() / ".cursor" / "mcp.json"


def _vscode_user_path() -> Path:
    if sys.platform == "darwin":
        return _home() / "Library" / "Application Support" / "Code" / "User" / "mcp.json"
    if sys.platform == "win32":
        return _appdata() / "Code" / "User" / "mcp.json"
    return _home() / ".config" / "Code" / "User" / "mcp.json"


def _gemini_cli_path() -> Path:
    return _home() / ".gemini" / "settings.json"


def _opencode_path() -> Path:
    return _home() / ".opencode" / "opencode.json"


def _windsurf_path() -> Path:
    if sys.platform == "win32":
        return _appdata() / "Windsurf" / "User" / "mcp_config.json"
    if sys.platform == "darwin":
        return _home() / "Library" / "Application Support" / "Windsurf" / "User" / "mcp_config.json"
    return _home() / ".codeium" / "windsurf" / "mcp_config.json"


def _cline_path() -> Path:
    if sys.platform == "win32":
        return _appdata() / "Code" / "User" / "globalStorage" / "saoudrizwan.claude-dev" / "settings" / "cline_mcp_settings.json"
    if sys.platform == "darwin":
        return _home() / "Library" / "Application Support" / "Code" / "User" / "globalStorage" / "saoudrizwan.claude-dev" / "settings" / "cline_mcp_settings.json"
    return _home() / ".config" / "Code" / "User" / "globalStorage" / "saoudrizwan.claude-dev" / "settings" / "cline_mcp_settings.json"


def _continue_path() -> Path:
    """Continue.dev stores config in ``~/.continue/config.yaml`` (new) or
    ``~/.continue/config.json`` (legacy). We write to config.json since it
    is still honoured and unambiguous to merge JSON into."""
    return _home() / ".continue" / "config.json"


def _zed_path() -> Path:
    """Zed stores MCP context servers in its settings.json."""
    if sys.platform == "darwin":
        return _home() / "Library" / "Application Support" / "Zed" / "settings.json"
    if sys.platform == "win32":
        return _appdata() / "Zed" / "settings.json"
    return _home() / ".config" / "zed" / "settings.json"


def _cherry_studio_path() -> Path:
    """Cherry Studio (Electron app) per-OS user-data folder."""
    if sys.platform == "darwin":
        return _home() / "Library" / "Application Support" / "CherryStudio" / "mcp.json"
    if sys.platform == "win32":
        return _appdata() / "CherryStudio" / "mcp.json"
    return _home() / ".config" / "CherryStudio" / "mcp.json"


def _fivire_path() -> Path:
    """5ire (MCP-first desktop client) config."""
    if sys.platform == "darwin":
        return _home() / "Library" / "Application Support" / "5ire" / "mcp.json"
    if sys.platform == "win32":
        return _appdata() / "5ire" / "mcp.json"
    return _home() / ".config" / "5ire" / "mcp.json"


def _roo_cline_path() -> Path:
    """Roo Cline — the actively-maintained fork of Cline."""
    base = {
        "win32":  _appdata() / "Code" / "User" / "globalStorage",
        "darwin": _home() / "Library" / "Application Support" / "Code" / "User" / "globalStorage",
    }.get(sys.platform, _home() / ".config" / "Code" / "User" / "globalStorage")
    return base / "rooveterinaryinc.roo-cline" / "settings" / "cline_mcp_settings.json"


# ── Presence path providers (where we check for install) ─────────────────────
# Each returns a list of candidate paths; the client counts as installed if
# any exists. Glob patterns are honoured.

def _cursor_presence() -> list[Path]:
    paths = [
        _home() / ".cursor",
        _cursor_global_path().parent,
    ]
    if sys.platform == "win32":
        paths += [
            _localappdata() / "Programs" / "cursor",
            _localappdata() / "Programs" / "Cursor",
            _appdata() / "Cursor",
        ]
    elif sys.platform == "darwin":
        paths += [Path("/Applications/Cursor.app")]
    else:
        paths += [_home() / ".config" / "Cursor"]
    return paths


def _windsurf_presence() -> list[Path]:
    paths = [_windsurf_path().parent]
    if sys.platform == "win32":
        paths += [
            _localappdata() / "Programs" / "Windsurf",
            _appdata() / "Windsurf",
            _home() / ".codeium",
        ]
    elif sys.platform == "darwin":
        paths += [Path("/Applications/Windsurf.app")]
    else:
        paths += [_home() / ".codeium" / "windsurf"]
    return paths


def _cline_presence() -> list[Path]:
    paths = [_cline_path().parent]
    vscode_ext_globs = [
        str(_home() / ".vscode" / "extensions" / "saoudrizwan.claude-dev-*"),
        str(_home() / ".vscode-insiders" / "extensions" / "saoudrizwan.claude-dev-*"),
        str(_home() / ".cursor" / "extensions" / "saoudrizwan.claude-dev-*"),
    ]
    hits = []
    for g in vscode_ext_globs:
        hits += [Path(p) for p in glob.glob(g)]
    return paths + hits


def _claude_desktop_presence() -> list[Path]:
    paths = [_claude_desktop_path().parent]
    if sys.platform == "win32":
        paths += [_localappdata() / "AnthropicClaude", _localappdata() / "Programs" / "Claude"]
    elif sys.platform == "darwin":
        paths += [Path("/Applications/Claude.app")]
    return paths


def _claude_code_presence() -> list[Path]:
    return [_claude_code_path(), _home() / ".claude"]


def _vscode_presence() -> list[Path]:
    paths = [_vscode_user_path().parent]
    if sys.platform == "win32":
        paths += [
            _localappdata() / "Programs" / "Microsoft VS Code",
            _appdata() / "Code",
        ]
    elif sys.platform == "darwin":
        paths += [Path("/Applications/Visual Studio Code.app")]
    else:
        paths += [Path("/usr/share/code"), Path("/snap/code/current")]
    return paths


def _gemini_cli_presence() -> list[Path]:
    return [_gemini_cli_path().parent, _home() / ".gemini"]


def _opencode_presence() -> list[Path]:
    return [_opencode_path().parent, _home() / ".opencode"]


def _continue_presence() -> list[Path]:
    paths = [_continue_path().parent, _home() / ".continue"]
    # Continue ships as extensions in VS Code / JetBrains; surface both.
    paths += [Path(p) for p in glob.glob(str(_home() / ".vscode" / "extensions" / "continue.continue-*"))]
    return paths


def _zed_presence() -> list[Path]:
    paths = [_zed_path().parent]
    if sys.platform == "darwin":
        paths += [Path("/Applications/Zed.app"), Path("/Applications/Zed Preview.app")]
    elif sys.platform == "win32":
        paths += [_localappdata() / "Programs" / "Zed"]
    else:
        paths += [Path("/usr/bin/zed"), _home() / ".local" / "share" / "zed"]
    return paths


def _cherry_studio_presence() -> list[Path]:
    paths = [_cherry_studio_path().parent]
    if sys.platform == "darwin":
        paths += [Path("/Applications/Cherry Studio.app")]
    elif sys.platform == "win32":
        paths += [_localappdata() / "Programs" / "Cherry Studio", _appdata() / "CherryStudio"]
    return paths


def _fivire_presence() -> list[Path]:
    paths = [_fivire_path().parent]
    if sys.platform == "darwin":
        paths += [Path("/Applications/5ire.app")]
    elif sys.platform == "win32":
        paths += [_localappdata() / "Programs" / "5ire", _appdata() / "5ire"]
    return paths


def _roo_cline_presence() -> list[Path]:
    paths = [_roo_cline_path().parent]
    paths += [Path(p) for p in glob.glob(str(_home() / ".vscode" / "extensions" / "rooveterinaryinc.roo-cline-*"))]
    paths += [Path(p) for p in glob.glob(str(_home() / ".vscode" / "extensions" / "rooveterinaryinc.roo-code-*"))]
    return paths


# ──────────────────────────────────────────────────────────────────────────────
#  Registry
# ──────────────────────────────────────────────────────────────────────────────

SCHEMA_MCPSERVERS = "mcpServers"
SCHEMA_SERVERS_TYPED = "servers_typed"


@dataclass(frozen=True)
class MCPClient:
    """Descriptor for a single MCP client."""

    slug: str
    display_name: str
    config_path: Callable[[], Path]
    schema: str
    docs_url: str
    presence_paths: Callable[[], list[Path]] = field(default=None)  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.presence_paths is None:
            # Default: only look at the config file's parent dir.
            object.__setattr__(
                self,
                "presence_paths",
                lambda: [self.config_path().parent],
            )

    def is_installed(self) -> bool:
        for p in self.presence_paths():
            if p.exists():
                return True
        return False

    def describe(self) -> str:
        return f"{self.display_name} ({self.slug}) → {self.config_path()}"


CLIENTS: list[MCPClient] = [
    MCPClient(
        slug="claude-desktop",
        display_name="Claude Desktop",
        config_path=_claude_desktop_path,
        schema=SCHEMA_MCPSERVERS,
        docs_url="https://modelcontextprotocol.io/quickstart/user",
        presence_paths=_claude_desktop_presence,
    ),
    MCPClient(
        slug="claude-code",
        display_name="Claude Code (CLI)",
        config_path=_claude_code_path,
        schema=SCHEMA_MCPSERVERS,
        docs_url="https://docs.claude.com/en/docs/claude-code/mcp",
        presence_paths=_claude_code_presence,
    ),
    MCPClient(
        slug="cursor",
        display_name="Cursor",
        config_path=_cursor_global_path,
        schema=SCHEMA_MCPSERVERS,
        docs_url="https://docs.cursor.com/context/mcp",
        presence_paths=_cursor_presence,
    ),
    MCPClient(
        slug="vscode",
        display_name="VS Code / GitHub Copilot",
        config_path=_vscode_user_path,
        schema=SCHEMA_SERVERS_TYPED,
        docs_url="https://code.visualstudio.com/docs/copilot/copilot-mcp",
        presence_paths=_vscode_presence,
    ),
    MCPClient(
        slug="gemini-cli",
        display_name="Gemini CLI",
        config_path=_gemini_cli_path,
        schema=SCHEMA_MCPSERVERS,
        docs_url="https://github.com/google-gemini/gemini-cli",
        presence_paths=_gemini_cli_presence,
    ),
    MCPClient(
        slug="opencode",
        display_name="OpenCode",
        config_path=_opencode_path,
        schema=SCHEMA_MCPSERVERS,
        docs_url="https://opencode.ai",
        presence_paths=_opencode_presence,
    ),
    MCPClient(
        slug="windsurf",
        display_name="Windsurf (Codeium)",
        config_path=_windsurf_path,
        schema=SCHEMA_MCPSERVERS,
        docs_url="https://docs.codeium.com/windsurf/mcp",
        presence_paths=_windsurf_presence,
    ),
    MCPClient(
        slug="cline",
        display_name="Cline (VS Code extension)",
        config_path=_cline_path,
        schema=SCHEMA_MCPSERVERS,
        docs_url="https://docs.cline.bot/mcp",
        presence_paths=_cline_presence,
    ),
    MCPClient(
        slug="roo-cline",
        display_name="Roo Cline (VS Code extension)",
        config_path=_roo_cline_path,
        schema=SCHEMA_MCPSERVERS,
        docs_url="https://github.com/RooVetGit/Roo-Cline",
        presence_paths=_roo_cline_presence,
    ),
    MCPClient(
        slug="continue",
        display_name="Continue.dev",
        config_path=_continue_path,
        schema=SCHEMA_MCPSERVERS,
        docs_url="https://docs.continue.dev/customize/deep-dives/mcp",
        presence_paths=_continue_presence,
    ),
    MCPClient(
        slug="zed",
        display_name="Zed",
        config_path=_zed_path,
        schema=SCHEMA_MCPSERVERS,
        docs_url="https://zed.dev/docs/ai/mcp",
        presence_paths=_zed_presence,
    ),
    MCPClient(
        slug="cherry-studio",
        display_name="Cherry Studio",
        config_path=_cherry_studio_path,
        schema=SCHEMA_MCPSERVERS,
        docs_url="https://cherry-ai.com/docs/mcp",
        presence_paths=_cherry_studio_presence,
    ),
    MCPClient(
        slug="5ire",
        display_name="5ire",
        config_path=_fivire_path,
        schema=SCHEMA_MCPSERVERS,
        docs_url="https://5ire.app",
        presence_paths=_fivire_presence,
    ),
]


def get_client(slug: str) -> MCPClient:
    for c in CLIENTS:
        if c.slug == slug:
            return c
    raise KeyError(f"Unknown MCP client slug: {slug!r}. Known: {[c.slug for c in CLIENTS]}")


def detect_installed() -> list[MCPClient]:
    return [c for c in CLIENTS if c.is_installed()]
