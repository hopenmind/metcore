"""Headless tests for the N_G panel controller — no Qt, no display."""
import os
import numpy as np
from metcore_gui.ng_panel import NGController, NGPanel, make_panel


def test_revival_is_nonmarkovian():
    r = NGController().compute(channel="revival", gamma=0.1, omega=2.0)
    assert r.n_g > 1e-2
    assert r.verdict.startswith("non-Markovian")
    # volume must re-expand somewhere (non-monotone) for a memory channel
    dv = np.diff(r.volume)
    assert (dv > 0).any()


def test_dephasing_is_markovian():
    r = NGController().compute(channel="dephasing", gamma=0.5, t_max=8.0, n_points=512)
    assert r.n_g < 1e-4
    assert r.verdict.startswith("Markovian")


def test_make_figure_applies_branding():
    from metcore_export import BrandingConfig
    cfg = BrandingConfig()
    cfg.institute_name = "Institut Test"
    cfg.footer_text = "unit-test footer"
    ctrl = NGController()
    fig = ctrl.make_figure(ctrl.compute(channel="revival"), branding=cfg)
    texts = [t.get_text() for t in fig.texts]
    assert "Institut Test" in texts
    assert "unit-test footer" in texts


def test_export_writes_files(tmp_path):
    from metcore_export import BrandingConfig
    ctrl = NGController()
    fig = ctrl.make_figure(ctrl.compute(channel="revival"), branding=BrandingConfig())
    res = ctrl.export(fig, tmp_path, basename="NG_revival",
                      formats=["png300", "pdf"])
    assert len(res) >= 1
    for p in res.paths():
        assert os.path.isfile(p) and os.path.getsize(p) > 0


def test_panel_contract():
    p = make_panel()
    assert isinstance(p, NGPanel)
    assert p.display_name and p.slug == "obliquity-ng"
    # build() needs Qt; we only check the class honours the headless contract
    assert hasattr(p, "on_run") and hasattr(p, "on_export")
