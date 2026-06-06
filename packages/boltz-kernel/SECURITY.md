# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| 1.0.x   | Yes       |

## Reporting a Vulnerability

If you discover a security vulnerability in BoltZ-Kernel, please report it responsibly.

**Contact:** contact@hopenmind.com

**Do NOT** open a public GitHub issue for security vulnerabilities.

We will acknowledge receipt within 48 hours and provide a timeline for resolution.

## Scope

This software performs numerical simulations only. It does not:

- Connect to external servers or APIs
- Process user credentials or authentication tokens
- Store sensitive personal data
- Execute arbitrary user-supplied code (spectral densities are limited to mathematical functions)

The PyQt6 GUI runs entirely locally. The standalone executable (`M-E-K.exe`) is self-contained with no network access.

## Dependencies

Core dependencies are limited to well-maintained scientific Python packages:

- NumPy
- SciPy
- Matplotlib
- PyQt6 (GUI only)

Keep these updated to their latest stable versions.

---

**Authors:** DESVAUX G.J.Y. et al.  
**Copyright (c) 2008-2026 Hope 'n Mind SASU - Research**
