"""
Batch processing core for the Metcore GUI - headless and unit-testable.

A "template" (patron) is: a controller, a list of jobs (each a dict of compute
parameters, optionally a "name"), an output folder, a set of formats, a filename
pattern, and a flag for the XML data sidecar. For each job this computes the
result, renders the branded figure, and writes the chosen image format(s) plus an
optional structured XML next to it, named by the pattern.

No Qt here on purpose: the GUI batch dialog is a thin front-end over run_batch.

SPDX-License-Identifier: Apache-2.0 OR LicenseRef-HopenMind-Commercial
Author: DESVAUX G.J.Y. - Hope 'n Mind SASU - Research
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable, Optional


class _SafeMap(dict):
    def __missing__(self, key):  # pattern references an absent field -> blank
        return ""


def _basename_for(pattern: str, index: int, job: dict) -> str:
    name = job.get("name") or f"job{index:03d}"
    fields = _SafeMap(job)
    fields["index"] = index
    fields["name"] = name
    try:
        out = pattern.format_map(fields)
    except Exception:
        out = name
    out = "".join(c if (c.isalnum() or c in "-_.") else "_" for c in out).strip("_")
    return out or f"job{index:03d}"


@dataclass
class BatchReport:
    n_jobs: int = 0
    n_ok: int = 0
    n_failed: int = 0
    jobs: list = field(default_factory=list)   # per-job {name, files, xml, error}

    def __len__(self) -> int:
        return self.n_ok


def run_batch(controller, jobs: Iterable[dict], outdir, *,
              formats: Iterable[str] = ("png600",), write_xml: bool = True,
              attachments: Iterable[str] = (), name_pattern: str = "{name}",
              branding: Any = None,
              progress: Optional[Callable[[int, int, str], None]] = None) -> BatchReport:
    """Run a controller over many parameter sets, exporting figures (+ XML).

    controller: any Qt-free controller exposing ``compute(**params)`` and
                ``make_figure(result, branding=...)``.
    jobs:       iterable of dicts of compute parameters (optional key "name").
    outdir:     destination folder (created if needed).
    formats:    image format keys from metcore_export.ACADEMIC_FORMATS.
    write_xml:  also write a structured <basename>.xml beside each figure.
    name_pattern: filename stem template, e.g. "{name}" or "{index}_{channel}".
    """
    from metcore_export import export_all, export_xml, BrandingConfig, write_attachment
    from matplotlib.backends.backend_agg import FigureCanvasAgg

    cfg = branding if branding is not None else BrandingConfig.load()
    outdir = Path(outdir)
    jobs = list(jobs)
    report = BatchReport(n_jobs=len(jobs))

    for i, job in enumerate(jobs):
        name = job.get("name") or f"job{i:03d}"
        if progress:
            progress(i, len(jobs), name)
        entry: dict[str, Any] = {"name": name, "files": [], "xml": None,
                                 "attachments": [], "error": None}
        try:
            params = {k: v for k, v in job.items() if k != "name"}
            result = controller.compute(**params)
            try:
                fig = controller.make_figure(result, branding=cfg)
            except TypeError:
                fig = controller.make_figure(result)
            if getattr(fig, "canvas", None) is None or \
                    fig.canvas.__class__.__name__ == "FigureCanvasBase":
                FigureCanvasAgg(fig)
            base = _basename_for(name_pattern, i, job)
            res = export_all(fig, outdir, base, branding=cfg,
                             formats=list(formats), apply=False)
            entry["files"] = [str(p) for p in res.paths()]
            if write_xml:
                entry["xml"] = str(export_xml(result, outdir, base))
            atts = list(attachments)
            if atts:
                series = controller.series(result) if hasattr(controller, "series") else None
                def _mk(_r=result):
                    try:
                        return controller.make_figure(_r, branding=cfg)
                    except TypeError:
                        return controller.make_figure(_r)
                for key in atts:
                    try:
                        ap = write_attachment(key, outdir=outdir, basename=base,
                                              result=result, series=series, make_figure=_mk)
                        entry["attachments"].append(str(ap))
                    except Exception as aexc:  # a missing attachment must not kill the job
                        entry.setdefault("attach_errors", []).append(f"{key}: {aexc}")
            report.n_ok += 1
        except Exception as exc:  # one bad job must not kill the batch
            entry["error"] = f"{type(exc).__name__}: {exc}"
            report.n_failed += 1
        report.jobs.append(entry)
    return report


def load_jobs_csv(path) -> list[dict]:
    """Read a CSV of parameter sets, one job per row.

    The header row names the compute parameters (a "name" column is optional and
    used for output naming). Numeric cells are converted to int/float; everything
    else stays a string.
    """
    import csv
    jobs: list[dict] = []
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            job: dict[str, Any] = {}
            for k, v in row.items():
                if k is None:
                    continue
                v = (v or "").strip()
                if v == "":
                    continue
                if k == "name":
                    job[k] = v
                    continue
                try:
                    job[k] = int(v)
                except ValueError:
                    try:
                        job[k] = float(v)
                    except ValueError:
                        job[k] = v
            if job:
                jobs.append(job)
    return jobs
