import numpy as np
from memkern.embedding import lindblad_gap, exterior_lindblad_rate
from memkern.cptp import cptp_certify
from memkern import zoo


def test_drude_is_cp_divisible_and_lindblad_tight_asymptotically():
    k = zoo.drude(lam=1.0, gamma=1.0)
    cert = cptp_certify(k.alphas, k.betas, t_max=20)
    assert cert["cp_divisible"] is True
    g = lindblad_gap(k.alphas, k.betas, t_max=20)
    assert abs(g["gamma_M"] - 1.0) < 1e-9          # γ_M = λ = 1
    assert g["gap"][-1] < 1e-2                       # gap vanishes asymptotically
    assert g["peak_gap"] > 0                         # but is nonzero transiently


def test_underdamped_breaks_cp_and_has_large_gap():
    k = zoo.underdamped(lam=1.0, w0=3.0, gamma=0.15)
    cert = cptp_certify(k.alphas, k.betas, t_max=30)
    assert cert["cp_divisible"] is False
    assert cert["rate_min"] < 0
    assert len(cert["breakdown_intervals"]) >= 1
    g = lindblad_gap(k.alphas, k.betas, t_max=30)
    assert g["integrated_gap"] > 0
    assert g["verdict"].startswith("Lindblad misses")


def test_exterior_rate_matches_hat_C_zero():
    # γ_M = Re Σ α_k/β_k
    a = np.array([2.0+0j, 1.0+0j]); b = np.array([0.5+0j, 2.0+0j])
    assert abs(exterior_lindblad_rate(a, b) - (2/0.5 + 1/2)) < 1e-12


def test_zoo_prony_recovers_drude_mode():
    from memkern import prony_decompose
    k = zoo.drude(lam=1.0, gamma=0.7)
    tau = np.linspace(0, 12, 256)
    res = prony_decompose(tau, k.C(tau), n_exp=1)
    assert abs(res.betas[0].real - 0.7) < 1e-2


def test_zoo_listing_has_domains():
    names = {e["name"]: e for e in zoo.list_zoo()}
    assert names["maxwell_wiechert"]["domain"] == "rheology"
    assert names["subohmic"]["rational"] is False


def test_subohmic_flagged_by_embeddability():
    from memkern import embeddability_report
    k = zoo.subohmic(s=0.5, wc=1.0)
    tau = np.linspace(0, 50, 512)
    rep = embeddability_report(tau, k.C(tau))
    assert rep["regime"] != "rational-embeddable"
