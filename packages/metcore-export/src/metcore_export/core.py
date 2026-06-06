"""Core of hopenmind-export — branding + 7-format academic export.

Lifts the production-grade BrandingConfig and writer logic that have
been battle-tested inside BoltZ-Kernel since 2026, into a
suite-generic package. Defaults are now tool-neutral (no "BoltZ-Kernel"
hardcoded); the invisible HNM metadata watermark remains on every file.

SPDX-License-Identifier: Apache-2.0 OR LicenseRef-HopenMind-Commercial
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable


# ──────────────────────────────────────────────────────────────────────────────
#  Canonical academic-format manifest
# ──────────────────────────────────────────────────────────────────────────────

# (key, extension, dpi-or-None)  — dpi None ⇒ vector output
ACADEMIC_FORMATS: list[tuple[str, str, int | None]] = [
    ("png300",  "png",  300),   # conference / web
    ("png600",  "png",  600),   # high-res print
    ("pdf",     "pdf",  None),  # LaTeX / journals
    ("svg",     "svg",  None),  # Inkscape / Illustrator
    ("eps",     "eps",  None),  # AIP / APS legacy journals
    ("tiff300", "tiff", 300),   # standard print
    ("tiff600", "tiff", 600),   # biomedical / optics
]


# ──────────────────────────────────────────────────────────────────────────────
#  Invisible HNM watermark — always embedded in file metadata
# ──────────────────────────────────────────────────────────────────────────────

_HNM_SOFTWARE  = "Metcore - Hope 'n Mind Scientific Suite"
_HNM_COPYRIGHT = "Hope 'n Mind SASU - Research - https://doi.org/10.5281/zenodo.20557167"


# ──────────────────────────────────────────────────────────────────────────────
#  BrandingConfig
# ──────────────────────────────────────────────────────────────────────────────

_DEFAULTS = {
    "institute_name":       "Your institute / lab",   # placeholder until edited
    "subtitle":             "",            # 2nd line — experiment / method name
    "reference":            "",            # 3rd line — DOI, arXiv, grant
    "logo_path":            "auto",        # "auto" → bundled "Your logo here";
                                           # ""     → no logo; path → custom logo
    "logo_position":        "left",        # "left" | "right"
    "footer_text":          "",
    "source_label":         "",            # small italic top-left (J(ω): ...)
    "theme_primary":        "",            # hex color; empty -> metcore default
    "theme_secondary":      "",            # hex color; empty -> metcore default
    "embed_hnm_metadata":   True,          # invisible HNM watermark in file properties
}


@dataclass
class BrandingConfig:
    """Editable branding applied to every figure exported by the suite.

    All visible fields are blank by default — no "HNM" branding is
    forced on researchers. An invisible HNM watermark is embedded in
    the file metadata by default (Software/Creator fields); set
    ``embed_hnm_metadata=False`` to get zero-trace files.
    """
    institute_name:     str  = _DEFAULTS["institute_name"]
    subtitle:           str  = _DEFAULTS["subtitle"]
    reference:          str  = _DEFAULTS["reference"]
    logo_path:          str  = _DEFAULTS["logo_path"]
    logo_position:      str  = _DEFAULTS["logo_position"]
    footer_text:        str  = _DEFAULTS["footer_text"]
    source_label:       str  = _DEFAULTS["source_label"]
    theme_primary:      str  = _DEFAULTS["theme_primary"]
    theme_secondary:    str  = _DEFAULTS["theme_secondary"]
    embed_hnm_metadata: bool = _DEFAULTS["embed_hnm_metadata"]

    # ── Persistence ────────────────────────────────────────────────────────
    @classmethod
    def _config_path(cls) -> Path:
        return Path.home() / ".metcore" / "branding.json"

    @classmethod
    def load(cls) -> "BrandingConfig":
        """Load from ``~/.metcore/branding.json`` or return defaults."""
        cfg = cls()
        path = cls._config_path()
        if not path.is_file():
            return cfg
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            for k in _DEFAULTS:
                if k in data:
                    setattr(cfg, k, str(data[k]))
        except Exception:
            pass
        return cfg

    def save(self) -> None:
        path = self._config_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {k: getattr(self, k) for k in _DEFAULTS}
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False),
                        encoding="utf-8")

    # ── File metadata ──────────────────────────────────────────────────────
    def metadata_dict(self, extra: dict[str, Any] | None = None) -> dict[str, str]:
        meta: dict[str, str] = {
            "Title":    self.subtitle or "Hope 'n Mind Suite figure",
            "Author":   self.institute_name,
            "Subject":  self.reference,
        }
        if self.embed_hnm_metadata:
            meta.update({
                "Software":    _HNM_SOFTWARE,
                "Description": _HNM_COPYRIGHT,
                "Creator":     _HNM_SOFTWARE,
                "Keywords":    "hope-n-mind, scientific-computing",
            })
        if extra:
            meta.update(extra)
        return meta

    def metadata_for_format(self, ext: str,
                            extra: dict[str, Any] | None = None
                            ) -> dict[str, str] | None:
        """Filter metadata to keys accepted by each matplotlib backend.

        PNG / TIFF (Agg) : Title, Author, Description, Software
        PDF              : Title, Author, Subject, Keywords, Creator
        SVG / EPS        : None (not reliably supported across versions)
        """
        base = self.metadata_dict(extra)
        ext = ext.lower().lstrip(".")
        if ext == "pdf":
            return {k: base[k] for k in
                    ("Title", "Author", "Subject", "Keywords", "Creator")
                    if k in base}
        if ext in ("png", "tif", "tiff"):
            return {k: base[k] for k in
                    ("Title", "Author", "Description", "Software")
                    if k in base}
        return None


# ──────────────────────────────────────────────────────────────────────────────
#  apply_branding — paint header/footer/logo on a Figure
# ──────────────────────────────────────────────────────────────────────────────

def _placeholder_logo_path() -> str | None:
    """Locate the bundled "Your logo here" placeholder (dev, wheel, frozen)."""
    try:
        from importlib.resources import files
        p = files("metcore_export") / "assets" / "your_logo_here.png"
        if p.is_file():
            return str(p)
    except Exception:
        pass
    return None


def apply_branding(fig, cfg: BrandingConfig) -> None:
    """Stamp branding on a matplotlib Figure.

    Layout:
      * Top center: institute_name (bold) + subtitle + reference (italic, grey)
      * Top left (optional): source_label (small italic, "J(ω): ...")
      * Footer (bottom center): footer_text (small italic grey)
      * Inset logo: top left or top right, preserves aspect
    """
    import matplotlib.image as mpimg  # lazy, keeps import graph light

    fig.texts.clear()

    y_top = 0.985
    if cfg.institute_name:
        fig.text(0.5, y_top, cfg.institute_name,
                 ha="center", va="top", fontsize=11, fontweight="bold")
        y_cur = y_top - 0.038
    else:
        y_cur = y_top

    if cfg.subtitle:
        fig.text(0.5, y_cur, cfg.subtitle,
                 ha="center", va="top", fontsize=10)
        y_cur -= 0.030

    if cfg.reference:
        fig.text(0.5, y_cur, cfg.reference,
                 ha="center", va="top", fontsize=8,
                 color="#555555", style="italic")

    if cfg.source_label:
        fig.text(0.01, 0.895, cfg.source_label,
                 ha="left", va="top",
                 fontsize=7.5, color="#444444", style="italic")

    if cfg.footer_text:
        fig.text(0.5, 0.005, cfg.footer_text,
                 ha="center", va="bottom",
                 fontsize=7, color="#888888", style="italic")

    logo_path = cfg.logo_path
    if logo_path == "auto":
        logo_path = _placeholder_logo_path() or ""
    if logo_path and os.path.isfile(logo_path):
        try:
            img = mpimg.imread(logo_path)
            if cfg.logo_position == "right":
                ax_logo = fig.add_axes([0.87, 0.90, 0.09, 0.09])
            else:
                ax_logo = fig.add_axes([0.04, 0.90, 0.09, 0.09])
            ax_logo.imshow(img)
            ax_logo.axis("off")
        except Exception:
            pass  # logo failure must never kill export


# ──────────────────────────────────────────────────────────────────────────────
#  Export
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class ExportResult:
    """Map of format-key → written filepath (plus any failures)."""
    written: dict[str, Path] = field(default_factory=dict)
    failed:  dict[str, str]  = field(default_factory=dict)

    def __len__(self) -> int:
        return len(self.written)

    def paths(self) -> list[Path]:
        return list(self.written.values())


def _format_spec(key: str) -> tuple[str, int | None]:
    for k, ext, dpi in ACADEMIC_FORMATS:
        if k == key:
            return ext, dpi
    raise KeyError(f"Unknown format key {key!r}. "
                   f"Known: {[k for k, _, _ in ACADEMIC_FORMATS]}")


def export_one(fig, outdir: str | os.PathLike,
               basename: str, format_key: str,
               cfg: BrandingConfig | None = None) -> Path:
    """Save ``fig`` in one academic format; return the written Path."""
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    ext, dpi = _format_spec(format_key)

    cfg = cfg or BrandingConfig()
    meta = cfg.metadata_for_format(ext)

    fname = f"{basename}_{format_key}.{ext}" if dpi else f"{basename}.{ext}"
    path = outdir / fname

    kwargs: dict[str, Any] = {}
    if dpi:
        kwargs["dpi"] = dpi

    if ext in ("tif", "tiff"):
        # matplotlib's Agg backend rejects metadata= for TIFF; route the
        # invisible watermark through Pillow's TIFF tags instead. Falls back
        # to a plain (metadata-free) TIFF if Pillow is unavailable.
        if meta:
            try:
                from PIL.TiffImagePlugin import ImageFileDirectory_v2
                info = ImageFileDirectory_v2()
                if meta.get("Software"):
                    info[305] = meta["Software"]            # Software tag
                desc = meta.get("Description") or meta.get("Title")
                if desc:
                    info[270] = desc                        # ImageDescription
                kwargs["pil_kwargs"] = {"tiffinfo": info}
            except Exception:
                pass
    elif meta is not None:
        kwargs["metadata"] = meta

    fig.savefig(path, **kwargs)
    return path


def export_all(fig, outdir: str | os.PathLike,
               basename: str, *,
               branding: BrandingConfig | None = None,
               formats: Iterable[str] | None = None,
               apply: bool = True) -> ExportResult:
    """Export a figure in every academic format at once.

    Parameters
    ----------
    fig : matplotlib.figure.Figure
    outdir : str or Path
        Destination directory (created if needed).
    basename : str
        Stem of each output file.
    branding : BrandingConfig or None
        If None, a default (blank) config is used. The invisible HNM
        metadata watermark is still embedded on every file.
    formats : iterable of format keys or None
        Subset of ``ACADEMIC_FORMATS`` to emit. Default: all seven.
    apply : bool
        If True, the branding is painted on the figure before saving
        (idempotent if called multiple times).

    Returns
    -------
    ExportResult
        ``.written`` maps format-key to the absolute path; ``.failed``
        holds a per-format error message for any format that threw.
    """
    cfg = branding or BrandingConfig()
    if apply:
        apply_branding(fig, cfg)
    keys = list(formats) if formats else [k for k, _, _ in ACADEMIC_FORMATS]

    result = ExportResult()
    for k in keys:
        try:
            result.written[k] = export_one(fig, outdir, basename, k, cfg)
        except Exception as exc:  # noqa: BLE001
            result.failed[k] = f"{type(exc).__name__}: {exc}"
    return result


# ──────────────────────────────────────────────────────────────────────────────
#  Structured result export (XML) - the data sidecar next to each figure
# ──────────────────────────────────────────────────────────────────────────────

def _to_serializable(value, array_cap: int = 64):
    """Convert numpy / dataclass / nested values into XML-friendly Python.

    Small arrays (<= array_cap) become lists; large arrays become a compact
    summary (length, min, max, mean) so the XML stays readable.
    """
    import numpy as _np
    import dataclasses as _dc
    if _dc.is_dataclass(value) and not isinstance(value, type):
        return {k: _to_serializable(v, array_cap) for k, v in _dc.asdict(value).items()}
    if isinstance(value, dict):
        return {str(k): _to_serializable(v, array_cap) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_serializable(v, array_cap) for v in value]
    if isinstance(value, _np.ndarray):
        if value.size <= array_cap:
            return [_to_serializable(v, array_cap) for v in value.tolist()]
        flat = _np.asarray(value, dtype=float).ravel()
        return {"_array": True, "length": int(value.size),
                "shape": list(value.shape),
                "min": float(_np.nanmin(flat)), "max": float(_np.nanmax(flat)),
                "mean": float(_np.nanmean(flat))}
    if isinstance(value, (_np.integer,)):
        return int(value)
    if isinstance(value, (_np.floating,)):
        return float(value)
    if isinstance(value, (_np.bool_,)):
        return bool(value)
    if isinstance(value, complex):
        return {"re": value.real, "im": value.imag}
    return value


def _dict_to_xml(parent, data):
    import xml.etree.ElementTree as ET
    if isinstance(data, dict):
        for k, v in data.items():
            key = str(k)
            if not (key[:1].isalpha() or key[:1] == "_"):
                key = "field_" + key
            child = ET.SubElement(parent, key)
            _dict_to_xml(child, v)
    elif isinstance(data, (list, tuple)):
        for v in data:
            item = ET.SubElement(parent, "item")
            _dict_to_xml(item, v)
    else:
        parent.text = "" if data is None else str(data)


def result_to_dict(result, array_cap: int = 64) -> dict:
    """Turn a controller result (dataclass / dict) into a serializable dict."""
    d = _to_serializable(result, array_cap)
    return d if isinstance(d, dict) else {"value": d}


def export_xml(result, outdir, basename: str, *,
               root_tag: str = "metcore_result", array_cap: int = 64) -> "Path":
    """Write a structured result as ``<basename>.xml`` and return the Path."""
    import xml.etree.ElementTree as ET
    outdir = Path(outdir); outdir.mkdir(parents=True, exist_ok=True)
    data = result_to_dict(result, array_cap)
    root = ET.Element(root_tag)
    root.set("software", _HNM_SOFTWARE)
    _dict_to_xml(root, data)
    tree = ET.ElementTree(root)
    try:
        ET.indent(tree, space="  ")
    except Exception:
        pass
    path = outdir / f"{basename}.xml"
    tree.write(path, encoding="utf-8", xml_declaration=True)
    return path
