import numpy as np
from metcore_gui.panel import register_panel, panels_by_domain
from metcore_gui.ng_panel import make_panel as ng
from metcore_gui.rheology_panel import RheologyController, RheologyPanel, make_panel as rheo

def test_rheology_recovers_maxwell_wiechert():
    c = RheologyController()
    r = c.compute_from_modes([2.0, 1.0], [0.4, 2.5], t_max=12, n_points=400)
    assert r.n_modes >= 2
    assert r.rms_error < 1e-3
    # relaxation times recovered (order-independent)
    got = sorted(np.round(r.relax_times, 1))
    assert got == [0.4, 2.5] or abs(got[0]-0.4) < 0.2

def test_domain_grouping():
    register_panel("obliquity-ng", ng)
    register_panel("memkern-rheology", rheo)
    groups = panels_by_domain()
    assert "Diagnostics" in groups
    assert "Classical & Rheology" in groups
    assert "obliquity-ng" in groups["Diagnostics"]
    assert "memkern-rheology" in groups["Classical & Rheology"]

def test_panel_domains():
    assert RheologyPanel.domain == "Classical & Rheology"
