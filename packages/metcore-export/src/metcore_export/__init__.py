"""hopenmind-export — academic figure export + branding.

Public surface:
  * ``BrandingConfig`` — editable header / logo / footer.
  * ``apply_branding(fig, cfg)`` — paint the header + footer on a Figure.
  * ``export_all(fig, outdir, basename, ...)`` — write 7 academic
    formats in one call (PNG 300/600, PDF, SVG, EPS, TIFF 300/600).
  * ``ACADEMIC_FORMATS`` — the canonical 7-format manifest.

The module can be used standalone (without the rest of the suite) as a
lightweight academic-figure saver.

SPDX-License-Identifier: Apache-2.0 OR LicenseRef-HopenMind-Commercial
"""

from __future__ import annotations

from metcore_export.core import (
    ACADEMIC_FORMATS,
    BrandingConfig,
    ExportResult,
    apply_branding,
    export_all,
    export_one,
    export_xml,
    result_to_dict,
)
from metcore_export.tables import (
    ATTACHMENTS,
    Attachment,
    add_data_table,
    export_csv,
    export_xlsx,
    write_attachment,
)
from metcore_export.theme import THEME_PRESETS, theme_colors, tint

__all__ = [
    "ACADEMIC_FORMATS",
    "BrandingConfig",
    "ExportResult",
    "apply_branding",
    "export_all",
    "export_one",
    "export_xml",
    "result_to_dict",
    "ATTACHMENTS",
    "Attachment",
    "add_data_table",
    "export_csv",
    "export_xlsx",
    "write_attachment",
    "THEME_PRESETS",
    "theme_colors",
    "tint",
]

__version__ = "0.1.0"
__author__ = "DESVAUX G.J.Y."
__contact__ = "contact@hopenmind.com"
__license__ = "Apache-2.0 OR LicenseRef-HopenMind-Commercial"
