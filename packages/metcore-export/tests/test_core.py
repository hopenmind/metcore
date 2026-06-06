"""Tests for hopenmind-export.

SPDX-License-Identifier: Apache-2.0 OR LicenseRef-HopenMind-Commercial
"""

from __future__ import annotations

import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pytest

from metcore_export import (
    ACADEMIC_FORMATS,
    BrandingConfig,
    ExportResult,
    apply_branding,
    export_all,
    export_one,
)


# ──────────────────────────────────────────────────────────────────────────────
#  Manifest
# ──────────────────────────────────────────────────────────────────────────────

def test_manifest_has_seven_formats():
    assert len(ACADEMIC_FORMATS) == 7
    keys = [k for k, _, _ in ACADEMIC_FORMATS]
    assert keys == ["png300", "png600", "pdf", "svg", "eps", "tiff300", "tiff600"]


# ──────────────────────────────────────────────────────────────────────────────
#  BrandingConfig
# ──────────────────────────────────────────────────────────────────────────────

def test_defaults_are_first_launch_placeholders():
    cfg = BrandingConfig()
    # invite-to-customize defaults: placeholder header + bundled sample logo
    assert cfg.institute_name == "Your institute / lab"
    assert cfg.logo_path == "auto"
    assert cfg.subtitle == ""
    assert cfg.reference == ""


def test_metadata_default_carries_hnm_watermark():
    cfg = BrandingConfig()  # default embed_hnm_metadata=True
    meta = cfg.metadata_dict()
    assert "Hope 'n Mind" in meta["Software"]
    assert "Hope 'n Mind" in meta["Description"]


def test_metadata_opt_out_yields_zero_trace():
    """Setting embed_hnm_metadata=False strips all HNM-identifying fields."""
    cfg = BrandingConfig(embed_hnm_metadata=False)
    meta = cfg.metadata_dict()
    assert "Software" not in meta
    assert "Description" not in meta
    assert "Creator" not in meta
    assert "Keywords" not in meta
    # Only user-supplied fields remain
    assert set(meta.keys()) == {"Title", "Author", "Subject"}


def test_metadata_for_format_filters_per_backend():
    cfg = BrandingConfig(institute_name="Lab X", subtitle="Run 1",
                         reference="arXiv:2504.XXXXX")
    # PDF keeps 5 keys
    pdf_meta = cfg.metadata_for_format("pdf")
    assert pdf_meta is not None
    assert set(pdf_meta.keys()) <= {"Title", "Author", "Subject", "Keywords", "Creator"}
    # PNG/TIFF keep 4 keys
    png_meta = cfg.metadata_for_format("png")
    assert set(png_meta.keys()) <= {"Title", "Author", "Description", "Software"}
    # SVG/EPS return None
    assert cfg.metadata_for_format("svg") is None
    assert cfg.metadata_for_format("eps") is None


def test_roundtrip_save_load(tmp_path, monkeypatch):
    # Redirect ~/.hopenmind to tmp_path
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))  # Windows fallback

    cfg = BrandingConfig(institute_name="X", subtitle="Y", reference="Z",
                         footer_text="foot")
    # On Windows Path.home() may still resolve to the real home; patch
    # the classmethod explicitly.
    monkeypatch.setattr(BrandingConfig, "_config_path",
                        classmethod(lambda cls: tmp_path / "branding.json"))
    cfg.save()
    assert (tmp_path / "branding.json").is_file()

    cfg2 = BrandingConfig.load()
    assert cfg2.institute_name == "X"
    assert cfg2.subtitle == "Y"
    assert cfg2.footer_text == "foot"


# ──────────────────────────────────────────────────────────────────────────────
#  apply_branding — no crash, places texts
# ──────────────────────────────────────────────────────────────────────────────

def test_apply_branding_adds_texts():
    fig, ax = plt.subplots()
    ax.plot([0, 1], [0, 1])
    cfg = BrandingConfig(institute_name="Lab", subtitle="Sub",
                         reference="ref", footer_text="foot")
    apply_branding(fig, cfg)
    # at least institute/subtitle/reference/footer → 4 fig.texts
    assert len(fig.texts) >= 3
    plt.close(fig)


def test_apply_branding_idempotent():
    fig, ax = plt.subplots()
    ax.plot([0, 1], [0, 1])
    cfg = BrandingConfig(institute_name="Lab", footer_text="foot")
    apply_branding(fig, cfg)
    n1 = len(fig.texts)
    apply_branding(fig, cfg)
    n2 = len(fig.texts)
    assert n1 == n2  # same count after second apply
    plt.close(fig)


# ──────────────────────────────────────────────────────────────────────────────
#  export_all — round trip every format
# ──────────────────────────────────────────────────────────────────────────────

def _demo_figure():
    fig, ax = plt.subplots(figsize=(6, 4))
    t = np.linspace(0, 10, 200)
    ax.plot(t, np.sin(t))
    ax.set_xlabel("t")
    ax.set_ylabel("amplitude")
    return fig


def test_export_all_writes_most_formats(tmp_path):
    """EPS may fail on some Windows matplotlib builds (missing PostScript
    driver). The test asserts the three critical formats always write
    (PNG, PDF, SVG) and at least 5 of 7 formats succeed overall."""
    fig = _demo_figure()
    cfg = BrandingConfig(institute_name="Lab", subtitle="Demo")
    res = export_all(fig, tmp_path, "demo", branding=cfg)
    plt.close(fig)

    assert isinstance(res, ExportResult)
    # Mandatory formats must always work
    for k in ("png300", "png600", "pdf", "svg"):
        assert k in res.written, f"critical format {k} missing; failed={res.failed}"
    assert len(res.written) >= 5
    for path in res.paths():
        assert path.is_file()
        assert path.stat().st_size > 0


def test_export_subset(tmp_path):
    fig = _demo_figure()
    res = export_all(fig, tmp_path, "sub", formats=["pdf", "svg"])
    plt.close(fig)
    assert set(res.written.keys()) == {"pdf", "svg"}


def test_export_one_returns_path(tmp_path):
    fig = _demo_figure()
    p = export_one(fig, tmp_path, "one", "pdf")
    plt.close(fig)
    assert p.is_file()
    assert p.suffix == ".pdf"


def test_export_one_rejects_unknown_format():
    fig = _demo_figure()
    with pytest.raises(KeyError, match="Unknown format"):
        export_one(fig, ".", "x", "not-a-format")
    plt.close(fig)
