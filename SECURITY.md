# Security Policy - Hope 'n Mind Scientific Suite

## Supported versions

| Package | Supported versions |
|---------|--------------------|
| `boltz-kernel` | 1.1.x (current), security patches back-ported to 1.0.x |
| `hopenmind-mcp` | 0.1.x (unified server) |
| `hopenmind-suite` (meta) | 0.1.x |

Sub-packages each track their own advisory stream.

## Reporting a vulnerability

Do **not** open a public GitHub issue for security problems.

Send a private report to **contact@hopenmind.com** with:

- Affected package and version
- A minimal reproducer (code, command, or trace)
- Your assessment of impact (CVSS or a plain-language severity)

You will receive an acknowledgement within 72 hours and a preliminary
triage within 5 business days. Coordinated disclosure is welcome; we
follow a default 90-day disclosure window, negotiable for complex fixes.

## Out of scope

- Pre-1.0 sub-packages (alpha/stub status).
- Issues in upstream dependencies - please report them upstream.
- Theoretical cryptographic strength of third-party primitives.

## Acknowledgements

Reporters who follow coordinated disclosure will be credited in the
release notes of the fixed version unless they prefer to remain
anonymous.
