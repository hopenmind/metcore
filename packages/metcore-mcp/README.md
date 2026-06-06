# `hopenmind-mcp` — Unified MCP server for the Hope 'n Mind Suite

Status: **alpha / stub**. The package is published to reserve the PyPI
name and to anchor the import path. Aggregation logic will be added
as sub-tools land.

## Concept

Each sub-tool of the [Hope 'n Mind Scientific Suite](https://github.com/hopenmind/hopenmind-suite)
exposes its own [Model Context Protocol](https://modelcontextprotocol.io)
server. Rather than asking an agent to connect to several servers,
`hopenmind-mcp` imports each sub-tool's MCP surface and re-registers
every tool under one connection.

```
LLM agent  ──────►  hopenmind-mcp  ──► boltz-kernel MCP tools
                                     ──► ng-vol MCP tools
                                     ──► ...
```

## Install

```bash
pip install hopenmind-mcp              # core (MCP skeleton only)
pip install "hopenmind-mcp[boltz]"     # + BoltZ-Kernel tools
pip install "hopenmind-mcp[all]"       # + every stable sub-tool
```

## Run

```bash
hopenmind-mcp                          # stdio transport (default)
hopenmind-mcp --transport http --port 8787
```

## Licence

Apache-2.0 for academic / non-commercial use, proprietary for
commercial use. See [LICENSE](../LICENSE) at the suite root.
