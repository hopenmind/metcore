"""
Batch pipeline runner — YAML/TOML/JSON declarative sweeps.

Expands parameter sweeps, orchestrates parallel runs, classifies outputs,
writes structured index (same schema as single runs, just aggregated).

SPDX-License-Identifier: Apache-2.0 OR LicenseRef-BoltZ-Commercial
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional


def run_batch(
    *,
    config: Path,
    output_dir: Optional[Path],
    workers: int,
    resume: bool,
    dry_run: bool,
    quiet: bool,
    plain: bool,
) -> int:
    """Return exit code. Pending full implementation (Round 2)."""
    sys.stderr.write(
        f"Batch mode detected config: {config}\n"
        "Batch orchestration is pending full implementation (Round 2).\n"
        "The schema is defined and stable:\n"
        "\n"
        "  name: string\n"
        "  output_dir: path\n"
        "  output: { structured, visual, raw }\n"
        "  classification: flat | by_parameter | by_spectral | by_run\n"
        "  workers: int\n"
        "  defaults: { omega0, t_max, dt, ... }\n"
        "  runs: [ { spectral, params, sweep }, ... ]\n"
        "\n"
        "In the meantime, script multiple `boltz-kernel run` calls from a shell\n"
        "loop or Python — all three execution channels share the same core.\n"
    )
    return 2
