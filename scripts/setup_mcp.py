#!/usr/bin/env python3
"""
Guided installer for the Hope 'n Mind MCP server.

A short questionnaire that wires the `hopenmind` MCP server into your client
(Claude Desktop, Claude Code, Cursor, VS Code, Windsurf, Cline, and others) so
you do not have to edit JSON by hand.

Run:
    python scripts/setup_mcp.py

It is a thin, friendly front-end over `hopenmind-mcp configure`. If the
`hopenmind-mcp` package is not importable, it prints the manual config instead.
"""

from __future__ import annotations

import sys


BANNER = r"""
  Metcore  -  MCP setup
  --------------------------
  This will register the 'metcore' MCP server in your LLM client.
"""

MANUAL_JSON = """
{
  "mcpServers": {
    "metcore": { "command": "metcore-mcp", "args": ["serve"] }
  }
}
"""


def _ask_choice(prompt: str, options: list[tuple[str, str]], default: int = 1) -> str:
    """Numbered multiple-choice prompt. Returns the chosen key."""
    print("\n" + prompt)
    for i, (key, label) in enumerate(options, 1):
        mark = "  (default)" if i == default else ""
        print(f"  {i}. {label}{mark}")
    while True:
        raw = input(f"Choice [1-{len(options)}] (Enter for {default}): ").strip()
        if raw == "":
            return options[default - 1][0]
        if raw.isdigit() and 1 <= int(raw) <= len(options):
            return options[int(raw) - 1][0]
        print("  Please enter a number from the list.")


def _ask_yes(prompt: str, default: bool = True) -> bool:
    d = "Y/n" if default else "y/N"
    raw = input(f"{prompt} [{d}]: ").strip().lower()
    if raw == "":
        return default
    return raw in ("y", "yes", "o", "oui")


def main() -> int:
    print(BANNER)

    try:
        from hopenmind_mcp import clients as _clients
        from hopenmind_mcp import configure as _configure
    except Exception:
        print("The 'hopenmind-mcp' package is not installed in this environment.")
        print("Install it with:  pip install hopenmind-mcp")
        print("\nThen add this entry to your client's MCP config manually:")
        print(MANUAL_JSON)
        return 1

    # 1) which clients
    try:
        known = _clients.detect_installed()
    except Exception:
        known = []
    detected = [c for c in known if getattr(c, "installed", True)]

    scope = _ask_choice(
        "Which clients do you want to configure?",
        [("detected", f"Only clients detected on this machine ({len(detected)} found)"),
         ("all", "Every client I know about"),
         ("pick", "Let me pick one by name")],
        default=1,
    )

    selection = None
    all_clients = False
    if scope == "all":
        all_clients = True
    elif scope == "pick":
        try:
            allc = _clients.detect_installed()
            opts = [(c.slug, getattr(c, "name", c.slug)) for c in allc]
        except Exception:
            opts = [("claude-desktop", "Claude Desktop"), ("cursor", "Cursor"),
                    ("vscode", "VS Code")]
        chosen = _ask_choice("Pick a client:", opts, default=1)
        selection = [chosen]

    # 2) preview first?
    dry = _ask_choice(
        "Apply now, or preview the changes first?",
        [("apply", "Apply the configuration now"),
         ("dry", "Preview only (write nothing)")],
        default=1,
    ) == "dry"

    # 3) confirm
    print("\nSummary:")
    print(f"  scope     : {scope}")
    print(f"  mode      : {'preview (dry-run)' if dry else 'apply'}")
    if not _ask_yes("Proceed?", default=True):
        print("Cancelled. Nothing was changed.")
        return 0

    try:
        rc = _configure.run(selection=selection, all_clients=all_clients,
                            dry_run=dry, interactive=False)
    except TypeError:
        # tolerate a slightly different signature across versions
        rc = _configure.run(selection=selection, dry_run=dry)
    if not dry and rc in (0, None):
        print("\nDone. Restart your client; the server appears as 'metcore'.")
        print("Tip: ask it to run  full_diagnosis  on the underdamped kernel.")
    return int(rc or 0)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\nCancelled.")
        raise SystemExit(130)
