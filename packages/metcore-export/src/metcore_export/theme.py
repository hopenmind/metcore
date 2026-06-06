"""Color themes for academic branding.

A theme is two colors: *primary* (curves, table header) and *secondary*
(fit / comparison lines, accents). Everything else (zebra rows, edges,
fills) is derived as tints of the primary, so a lab only has to pick or
type its two brand colors and every figure and table follows.

Presets are named after their colors (not institutions). A custom theme
is just two hex fields in the branding config.

SPDX-License-Identifier: Apache-2.0 OR LicenseRef-HopenMind-Commercial
"""
from __future__ import annotations

# name -> (primary, secondary)
THEME_PRESETS: dict[str, tuple[str, str]] = {
    "metcore":        ("#1f4e8c", "#c0392b"),
    "oxford blue":    ("#002147", "#be9b58"),
    "cambridge blue": ("#00303c", "#85b09a"),
    "crimson":        ("#a51c30", "#2f2f2f"),
    "burgundy gold":  ("#6d071a", "#c8a45d"),
    "forest":         ("#1b4d3e", "#b58900"),
    "navy gold":      ("#003366", "#d29f13"),
    "charcoal coral": ("#36454f", "#e07a5f"),
    "teal rust":      ("#00696d", "#c75b12"),
    "violet":         ("#4b2e83", "#85754d"),
}


def _parse_hex(color: str) -> tuple[int, int, int]:
    c = (color or "").strip().lstrip("#")
    if len(c) == 3:
        c = "".join(ch * 2 for ch in c)
    if len(c) != 6:
        raise ValueError(f"not a hex color: {color!r}")
    return int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)


def tint(color: str, factor: float) -> str:
    """Blend *color* toward white. factor 0 -> color, 1 -> white."""
    try:
        r, g, b = _parse_hex(color)
    except ValueError:
        return color
    f = min(max(float(factor), 0.0), 1.0)
    return "#{:02x}{:02x}{:02x}".format(
        round(r + (255 - r) * f), round(g + (255 - g) * f),
        round(b + (255 - b) * f))


def theme_colors(branding=None) -> dict[str, str]:
    """Resolve the active theme into concrete colors.

    Reads theme_primary / theme_secondary from the given BrandingConfig
    (loaded from disk when None) and derives the rest. Always returns a
    full dict, falling back to the metcore default on any bad value.
    """
    primary, secondary = THEME_PRESETS["metcore"]
    cfg = branding
    if cfg is None:
        try:
            from metcore_export import BrandingConfig
            cfg = BrandingConfig.load()
        except Exception:
            cfg = None
    p = (getattr(cfg, "theme_primary", "") or "").strip()
    s = (getattr(cfg, "theme_secondary", "") or "").strip()
    try:
        _parse_hex(p); primary = p
    except ValueError:
        pass
    try:
        _parse_hex(s); secondary = s
    except ValueError:
        pass
    return {
        "primary":   primary,
        "secondary": secondary,
        "fill":      primary,           # used with low alpha under curves
        "header_bg": primary,
        "header_fg": "#ffffff",
        "zebra":     tint(primary, 0.93),
        "edge":      tint(primary, 0.72),
    }
