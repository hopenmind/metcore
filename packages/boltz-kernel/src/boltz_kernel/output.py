"""
Output writers — every format first-class.

Three axes, independent, all configurable:
  - structured : json | yaml | xml | jsonld | none
  - visual     : svg | pdf | png | tiff | eps | none
  - raw        : csv | hdf5 | parquet | none

Optional backends (HDF5, Parquet, JSON-LD, advanced XML) are loaded lazily
and raise a clear error only if actually requested.

SPDX-License-Identifier: Apache-2.0 OR LicenseRef-BoltZ-Commercial
"""

from __future__ import annotations

import csv as _csv
import json as _json
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET


# ── Top-level dispatch ─────────────────────────────────────────────────────────

def write_all(
    *,
    output_dir: Path,
    cmp,                  # ComparisonResult
    run_meta: dict,
    branding,             # BrandingConfig
    source_label: str,
    structured: str,
    visual: str,
    raw: str,
) -> list[dict[str, str]]:
    """
    Write every requested format to output_dir and return an artefact list:
        [{"type": "json", "path": "run.json"}, ...]
    """
    artifacts: list[dict[str, str]] = []

    if structured != "none":
        path = _write_structured(output_dir, run_meta, structured)
        artifacts.append({"type": structured, "path": path.name})

    if visual != "none":
        path = _write_visual(output_dir, cmp, branding, source_label, visual, run_meta)
        artifacts.append({"type": visual, "path": path.name})

    if raw != "none":
        path = _write_raw(output_dir, cmp, raw)
        artifacts.append({"type": raw, "path": path.name})

    return artifacts


# ── Structured writers (JSON / YAML / XML / JSON-LD) ───────────────────────────

def _write_structured(output_dir: Path, run_meta: dict, fmt: str) -> Path:
    if fmt == "json":
        path = output_dir / "run.json"
        with open(path, "w", encoding="utf-8") as f:
            _json.dump(run_meta, f, indent=2, ensure_ascii=False)
        return path

    if fmt == "yaml":
        try:
            import yaml  # PyYAML is a core dep
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError(
                "PyYAML not installed. pip install pyyaml"
            ) from exc
        path = output_dir / "run.yaml"
        with open(path, "w", encoding="utf-8") as f:
            yaml.safe_dump(run_meta, f, sort_keys=False, allow_unicode=True)
        return path

    if fmt == "xml":
        path = output_dir / "run.xml"
        root = _dict_to_xml("boltz-run", run_meta)
        tree = ET.ElementTree(root)
        ET.indent(tree, space="  ")
        tree.write(path, encoding="utf-8", xml_declaration=True)
        return path

    if fmt == "jsonld":
        path = output_dir / "run.jsonld"
        ld = _to_jsonld(run_meta)
        with open(path, "w", encoding="utf-8") as f:
            _json.dump(ld, f, indent=2, ensure_ascii=False)
        return path

    raise ValueError(f"Unknown structured format: {fmt}")


def _dict_to_xml(tag: str, obj: Any) -> ET.Element:
    """Recursive dict→XML. Lists become repeated children."""
    el = ET.Element(tag)
    if isinstance(obj, dict):
        for k, v in obj.items():
            key = str(k).replace("_", "-")
            if isinstance(v, (dict, list)):
                el.append(_dict_to_xml(key, v))
            else:
                child = ET.SubElement(el, key)
                child.text = "" if v is None else str(v)
    elif isinstance(obj, list):
        for item in obj:
            el.append(_dict_to_xml("item", item))
    else:
        el.text = "" if obj is None else str(obj)
    return el


def _to_jsonld(run_meta: dict) -> dict:
    """Minimal JSON-LD wrapper with schema.org SoftwareApplication + prov context."""
    return {
        "@context": {
            "schema": "https://schema.org/",
            "prov": "http://www.w3.org/ns/prov#",
            "boltz": "https://hopenmind.com/boltz-kernel/terms#",
            "name": "schema:name",
            "version": "schema:softwareVersion",
            "doi": "schema:identifier",
            "timestamp": "prov:generatedAtTime",
            "metrics": "boltz:metrics",
            "artifacts": "boltz:artifacts",
        },
        "@type": "prov:Entity",
        "tool": {
            "@type": "schema:SoftwareApplication",
            **run_meta["tool"],
        },
        **run_meta,
    }


# ── Visual writers (SVG / PDF / PNG / TIFF / EPS) ──────────────────────────────

def _write_visual(
    output_dir: Path, cmp, branding, source_label: str, fmt: str, run_meta: dict,
) -> Path:
    path = output_dir / f"comparison.{fmt}"
    metadata = branding.metadata_for_format(fmt, extra={
        "Title":       run_meta["run"]["id"],
        "Description": f"BoltZ-Kernel run {run_meta['run']['id']} · "
                       f"{run_meta['output']['regime_kernel']}",
    })
    cmp.plot(
        show=False,
        save=str(path),
        branding=branding,
        metadata=metadata,
        source_label=source_label,
    )
    return path


# ── Raw writers (CSV / HDF5 / Parquet) ─────────────────────────────────────────

def _write_raw(output_dir: Path, cmp, fmt: str) -> Path:
    t = cmp.t
    nm = cmp.nm
    mk = cmp.markov
    td = cmp.trace_distance

    if fmt == "csv":
        path = output_dir / "data.csv"
        with open(path, "w", encoding="utf-8", newline="") as f:
            w = _csv.writer(f)
            w.writerow([
                "t",
                "nm_population", "nm_coherence",
                "markov_population", "markov_coherence",
                "trace_distance",
            ])
            for i in range(len(t)):
                w.writerow([
                    f"{t[i]:.6f}",
                    f"{nm.populations[i]:.6e}",
                    f"{nm.coherences[i]:.6e}",
                    f"{mk.populations[i]:.6e}",
                    f"{mk.coherences[i]:.6e}",
                    f"{td[i]:.6e}",
                ])
        return path

    if fmt == "hdf5":
        try:
            import h5py
        except ImportError as exc:
            raise RuntimeError(
                "HDF5 support requires `pip install boltz-kernel[hdf5]`."
            ) from exc
        path = output_dir / "data.h5"
        with h5py.File(path, "w") as f:
            f.create_dataset("t", data=t)
            g_nm = f.create_group("nm")
            g_nm.create_dataset("population", data=nm.populations)
            g_nm.create_dataset("coherence",  data=nm.coherences)
            g_nm.create_dataset("bloch_x",    data=nm.x)
            g_nm.create_dataset("bloch_y",    data=nm.y)
            g_nm.create_dataset("bloch_z",    data=nm.z)
            g_mk = f.create_group("markov")
            g_mk.create_dataset("population", data=mk.populations)
            g_mk.create_dataset("coherence",  data=mk.coherences)
            f.create_dataset("trace_distance", data=td)
        return path

    if fmt == "parquet":
        try:
            import pyarrow as pa
            import pyarrow.parquet as pq
        except ImportError as exc:
            raise RuntimeError(
                "Parquet support requires `pip install boltz-kernel[parquet]`."
            ) from exc
        path = output_dir / "data.parquet"
        table = pa.table({
            "t": t,
            "nm_population":    nm.populations,
            "nm_coherence":     nm.coherences,
            "markov_population": mk.populations,
            "markov_coherence":  mk.coherences,
            "trace_distance":   td,
        })
        pq.write_table(table, path, compression="snappy")
        return path

    raise ValueError(f"Unknown raw format: {fmt}")
