import numpy as np
from memkern.adapters import quantum_kernel, neural_kernel, spectral_density
from memkern import embeddability_report, full_diagnosis

def test_drude_kernel_is_embeddable_lowT():
    tau, C = quantum_kernel("drude", T=0.02, tau_max=12, n_points=160, lam=1.0, gamma=1.0)
    # near T=0 the Drude correlation ~ exp(-gamma tau): single rational mode
    rep = embeddability_report(tau, np.real(C))
    assert rep["regime"] in ("rational-embeddable", "borderline")
    # decays monotonically in magnitude
    assert np.abs(C[-1]) < np.abs(C[0])

def test_subohmic_kernel_flagged():
    tau, C = quantum_kernel("subohmic", T=0.05, tau_max=30, n_points=200, s=0.4, wc=5.0)
    rep = embeddability_report(tau, np.real(C))
    assert rep["regime"] != "rational-embeddable"

def test_neural_kernel_two_modes_embeddable():
    tau, C = neural_kernel(tau_rise=0.3, tau_decay=3.0, tau_max=20, n_points=256)
    r = full_diagnosis(tau, C)
    assert r["steps"]["embeddability"]["regime"] in ("rational-embeddable","borderline")
    assert r["steps"]["embeddability"]["K_est"] >= 2 or "MET applies" in r["summary"]

def test_spectral_densities_positive():
    w = np.linspace(0.01, 10, 100)
    for name in ("drude","ohmic","subohmic","lorentzian"):
        assert np.all(spectral_density(name, w) >= 0)
