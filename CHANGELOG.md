# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project aims
to follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- New 'Shortcuts' tab + memkern.shortcuts: analytic one-stroke answers where the normal route is hours of simulation - exterior Lindbladian rate gamma_M, memory-modified Kuramoto threshold K_c(M), resonance line shape of the threshold shift, reaction-time scaling. Each also exposed as an MCP tool and in the batch dialog. From the corpus inventory (papers 1b, 2, 3a).
- '? > Tutorial & purpose' dialog: states the app's claim (measure whether memory matters and whether heavy non-Markovian compute is worth it, instead of guessing) and walks the decision pipeline step by step.
- First-launch branding placeholders: a bundled 'Your logo here' badge and a default 'Your institute / lab' header appear on every render until customized; one-click clear crosses in the Branding dialog. logo_path convention: 'auto' = placeholder, '' = none, path = custom. Two new MCP tools, branding_get / branding_set, expose the same ~/.metcore/branding.json contract so an LLM can read, propose and apply branding.
- Classic menu bar (File / Edit / Tools / ?) with a real About dialog (logo, version, DOI, links) and a persistent Preferences dialog (~/.metcore/settings.json): default live update, embedded-table rows, export formats and output folder, consumed by every panel and the batch dialog. New metcore_gui.preferences.
- Color themes for academic branding: pick a preset (oxford blue, crimson, burgundy gold, ...) or type two hex brand colors in the Branding dialog; curves, fills, table header and zebra rows all follow, in the GUI, every export, and the MCP export_curve. New metcore_export.theme (THEME_PRESETS, theme_colors, tint) + theme_primary/theme_secondary in BrandingConfig.
- Numeric outputs everywhere: each figure can now also be saved as CSV and Excel of its plotted columns, an XML sidecar, or an image with an embedded value table - via a checkable attachments system in the right-click menu and the batch dialog. New metcore_export.tables (export_csv/export_xlsx/add_data_table/write_attachment + ATTACHMENTS registry), controller.series(), and two MCP tools (export_formats, export_curve) for the same outputs.
- GUI fixes + brand: live update now redraws the same Figure in place (no more 1/4-size shrink on HiDPI) and works on all four panels; TIFF export fixed (routed through Pillow tags, was silently failing); new Metcore icon/logo, window icon wired and bundled.
- GUI user-friendliness: right-click export menu on every figure (one
  format, all 7, or figure plus XML data sidecar), debounced live update that
  redraws as inputs change, and a Tools > Batch processing dialog that runs a
  CSV of jobs through any tool and writes PNG plus XML per job with a naming
  pattern. New: metcore_export.export_xml, metcore_gui.batch, batch_panel,
  panel_features.
- Native installers for all desktops: Windows (Inno Setup .exe), macOS
  (.dmg with a Metcore.app bundle), Linux (self-contained .AppImage). Built per
  architecture by the CI matrix and attached to each release.
- Unified `metcore` MCP server aggregating the suite tools, with a `serve`
  entry point and a guided installer (`scripts/setup_mcp.py`).
- Nine MCP tools: `suite_info`, `kernel_embeddability`, `prony_decompose`,
  `maxent_select_order`, `nonmarkovianity_ng`, `cptp_certify`, `lindblad_gap`,
  `full_diagnosis`, `kernel_zoo`.
- `memkern.diagnostics`: embeddability gate (Hankel rank cliff vs power-law)
  with bootstrap confidence on the order K.
- `memkern.embedding`: exterior Lindbladian and the Lindblad-gap meter.
- `memkern.cptp`: CP-divisibility certifier (scalar matrix-Bernstein).
- `memkern.zoo`: canonical kernel library with analytic Prony modes.
- `memkern.pipeline.full_diagnosis`: one-call diagnostic pipeline.
- `memkern.adapters`: quantum (J(omega)) and neural (synaptic) domain adapters.
- GUI: tabs grouped by scientific domain; panels for N_G/obliquity, rheology
  G(t), quantum bath J(omega) and neural kernel K(t), with branded export.
- Documentation: rewritten `README.md`, `USAGE.md`, `MCP_DEPLOYMENT.md`, and
  presentation assets under `docs/assets/`.

### Changed
- `metcore-mcp` is now a working server, not a stub.

## [0.1.0]

### Added
- Initial monorepo: `memkern` (MET compiler), `boltz-kernel`, `obliquity-ng`,
  the HPC-triage line, export and CLI infrastructure.
