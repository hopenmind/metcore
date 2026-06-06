"""
Interactive guided session (opt-in).

Prompts for spectral density, parameters, preview, export formats.
Never invoked by default — explicit `boltz-kernel wizard`.

SPDX-License-Identifier: Apache-2.0 OR LicenseRef-BoltZ-Commercial
"""

from __future__ import annotations

import sys


def run_wizard() -> int:
    """Return exit code."""
    try:
        import questionary
    except ImportError:
        sys.stderr.write(
            "questionary not installed.\n"
            "pip install boltz-kernel (core deps already include it) "
            "or: pip install questionary\n"
        )
        return 3

    sys.stderr.write(
        "Wizard is pending full implementation (Round 2).\n"
        "Use `boltz-kernel run --help` for all available options in the meantime.\n"
    )
    return 2
