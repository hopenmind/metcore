"""Zero-friction configuration of MCP clients.

Writes the Hope 'n Mind MCP server entry into the config files of
popular MCP clients (Claude Desktop, Claude Code, Cursor, VS Code,
Gemini CLI, OpenCode, Windsurf, Cline).

Features:
  * Detects which clients appear installed on the current machine.
  * Interactive menu (when TTY) or flag-driven non-interactive mode.
  * Idempotent: re-running the command does not duplicate entries.
  * Backs up the existing config file before any write (``.bak``).
  * Dry-run mode shows the planned diff without touching the filesystem.

SPDX-License-Identifier: Apache-2.0 OR LicenseRef-HopenMind-Commercial
"""

from __future__ import annotations

import json
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from metcore_mcp.clients import (
    CLIENTS,
    SCHEMA_MCPSERVERS,
    SCHEMA_SERVERS_TYPED,
    MCPClient,
    detect_installed,
    get_client,
)

SERVER_KEY = "metcore"           # the name users will see in their client
SERVER_COMMAND = "metcore-mcp"   # the executable installed by this package


# ──────────────────────────────────────────────────────────────────────────────
#  Server entry builders — one per schema
# ──────────────────────────────────────────────────────────────────────────────

def _build_entry(schema: str, command: str = SERVER_COMMAND,
                 args: list[str] | None = None) -> dict:
    args = args or []
    if schema == SCHEMA_MCPSERVERS:
        return {"command": command, "args": args}
    if schema == SCHEMA_SERVERS_TYPED:
        return {"type": "stdio", "command": command, "args": args}
    raise ValueError(f"Unknown schema: {schema!r}")


def _container_key(schema: str) -> str:
    if schema == SCHEMA_MCPSERVERS:
        return "mcpServers"
    if schema == SCHEMA_SERVERS_TYPED:
        return "servers"
    raise ValueError(f"Unknown schema: {schema!r}")


# ──────────────────────────────────────────────────────────────────────────────
#  Core write logic
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class WriteResult:
    client: MCPClient
    path: Path
    action: str     # "created" | "updated" | "already-configured" | "dry-run"
    backup: Path | None


def _load_or_empty(path: Path) -> dict:
    if not path.exists() or path.stat().st_size == 0:
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise RuntimeError(
            f"Config file at {path} is not valid JSON: {e}. "
            f"Please fix it (or move it aside) before re-running the configurator."
        )


def apply(client: MCPClient, *, dry_run: bool = False,
          server_name: str = SERVER_KEY,
          command: str = SERVER_COMMAND,
          args: list[str] | None = None) -> WriteResult:
    path = client.config_path()
    container = _container_key(client.schema)
    desired = _build_entry(client.schema, command=command, args=args)

    doc = _load_or_empty(path)
    existing_section = doc.get(container, {}) if isinstance(doc, dict) else {}
    existing_entry = existing_section.get(server_name) if isinstance(existing_section, dict) else None

    if existing_entry == desired:
        return WriteResult(client=client, path=path,
                           action="already-configured", backup=None)

    if dry_run:
        return WriteResult(client=client, path=path, action="dry-run", backup=None)

    # Persist — create parent dir, take a backup if the file exists.
    path.parent.mkdir(parents=True, exist_ok=True)
    backup: Path | None = None
    if path.exists():
        backup = path.with_suffix(path.suffix + ".bak")
        shutil.copy2(path, backup)

    section = dict(existing_section) if isinstance(existing_section, dict) else {}
    section[server_name] = desired
    new_doc = dict(doc) if isinstance(doc, dict) else {}
    new_doc[container] = section

    path.write_text(
        json.dumps(new_doc, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    action = "updated" if existing_entry is not None else "created"
    return WriteResult(client=client, path=path, action=action, backup=backup)


# ──────────────────────────────────────────────────────────────────────────────
#  Interactive flow
# ──────────────────────────────────────────────────────────────────────────────

def _available_slugs() -> list[str]:
    return [c.slug for c in CLIENTS]


def _resolve_client_selection(selection: Iterable[str] | None,
                              all_clients: bool,
                              interactive: bool) -> list[MCPClient]:
    if all_clients:
        return list(CLIENTS)

    if selection:
        return [get_client(s.strip()) for s in selection if s.strip()]

    # No explicit selection: detect + prompt (if TTY).
    detected = detect_installed()
    if not detected:
        print(
            "No MCP client config directory detected on this machine. "
            "Pass --clients <slug1,slug2,...> to force, or --all. "
            f"Known slugs: {_available_slugs()}",
            file=sys.stderr,
        )
        return []

    if not interactive or not sys.stdin.isatty():
        return detected

    # Tiny line-prompt (no hard dependency on questionary for adoption).
    print("Detected MCP clients:")
    for i, c in enumerate(detected, 1):
        print(f"  [{i}] {c.describe()}")
    print("")
    print("Press Enter to configure ALL detected, or type a comma-separated "
          "list of numbers (e.g. '1,3').")
    raw = input("> ").strip()
    if not raw:
        return detected
    try:
        picks = [int(x) - 1 for x in raw.split(",")]
        return [detected[i] for i in picks if 0 <= i < len(detected)]
    except ValueError:
        print("Could not parse selection — aborting.", file=sys.stderr)
        return []


def run(selection: Iterable[str] | None = None,
        *,
        all_clients: bool = False,
        dry_run: bool = False,
        interactive: bool = True) -> int:
    targets = _resolve_client_selection(selection, all_clients, interactive)
    if not targets:
        return 1

    print(f"Configuring `{SERVER_KEY}` ({SERVER_COMMAND}) in "
          f"{len(targets)} client(s)"
          f"{' — DRY RUN, no changes written' if dry_run else ''}:")
    print()

    errors = 0
    for c in targets:
        try:
            r = apply(c, dry_run=dry_run)
            suffix = f"  ← backup: {r.backup}" if r.backup else ""
            print(f"  [{r.action:<17}] {c.display_name:<28} → {r.path}{suffix}")
        except Exception as exc:  # noqa: BLE001
            errors += 1
            print(f"  [ERROR            ] {c.display_name:<28} → {exc}",
                  file=sys.stderr)

    print()
    if errors:
        print(f"Done with {errors} error(s). See messages above.",
              file=sys.stderr)
        return 2
    print("Done. Restart your MCP client if it was running to pick up the change.")
    return 0


def list_clients() -> int:
    detected_slugs = {c.slug for c in detect_installed()}
    print("Known MCP clients (★ = detected on this machine):")
    for c in CLIENTS:
        mark = "★" if c.slug in detected_slugs else " "
        print(f"  {mark} {c.slug:<16} {c.display_name:<28} → {c.config_path()}")
    return 0
