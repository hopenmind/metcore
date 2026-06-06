"""
full_diagnosis - the one-call non-Markovian pipeline.

Data in (a measured kernel C(τ)), full verdict out:
  embeddability  →  Prony compile  →  CP-divisibility cert  →  Lindblad gap.

This is the coherence→decoherence bench in a single function: hand it a kernel
and it returns whether the MET applies, the embedding order K, whether Lindblad
is admissible, and quantitatively how wrong Lindblad is.

SPDX-License-Identifier: Apache-2.0 OR LicenseRef-HopenMind-Commercial
Author: DESVAUX G.J.Y. - Hope 'n Mind SASU - Research
"""

from __future__ import annotations

from typing import Any

import numpy as np

from memkern.diagnostics import embeddability_report
from memkern.prony import prony_decompose
from memkern.cptp import cptp_certify
from memkern.embedding import lindblad_gap


def full_diagnosis(tau, C, *, t_max: float = 20.0) -> dict[str, Any]:
    """Run the complete non-Markovian diagnostic pipeline on a kernel C(τ)."""
    tau = np.asarray(tau, dtype=float)
    C = np.asarray(C)
    report: dict[str, Any] = {"steps": {}}

    emb = embeddability_report(tau, C)
    report["steps"]["embeddability"] = emb
    if "error" in emb:
        report["summary"] = f"aborted: {emb['error']}"
        return report

    if emb["regime"] == "power-law/sub-ohmic":
        report["summary"] = (
            "Kernel is sub-ohmic / power-law: the finite MET does not apply. "
            "No finite Prony embedding; use the ε-extension and report truncation "
            "error. Downstream CP/Lindblad analysis skipped.")
        return report

    K = int(emb["K_est"])
    try:
        res = prony_decompose(tau, C.astype(complex), n_exp=K)
    except Exception as exc:
        report["summary"] = f"Prony compile failed at K={K}: {exc}"
        return report
    report["steps"]["prony"] = {
        "n_exp": int(res.n_exp),
        "rates": [{"re": float(b.real), "im": float(b.imag)} for b in res.betas],
        "rms_error": float(np.sqrt(np.mean(np.abs(res.evaluate(tau) - C) ** 2))),
    }

    cert = cptp_certify(res.alphas, res.betas, t_max=t_max)
    report["steps"]["cptp"] = cert
    gap = lindblad_gap(res.alphas, res.betas, t_max=t_max)
    report["steps"]["lindblad_gap"] = {
        k: gap[k] for k in ("gamma_M", "peak_gap", "integrated_gap",
                            "rate_min", "verdict") if k in gap}

    cp = cert.get("cp_divisible", None)
    summary = (
        f"MET applies (regime={emb['regime']}, K={K}). "
        + ("Dynamics is CP-divisible - Lindblad form admissible; "
           if cp else "Dynamics is NOT CP-divisible - Lindblad form inadmissible; ")
        + (f"Lindblad asymptotic rate γ_M={gap.get('gamma_M', float('nan')):.4g}, "
           f"integrated Lindblad error={gap.get('integrated_gap', float('nan')):.4g}.")
    )
    report["summary"] = summary
    return report
