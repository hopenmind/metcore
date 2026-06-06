"""
BoltZ-Kernel MCP (Model Context Protocol) server package.

Exposes the BoltZ-Kernel solver tools through MCP so that LLM-based
agents (Claude Desktop, Claude Code, Cursor, Continue.dev, any MCP
client) can call the solver directly from an editor or chat context,
without leaving the user's workflow.

Entry points:
    boltz-kernel mcp            — launch the server over stdio (default)
    boltz-kernel mcp --http     — launch over streamable HTTP on 127.0.0.1

Install:
    pip install "boltz-kernel[mcp]"

SPDX-License-Identifier: Apache-2.0 OR LicenseRef-BoltZ-Commercial
"""

__all__ = ["start_server"]


def start_server(transport: str = "stdio", host: str = "127.0.0.1", port: int = 7787) -> int:
    """Launch the MCP server. Returns process exit code."""
    from .server import launch
    return launch(transport=transport, host=host, port=port)
