"""bench-extrap — scaling-law extrapolator for NZ problems.

Runs a callable on 3 small problem sizes, fits a polynomial or
exponential cost model, extrapolates the wall-time at the requested
target size. Reports the tier that accommodates that target.

SPDX-License-Identifier: Apache-2.0 OR LicenseRef-HopenMind-Commercial
"""

from __future__ import annotations

from bench_extrap.tool import (
    BenchExtrapTool,
    bench_extrap_tool,
    fit_scaling_law,
)

__all__ = ["BenchExtrapTool", "bench_extrap_tool", "fit_scaling_law"]

__version__ = "0.1.0"
__author__ = "DESVAUX G.J.Y."
__license__ = "Apache-2.0 OR LicenseRef-HopenMind-Commercial"
