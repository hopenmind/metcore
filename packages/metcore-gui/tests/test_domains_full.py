import numpy as np
from metcore_gui.panel import register_panel, panels_by_domain
from metcore_gui.quantum_panel import QuantumController, make_panel as qp
from metcore_gui.neural_panel import NeuralController, make_panel as npл
from metcore_gui.ng_panel import make_panel as ng
from metcore_gui.rheology_panel import make_panel as rh

def test_quantum_controller_runs():
    r = QuantumController().compute(spectral="drude", T=0.1, tau_max=12, n_points=120)
    assert "summary" in r.diagnosis
    assert r.C.shape == r.tau.shape

def test_neural_controller_runs():
    r = NeuralController().compute(tau_rise=0.3, tau_decay=3.0)
    assert "summary" in r.diagnosis
    assert np.real(r.K).max() > 0

def test_four_domains_present():
    register_panel("boltz-kernel", qp); register_panel("paper3a-neural", npл)
    register_panel("obliquity-ng", ng); register_panel("memkern-rheology", rh)
    g = panels_by_domain()
    assert {"Quantum","Neural","Diagnostics","Classical & Rheology"} <= set(g)
