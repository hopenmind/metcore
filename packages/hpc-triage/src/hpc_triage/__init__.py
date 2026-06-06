"""hpc-triage — answers "do you actually need a supercomputer?".

A triage toolkit for PhD students and researchers working on
non-Markovian open-quantum-system problems. Given a ``Problem``, the
``cascade()`` runs an ordered ladder of tools (kernel-audit,
memkern-ladder, hpc-oracle, bench-extrap, cloud-dispatcher,
hpc-manifest) until one of them ``SOLVED`` the problem, confirmed it
``BLOCKED`` at every tested tier, or aborted.

This package contains the **abstraction** (``Problem``, ``Verdict``,
``TriageTool``, ``cascade``). Individual tools ship as sibling packages
that all implement the ``TriageTool`` protocol.

SPDX-License-Identifier: Apache-2.0 OR LicenseRef-HopenMind-Commercial
"""

from __future__ import annotations

from hpc_triage.core import (
    Problem,
    Tier,
    TriageTool,
    Verdict,
    VerdictStatus,
    cascade,
)

__all__ = [
    "Problem",
    "Tier",
    "TriageTool",
    "Verdict",
    "VerdictStatus",
    "cascade",
]

__version__ = "0.1.0"
__author__ = "DESVAUX G.J.Y."
__contact__ = "contact@hopenmind.com"
__license__ = "Apache-2.0 OR LicenseRef-HopenMind-Commercial"
