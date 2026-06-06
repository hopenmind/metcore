# `hopenmind-export`

Academic-figure export + branding for the Hope 'n Mind Suite.

- 7 formats: PNG 300/600, PDF, SVG, EPS, TIFF 300/600
- Editable `BrandingConfig` (institute, subtitle, reference, logo, footer)
- Invisible HNM metadata watermark on every file
- Standalone-usable, no suite dependency

## Usage

```python
from hopenmind_export import BrandingConfig, export_all

cfg = BrandingConfig(
    institute_name="Lab X",
    subtitle="Benchmark run 3",
    reference="arXiv:2504.XXXXX",
    footer_text="Fig. 3 — HNM Suite",
)
res = export_all(fig, "figures/", "fig3", branding=cfg)
# → 7 files in figures/ (fig3_png300.png, ..., fig3.pdf, fig3.svg, ...)
```
