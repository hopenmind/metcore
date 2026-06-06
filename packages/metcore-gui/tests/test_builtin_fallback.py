"""The frozen-app fallback must populate all four domains without entry-points."""
from metcore_gui import panel as P
from metcore_gui._builtin import register_builtin_panels

def test_builtin_registration_populates_domains():
    P._REGISTRY.clear()                      # simulate a bundle with no entry-points
    n = register_builtin_panels()
    assert n == 5  # 4 domain panels + the Shortcuts tab
    groups = P.panels_by_domain()
    assert {"Quantum","Neural","Diagnostics","Classical & Rheology"} <= set(groups)
