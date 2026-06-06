import numpy as np
from memkern.diagnostics import (
    embeddability_report, bootstrap_order, hankel_singular_spectrum)


def test_single_exponential_is_embeddable():
    tau = np.linspace(0, 12, 256)
    C = np.exp(-0.5 * tau)                      # rational, K=1
    r = embeddability_report(tau, C)
    assert r["regime"] == "rational-embeddable"
    assert r["K_est"] == 1
    assert r["gap_ratio"] >= 8.0


def test_three_exponentials_embeddable_higher_K():
    tau = np.linspace(0, 20, 400)
    C = (2*np.exp(-0.3*tau) + 1.0*np.exp(-1.1*tau) + 0.5*np.exp(-3.0*tau))
    r = embeddability_report(tau, C)
    assert r["regime"] in ("rational-embeddable", "borderline")
    assert r["K_est"] >= 2


def test_power_law_is_flagged_subohmic():
    tau = np.linspace(0, 50, 512)
    C = (1.0 + tau) ** (-0.5)                   # sub-ohmic-like, no rank gap
    r = embeddability_report(tau, C)
    assert r["regime"] in ("power-law/sub-ohmic", "borderline")
    assert r["regime"] != "rational-embeddable"


def test_bootstrap_stability_clean_signal():
    tau = np.linspace(0, 12, 256)
    C = np.exp(-0.5 * tau)
    b = bootstrap_order(tau, C, noise_rel=0.01, n_boot=80)
    assert b["K_median"] == 1
    assert b["stable"] is True


def test_spectrum_descending():
    tau = np.linspace(0, 10, 128)
    C = np.exp(-0.7 * tau)
    sv = hankel_singular_spectrum(tau, C)
    assert np.all(np.diff(sv) <= 1e-9)
