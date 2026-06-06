"""CLI entry point for ``hopenmind-mcp``.

Subcommands:
  * ``serve`` (default)  — run the MCP server (stub until aggregation lands).
  * ``configure``        — wire the server into popular MCP clients.
  * ``list-clients``     — show known clients and which appear installed.
"""

from __future__ import annotations

import argparse
import sys


def _cmd_serve(args: argparse.Namespace) -> int:
    try:
        from metcore_mcp.server import launch
    except Exception as exc:  # mcp not installed
        print("[hopenmind-mcp] cannot start server: " + str(exc), file=sys.stderr)
        print('[hopenmind-mcp] install the serve extra:  pip install "hopenmind-mcp[serve]"', file=sys.stderr)
        return 1
    print(
        f"[hopenmind-mcp] serving v0.1.0 — transport={args.transport} "
        f"host={args.host} port={args.port}",
        file=sys.stderr,
    )
    return launch(transport=args.transport, host=args.host, port=args.port)


def _cmd_configure(args: argparse.Namespace) -> int:
    from metcore_mcp import configure

    clients = None
    if args.clients:
        clients = [s.strip() for s in args.clients.split(",") if s.strip()]
    return configure.run(
        selection=clients,
        all_clients=args.all,
        dry_run=args.dry_run,
        interactive=not args.yes,
    )


def _cmd_list_clients(args: argparse.Namespace) -> int:
    from metcore_mcp import configure
    return configure.list_clients()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="hopenmind-mcp",
        description="Unified MCP server for the Hope 'n Mind Scientific Suite.",
    )
    sub = parser.add_subparsers(dest="command")

    # serve (default)
    p_serve = sub.add_parser(
        "serve",
        help="Run the MCP server (default if no subcommand given).",
    )
    p_serve.add_argument("--transport", choices=["stdio", "http"], default="stdio")
    p_serve.add_argument("--host", default="127.0.0.1")
    p_serve.add_argument("--port", type=int, default=8787)
    p_serve.set_defaults(func=_cmd_serve)

    # configure
    p_cfg = sub.add_parser(
        "configure",
        help="Install the server into popular MCP clients' config files.",
    )
    p_cfg.add_argument(
        "--clients",
        metavar="SLUGS",
        help="Comma-separated slugs (claude-desktop, claude-code, cursor, "
             "vscode, gemini-cli, opencode, windsurf, cline). "
             "Default: interactive on TTY, all detected otherwise.",
    )
    p_cfg.add_argument("--all", action="store_true",
                       help="Configure every known client, whether detected or not.")
    p_cfg.add_argument("--dry-run", action="store_true",
                       help="Show what would change without writing.")
    p_cfg.add_argument("--yes", action="store_true",
                       help="Non-interactive mode (skip confirmation prompts).")
    p_cfg.set_defaults(func=_cmd_configure)

    # list-clients
    p_list = sub.add_parser(
        "list-clients",
        help="List known MCP clients and which appear installed.",
    )
    p_list.set_defaults(func=_cmd_list_clients)

    args = parser.parse_args(argv)

    # Default to `serve` if no subcommand was given (preserves the old
    # invocation `hopenmind-mcp --transport http ...` as a fallback).
    if args.command is None:
        args.transport = getattr(args, "transport", "stdio")
        args.host = getattr(args, "host", "127.0.0.1")
        args.port = getattr(args, "port", 8787)
        return _cmd_serve(args)

    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
