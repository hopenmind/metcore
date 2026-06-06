"""hpc-manifest — generate right-sized SLURM / PBS / LSF submission scripts.

Reads the cost and memory estimates attached to the upstream Verdict
(from ``hpc-oracle`` or ``bench-extrap``), applies a configurable
safety margin, and emits a submission script for the requested
scheduler. The script is a SOLVED verdict — the ladder stops here.

SPDX-License-Identifier: Apache-2.0 OR LicenseRef-HopenMind-Commercial
"""

from __future__ import annotations

from hpc_manifest.tool import (
    HPCManifestTool,
    hpc_manifest_tool,
    render_pbs,
    render_slurm,
)

__all__ = ["HPCManifestTool", "hpc_manifest_tool",
           "render_slurm", "render_pbs"]

__version__ = "0.1.0"
__author__ = "DESVAUX G.J.Y."
__license__ = "Apache-2.0 OR LicenseRef-HopenMind-Commercial"
