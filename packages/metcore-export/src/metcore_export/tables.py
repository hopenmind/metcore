"""Tabular + composite attachments for exported figures.

Lives in its own module (no heavy deps at import time) so the suite can offer,
next to each figure: the raw plotted columns as CSV or Excel, and an "image
with an embedded data table" PNG. New attachment kinds register in ATTACHMENTS.

SPDX-License-Identifier: Apache-2.0 OR LicenseRef-HopenMind-Commercial
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable


# ── series normalization ──────────────────────────────────────────────────────

def _normalize_series(series) -> list[tuple[str, "Any"]]:
    """Accept a dict {name: array} or a list[(name, array)]; return aligned
    (name, 1-D float array) columns truncated to the shortest length."""
    import numpy as np
    items = list(series.items()) if isinstance(series, dict) else list(series)
    cols = [(str(name), np.asarray(arr).ravel()) for name, arr in items]
    if not cols:
        return []
    n = min(len(arr) for _, arr in cols)
    return [(name, arr[:n]) for name, arr in cols]


# ── CSV / XLSX writers ────────────────────────────────────────────────────────

def export_csv(series, outdir, basename: str) -> Path:
    """Write the plotted columns as ``<basename>.csv`` (zero-dependency)."""
    import csv
    cols = _normalize_series(series)
    outdir = Path(outdir); outdir.mkdir(parents=True, exist_ok=True)
    path = outdir / f"{basename}.csv"
    names = [c[0] for c in cols]
    arrs = [c[1] for c in cols]
    nrow = len(arrs[0]) if arrs else 0
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(names)
        for i in range(nrow):
            w.writerow([f"{float(a[i]):.10g}" for a in arrs])
    return path


def export_xlsx(series, outdir, basename: str, *, sheet: str = "curve") -> Path:
    """Write the plotted columns as a native ``<basename>.xlsx`` workbook."""
    from openpyxl import Workbook
    from openpyxl.styles import Font
    cols = _normalize_series(series)
    wb = Workbook(); ws = wb.active; ws.title = sheet
    ws.append([c[0] for c in cols])
    for cell in ws[1]:
        cell.font = Font(bold=True)
    arrs = [c[1] for c in cols]
    nrow = len(arrs[0]) if arrs else 0
    for i in range(nrow):
        ws.append([float(a[i]) for a in arrs])
    ws.freeze_panes = "A2"
    outdir = Path(outdir); outdir.mkdir(parents=True, exist_ok=True)
    path = outdir / f"{basename}.xlsx"
    wb.save(path)
    return path


# ── data table painted onto a figure ─────────────────────────────────────────

def add_data_table(fig, series, *, max_rows: int = 12, fmt: str = "{:.4g}",
                   branding=None) -> None:
    """Paint a sampled value table at the bottom of *fig*.

    Samples up to ``max_rows`` evenly-spaced rows so a 3000-point curve still
    yields a readable table. The largest axes (the plot) is moved up to make
    room; small axes (logo) are left untouched.
    """
    import numpy as np
    cols = _normalize_series(series)
    if not cols:
        return
    names = [c[0] for c in cols]
    arrs = [c[1] for c in cols]
    nrow = len(arrs[0])
    k = max(2, min(max_rows, nrow))
    idx = np.unique(np.linspace(0, nrow - 1, k).round().astype(int))
    cell_text = [[fmt.format(float(a[i])) for a in arrs] for i in idx]

    # move the main (largest) axes into the top band
    if fig.axes:
        main = max(fig.axes, key=lambda ax: ax.get_position().width
                   * ax.get_position().height)
        main.set_position([0.12, 0.47, 0.80, 0.37])

    tax = fig.add_axes([0.06, 0.02, 0.88, 0.36]); tax.axis("off")
    table = tax.table(cellText=cell_text, colLabels=names,
                      loc="center", cellLoc="center")
    table.auto_set_font_size(False)
    table.set_fontsize(7)
    table.scale(1.0, 0.98)
    # academic styling from the active color theme: bold header band on the
    # primary color, zebra rows tinted from it (see metcore_export.theme)
    from metcore_export.theme import theme_colors
    th = theme_colors(branding)
    for (row, _col), cell in table.get_celld().items():
        cell.set_edgecolor(th["edge"])
        cell.set_linewidth(0.6)
        if row == 0:                      # header
            cell.set_facecolor(th["header_bg"])
            cell.set_text_props(color=th["header_fg"], fontweight="bold")
            cell.set_height(cell.get_height() * 1.2)
        else:                             # zebra rows
            cell.set_facecolor("#ffffff" if row % 2 else th["zebra"])


# ── attachment registry ───────────────────────────────────────────────────────

@dataclass(frozen=True)
class Attachment:
    key: str
    label: str
    needs_series: bool
    needs_figure: bool


ATTACHMENTS: list[Attachment] = [
    Attachment("xml",         "Data sidecar (XML)",          False, False),
    Attachment("csv",         "Curve data (CSV)",            True,  False),
    Attachment("xlsx",        "Curve data (Excel)",          True,  False),
    Attachment("image_table", "Image with data table (PNG)", True,  True),
]


def write_attachment(key: str, *, outdir, basename: str,
                     result=None, series=None,
                     make_figure: Callable[[], Any] | None = None,
                     dpi: int = 300) -> Path:
    """Produce one attachment file; return its Path."""
    if key == "xml":
        from metcore_export import export_xml
        return export_xml(result, outdir, basename)
    if key == "csv":
        return export_csv(series, outdir, basename)
    if key == "xlsx":
        return export_xlsx(series, outdir, basename)
    if key == "image_table":
        fig = make_figure()
        add_data_table(fig, series)
        if getattr(fig, "canvas", None) is None or \
                fig.canvas.__class__.__name__ == "FigureCanvasBase":
            from matplotlib.backends.backend_agg import FigureCanvasAgg
            FigureCanvasAgg(fig)
        outdir = Path(outdir); outdir.mkdir(parents=True, exist_ok=True)
        path = outdir / f"{basename}_table.png"
        fig.savefig(path, dpi=dpi)
        return path
    raise KeyError(f"unknown attachment {key!r}")
