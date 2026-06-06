<!-- ╔══════════════════════════════════════════════════════════════╗
     ║   BoltZ-Kernel — Non-Markovian Quantum Dynamics Solver        ║
     ║   Boltzmann Memory Kernel via Maximum Entropy Principle       ║
     ║   DESVAUX G.J.Y. (2006–2026) · Hope 'n Mind Research          ║
     ╚══════════════════════════════════════════════════════════════╝ -->

<div align="center">

[![DOI](https://img.shields.io/badge/DOI-10.5281%2Fzenodo.19648837-c9a84c?style=for-the-badge&logo=doi&logoColor=white)](https://doi.org/10.5281/zenodo.19648837)
[![License: Apache-2.0 OR Commercial](https://img.shields.io/badge/License-Apache--2.0_or_Commercial-3d7fff?style=for-the-badge)](./LICENSE)
[![ORCID](https://img.shields.io/badge/ORCID-0009--0008--9813--4627-a6794e?style=for-the-badge&logo=orcid&logoColor=white)](https://orcid.org/0009-0008-9813-4627)
[![Python](https://img.shields.io/badge/Python-3.9+-3776AB?style=for-the-badge&logo=python&logoColor=white)]()

<br/>

<!-- <img src="./assets/pipeline.svg" alt="BoltZ-Kernel Solver Pipeline" width="100%"/> -->

<br/><br/>

# BoltZ-Kernel

**Non-Markovian Quantum Dynamics Solver with Boltzmann Memory Kernel**

*A diagnostic tool that detects where Lindblad fails — and shows you what non-Markovian dynamics actually look like for your specific environment.*

<br/>

</div>

---

## Table of Contents

- [Why This Solver Exists](#why-this-solver-exists)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Theory in 3 Equations](#theory-in-3-equations)
- [Execution Channels](#execution-channels)
- [Bring Your Own Data](#bring-your-own-data)
- [Built-in Spectral Densities](#built-in-spectral-densities)
- [Backend Selection](#backend-selection)
- [Output Formats](#output-formats)
- [What the Results Tell You](#what-the-results-tell-you)
- [Python API](#python-api)
- [Branding](#branding)
- [Known Limitations](#known-limitations)
- [Citation](#citation)
- [License](#license)

---

## Why This Solver Exists

Every quantum photonics lab measures the spectral density **J(ω)** of their environment — a cavity, a photonic crystal, a waveguide. Then, to predict how their qubit decoheres, they plug it into the **Lindblad master equation**. It's the default. Everybody does it.

The problem is that **Lindblad assumes the environment forgets instantly**. No memory. And everybody knows this is wrong as soon as the spectral density has structure — a sharp peak, a band edge, discrete modes. In those cases, the environment remembers, and Lindblad gives the wrong answer. Coherence decays too fast. Population revivals vanish. The prediction diverges from reality.

The reason people keep using Lindblad anyway is that the alternatives are painful. Full non-Markovian methods (Nakajima-Zwanzig, HEOM, process tensor) are either system-specific, computationally heavy, or require expertise that most experimentalists don't have time for.

> **BoltZ-Kernel is the missing middle ground.** You give it your J(ω) — measured, fitted, or theoretical — and it:
>
> 1. Computes the bath correlation function **C(τ)** from your spectral density
> 2. Builds a memory kernel **K*(t,s)** using the Maximum Entropy (Jaynes MaxEnt) principle — the least-biased Boltzmann-form kernel consistent with your environment's correlations
> 3. Solves the full integro-differential master equation with that kernel
> 4. Solves the standard Lindblad equation in parallel
> 5. **Tells you exactly how much they disagree, where, and why**

If the trace distance between the two solutions stays below **1%**, Lindblad is fine for your system — you can stop worrying. If it's at **10%** or more, your Lindblad predictions are wrong and the solver shows you what non-Markovian dynamics actually look like: population revivals, slower coherence decay, power-law tails instead of exponentials.

**It's a diagnostic tool.** Not a replacement for full theory, but a detector that says *"here, Lindblad lies"* — and shows you what the truth looks like.

---

## Installation

```bash
# Core (CLI + Python API + JSON/CSV/SVG/PDF/PNG outputs)
pip install boltz-kernel

# Everything (GUI + HDF5 + Parquet + XML + JSON-LD + term-image preview)
pip install "boltz-kernel[all]"

# Selective extras
pip install "boltz-kernel[gui]"      # PyQt6 desktop application
pip install "boltz-kernel[hdf5]"     # HDF5 raw-data export
pip install "boltz-kernel[parquet]"  # Apache Parquet raw-data export
pip install "boltz-kernel[xml]"      # lxml for advanced XML workflows
pip install "boltz-kernel[jsonld]"   # rdflib for semantic-web outputs
```

All Python ≥ 3.9, on Linux / macOS / Windows.

For a self-contained Windows executable without Python, see [releases](https://github.com/hopenmind/hopenmind-suite/releases).

---

## Quick Start

```bash
# Minimal: built-in Lorentzian cavity, default output to ./results/
boltz-kernel run -s lorentzian

# Your own J(ω) from CSV, full multi-format export
boltz-kernel run --csv my_cavity.csv --omega0 5.0 \
                 --structured json --visual pdf --raw hdf5 \
                 --output ./results/

# Pipeline-friendly: JSON on stdout, exit code reflects validity
boltz-kernel run --csv my_J.csv --json --quiet
# exit 0 → Lindblad valid (max trace distance < 1%)
# exit 1 → Lindblad invalid  (publishable deviation)

# From stdin (chainable)
cat measured_J.csv | boltz-kernel run --stdin --json

# Custom formula
boltz-kernel run --formula "0.1 * w * np.exp(-w/10)" --g 0.3

# Interactive guided mode (opt-in; not the default)
boltz-kernel wizard

# Desktop GUI
boltz-kernel gui

# Persistent branding configuration
boltz-kernel branding set --institute "Your Lab Name" --logo ./lab_logo.png
```

---

## Theory in 3 Equations

**1. Generalised master equation:**
```
dρ/dt = -i [H, ρ(t)] + ∫₀ᵗ K(t, s) · D[ρ(s)] ds
```

**2. Boltzmann memory kernel (MaxEnt-Jaynes derivation):**
```
K*(t, s) = exp(-e(t, s) / T_eff) / Z(t)

where  e(t, s) = ∫ₛᵗ |C(τ - s)|² dτ    (accumulated correlation energy)
```

**3. Bath correlation from spectral density:**
```
C(τ) = g² · ∫₀∞ J(ω) · exp(-i (ω - ω₀) τ) dω
```

---

## Execution Channels

Six first-class ways to run BoltZ-Kernel, all sharing the same computational core:

| Channel  | Invocation                       | Use case                                                        |
|----------|----------------------------------|-----------------------------------------------------------------|
| CLI      | `boltz-kernel run ...`           | One comparison, scriptable, pipeline-ready                      |
| Batch    | `boltz-kernel batch run <yaml>`  | Parameter sweeps, classified outputs at scale                   |
| GUI      | `boltz-kernel gui`               | Interactive exploration, PyQt6 desktop app                      |
| Wizard   | `boltz-kernel wizard`            | Guided menus, preview before export (opt-in)                    |
| **MCP**  | `boltz-kernel mcp`               | **Model Context Protocol server** — LLM agents call the solver directly |
| Python   | `from boltz_kernel import ...`   | Custom analysis, notebooks, embedding                           |

Batch configs (YAML / TOML / JSON) support parameter sweeps, parallel workers, resume, dry-run, and four output-classification schemes (flat / by_parameter / by_spectral / by_run).

### MCP (Model Context Protocol) — agent-native access

BoltZ-Kernel ships an MCP server that exposes the solver tools directly to
any MCP-compatible LLM agent (Claude Desktop, Claude Code, Cursor,
Continue.dev, …). A researcher asks *"run BoltZ on my cavity J(ω)"* in
their editor and the agent invokes the local solver without leaving the
context.

```bash
pip install "boltz-kernel[mcp]"

# stdio transport (default — Claude Desktop / Code integration)
boltz-kernel mcp

# streamable HTTP on 127.0.0.1:7787 (browser-based agents, REST-ish)
boltz-kernel mcp --transport http --port 7787
```

Exposed tools:

| Tool                         | Purpose                                                           |
|------------------------------|-------------------------------------------------------------------|
| `boltz_run_comparison`       | NM vs Lindblad on a built-in J(ω), any backend                    |
| `boltz_prony_decompose`      | Matrix-Pencil exponential fit of C(τ), MaxEnt order option        |
| `boltz_backends_info`        | Backend capabilities metadata (so the agent can route wisely)     |
| `boltz_branding_show/set`    | Persistent branding read/update                                   |
| `boltz_version`              | Name, version, DOI, tool list                                     |

Example Claude Desktop config (`~/Library/Application Support/Claude/claude_desktop_config.json`
on macOS, `%APPDATA%\Claude\claude_desktop_config.json` on Windows):

```json
{
  "mcpServers": {
    "boltz-kernel": {
      "command": "boltz-kernel",
      "args": ["mcp"]
    }
  }
}
```

All computation runs **locally** in the BoltZ-Kernel Python process — no
data leaves the machine, no external network calls. The MCP server is a
thin wrapper around the same functions used by the CLI and Python API.

---

## Bring Your Own Data

### CSV File

Two columns — header row optional, separators: comma / tab / space:

```csv
omega,J
0.1,0.003
1.0,0.089
5.0,0.034
```

```bash
boltz-kernel run --csv my_data.csv
```

### Custom Formula

Any Python expression using `w` as the frequency variable; NumPy via `np`:

```bash
boltz-kernel run --formula "0.05**1.5 / np.sqrt(w - 5) if w > 5 else 0"
```

### Standard Input (pipeline)

```bash
curl https://data.mylab.example/J.csv | boltz-kernel run --stdin --json
```

### Python Callable

```python
from boltz_kernel import compare
import numpy as np

def my_J(w):
    return 0.1 * w * np.exp(-w / 10)

cmp = compare(my_J, g=0.3, T=0.05, omega0=1.0, t_max=50.0)
```

---

## Built-in Spectral Densities

| Name                | Formula                                                        | Environment                    |
|---------------------|----------------------------------------------------------------|--------------------------------|
| `ohmic`             | `η · ωˢ · exp(-ω / ωc)`                                        | Generic thermal bath           |
| `super_ohmic`       | `η · ω³ · exp(-ω / ωc)`                                        | 3-D phonon bath                |
| `lorentzian`        | `(γ / 2π) · Δ² / ((ω - ωc)² + Δ²)`                             | Single-mode cavity             |
| `band_edge`         | `β^{3/2} / √(ω - ωe)` for ω > ωe                               | Photonic crystal edge          |
| `photonic_crystal`  | Band edge + gap                                                | PhC with band gap              |
| `waveguide`         | `(Γ_1D / 2π) / (1 + r² - 2 r cos(ω · τ_rt))`                   | Waveguide QED with mirror      |

---

## Backend Selection

The bath correlation **C(τ) = g² ∫₀^∞ J(ω) exp(-i(ω-ω₀)τ) dω** is the most
expensive step in building a memory kernel. BoltZ-Kernel exposes several
backends for this integral via the `backend=` keyword of
`MemoryKernel.from_spectral_density` and `compare(...)`.

### Available backends

| Backend  | Status  | Complexity     | Best for                                        | Notes                                                                                  |
|----------|---------|----------------|-------------------------------------------------|----------------------------------------------------------------------------------------|
| `auto`   | default | —              | pick the best one for the problem               | Currently delegates to `fft`. Future versions will detect J structure and route to `prony` / `nufft` automatically. |
| `fft`    | stable  | O(N log N)     | any smooth J, fast-decaying tails               | Uniform FFT after resampling. Recommended default. Verified against analytical Lorentzian. |
| `quad`   | stable  | O(N·prefactor) | verification / reference                        | scipy.quad legacy path. Robust for smooth J on bounded support; fails to converge on oscillatory integrands at large τ (surfaces `IntegrationWarning`). Kept for comparison. |
| `prony`  | stable  | O(N·K), K≈1–16 | J with low-order exponential structure (Lorentzian, sum of Lorentzians) | Extracts `C(τ) = Σₖ αₖ exp(-βₖτ)` via Matrix Pencil + MaxEnt order selection, then routes `.solve()` through a TCL2 pseudomode ODE — **14–450× speed-up on `.solve()`**. Matches analytical TCL2 to machine precision. |
| `nufft`  | Phase C | O(N log N)     | J with singularities (band_edge, PhC gap)       | Non-uniform FFT handles sharp features without ringing. Defer to FFT for smooth J. |

### Measured speed-up

**`from_spectral_density` build time** (Lorentzian bath, Python 3.14,
single thread, 2024-grade laptop CPU, no GPU, no HPC):

| `t_max` | N    | `backend="quad"` | `backend="fft"` (default) | Speed-up  |
|---------|------|------------------|---------------------------|-----------|
| 50      | 250  | 1.79 s           | **0.011 s**               | **165×**  |
| 100     | 1000 | 8.75 s           | **0.027 s**               | **326×**  |
| 200     | 2000 | 19.85 s          | **0.076 s**               | **262×**  |

**`.solve()` wall time** (Prony + pseudomode replaces the integrodifferential
convolution with a K-dimensional ODE system):

| `t_max` | N    | `backend="fft"` + integrodiff | `backend="prony"` + pseudomode | Speed-up   |
|---------|------|-------------------------------|--------------------------------|------------|
| 50      | 250  | 0.042 s                       | **0.003 s**                    | **14×**    |
| 100     | 1000 | 0.455 s                       | **0.004 s**                    | **129×**   |
| 200     | 2000 | 1.76 s                        | **0.004 s**                    | **453×**   |

**Combined Phase A + B vs legacy v1.0** on a `t_max=200, N=2000` run:
*28 s → 0.08 s (build) + 0.004 s (solve) ≈ **340× total***.

*Translation for lab users:* a parameter sweep that would previously
have warranted a HPC queue submission now runs on a laptop in seconds.
This is a deliberate design goal — computational frugality is a
resource ethic, not a convenience.

### Picking a backend explicitly

```python
from boltz_kernel import MemoryKernel, SpectralDensities

J = SpectralDensities.lorentzian(gamma=0.1, wc=5.0, width=0.5)

# Default — fast FFT path
K = MemoryKernel.from_spectral_density(J, g=0.3, T=0.05, omega0=5.0, t_max=50)

# Explicit backend selection (verification mode)
K_quad = MemoryKernel.from_spectral_density(J, ..., backend="quad")
K_fft  = MemoryKernel.from_spectral_density(J, ..., backend="fft")

# Backend-specific tuning (advanced)
K = MemoryKernel.from_spectral_density(
    J, ...,
    backend="fft",
    n_freq=2**15,       # increase FFT resolution
    window="tukey",     # suppress edge ringing (e.g. band_edge)
    window_alpha=0.05,  # narrow taper to preserve signal
)

# Prony backend — pseudomode solver with MaxEnt order selection
K = MemoryKernel.from_spectral_density(
    J, ...,
    backend="prony",
    use_maxent_selector=True,       # Shannon-entropy-based K selection
    entropy_ratio_threshold=0.95,    # default
    # n_exp=4,                       # alternatively: fix K manually
)
# K._prony exposes the decomposition (alphas, betas, residual, ...)
# .solve() automatically dispatches to the pseudomode O(N·K) solver.
```

Via the CLI:

```bash
# Default FFT
boltz-kernel run -s lorentzian --t-max 100

# Prony + pseudomode with MaxEnt order selection
boltz-kernel run -s lorentzian --t-max 100 \
                 --backend prony --prony-maxent

# Prony with manually fixed order
boltz-kernel run -s lorentzian --t-max 100 \
                 --backend prony --prony-order 4
```

### Why FFT as the default, not quad

1. **Frugality.** 100-300× faster on typical workloads; labs without HPC access run the same comparisons on commodity hardware.
2. **Stability at large τ.** `scipy.quad` silently fails to converge on oscillatory integrands for large τ (now surfaced as `IntegrationWarning` — previously suppressed). The FFT does not rely on adaptive quadrature and stays stable across the full τ range.
3. **Verified correctness.** The FFT path passes an analytical Lorentzian test (exact: `C(τ) = g² γΔ/2 · exp(-Δτ) · exp(-i(ωc-ω₀)τ)`) to within ~5% relative error in the default configuration — well within typical experimental calibration uncertainties.
4. **Reversibility.** `backend="quad"` is preserved for any user who wants to validate a suspicious result against the legacy adaptive-quadrature path.

### MaxEnt order selection for Prony (novel)

When the `prony` backend is used without a manually fixed `n_exp`, the
number of exponentials K is selected automatically. BoltZ-Kernel offers
two criteria:

- **Variance-ratio** (default) — smallest K such that the top-K singular
  values of the Hankel pencil capture ≥ 99.9% of the total variance.
  Classical PCA-style truncation.
- **MaxEnt-ratio** (`use_maxent_selector=True`, or `--prony-maxent`) —
  smallest K such that the *Shannon entropy* of the top-K truncated
  weight distribution reaches ≥ 95% of the full-spectrum entropy.

The MaxEnt criterion is consistent with the Jaynes principle already
underpinning the MaxEnt kernel itself: among all truncations that fit
the data, the one whose coefficients carry maximum entropy is the least
biased. For a pure rank-1 signal the two criteria agree; they can diverge
when the residual carries genuine structure spread across many small
modes, a regime where variance-ratio tends to under-fit.

This order selector is not present in the standard Prony / Matrix Pencil
literature; it is contributed by BoltZ-Kernel. See
`boltz_kernel.core.prony.maxent_select_order` for the implementation and
its documentation string for the derivation.

---

## Output Formats

Three independent axes — every format first-class:

| Axis       | Formats                                         | Default |
|------------|-------------------------------------------------|---------|
| structured | `json` · `yaml` · `xml` · `jsonld` · `none`     | `json`  |
| visual     | `svg` · `pdf` · `png` · `tiff` · `eps` · `none` | `svg`   |
| raw        | `csv` · `hdf5` · `parquet` · `none`             | `csv`   |

The structured output follows a stable schema (schema_version, tool, run, input, output, metrics, artefacts) — parseable with `jq`, `yq`, `xmlstarlet`, or any language binding, and convertible between formats without loss.

---

## What the Results Tell You

| Metric                     | Value       | Interpretation                                                |
|----------------------------|-------------|---------------------------------------------------------------|
| Max trace distance         | `< 0.01`    | Lindblad is fine for your system. Stop worrying.              |
| Max trace distance         | `> 0.01`    | Lindblad is wrong. Solver shows by how much and where.        |
| Memory parameter P         | `< 0.1`     | Markovian regime                                              |
| Memory parameter P         | `> 1`       | Strongly non-Markovian                                        |
| Memory kernel shape        | Exponential | Memory from cavity coupling                                   |
| Memory kernel shape        | Power-law   | Memory from band edge                                         |
| Memory kernel shape        | Oscillatory | Memory from waveguide modes                                   |

Exit codes (for CI / pipelines):

| Code | Meaning                                               |
|------|-------------------------------------------------------|
| `0`  | Lindblad valid (trace distance < 1%)                  |
| `1`  | Lindblad invalid (publishable deviation detected)     |
| `2`  | Input error (malformed CSV, negative J, unknown name) |
| `3`  | Internal solver or output error                       |

---

## Python API

```python
import numpy as np
from boltz_kernel import compare, SpectralDensities, MemoryKernel

# Built-in environment
J = SpectralDensities.lorentzian(gamma=0.1, wc=5.0, width=0.5)

# Or your own callable
# J = lambda w: 0.1 * w * np.exp(-w / 10)

cmp = compare(J, g=0.3, T=0.05, omega0=1.0, t_max=50.0)

print(cmp.regime)                     # "Weakly non-Markovian"
print(cmp.max_deviation)              # 0.087
print(cmp.kernel.non_markovianity())  # 0.42 (P)
print(cmp.kernel.memory_spread())     # σ_K

# Direct kernel construction
K = MemoryKernel.from_spectral_density(J, g=0.3, T=0.05, omega0=1.0)
result = K.solve(rho0=np.array([0.0, 0.0, 1.0]),
                  tspan=np.linspace(0, 50, 250))

# Publication-ready plot with your institute's branding
cmp.plot(save="figure.pdf")
```

---

## Branding

Researchers can put their institute name, subtitle, reference line, logo, and footer text on every generated figure — while BoltZ-Kernel provenance is preserved invisibly in the file metadata (Author / Software / Description fields of PNG, PDF, TIFF).

```bash
# Per-run override (no persistent changes)
boltz-kernel run -s lorentzian \
  --institute "Laboratoire X" \
  --subtitle  "Coherence study — Sample A12" \
  --reference "arXiv:2601.XXXXX" \
  --logo      ~/lab_x_logo.png \
  --footer    "Produced 2026-04-19 · author@labx.edu"

# Persistent configuration (stored in ~/.boltz-kernel/branding.json)
boltz-kernel branding set --institute "Laboratoire X" --logo ~/lab_x_logo.png
boltz-kernel branding show
boltz-kernel branding reset
```

---

## Known Limitations

### 1. Weak-Coupling Regime Only

The energy functional `e(t, s)` is computed using a mean-field factorisation `ρ_SE ≈ ρ_S ⊗ ρ_E`, valid at order `g ≪ ω₀`. At strong coupling (`g > 1`), the factorisation breaks and the solver's predictions become unreliable. **This is a stated domain of validity, not a bug.**

### 2. Boltzmann Kernel Is True by Construction (MaxEnt-derived)

The kernel `K*(t, s)` is the least-biased distribution consistent with the bath correlations. You cannot falsify MaxEnt itself — it is an inference principle (Jaynes 1957), not an empirical claim. What you **can** falsify is whether nature's memory kernel matches the MaxEnt prediction for a specific J(ω). If your measured decay curve disagrees with the solver's output, the MaxEnt kernel is wrong for that environment — and **that is a publishable result.**

### 3. Two-Level System (v1.1)

The current implementation tracks the Bloch vector (x, y, z) of a qubit. Generalisation to qudits (d > 2) via Liouville-space vectorisation is planned for v1.2. Multi-emitter (collective-bath) support is planned for v1.3.

### 4. No Experimental Data Included

BoltZ-Kernel is a theoretical diagnostic tool. It predicts what non-Markovian dynamics should look like given J(ω). Comparing its predictions with actual lab measurements is the researcher's job — and the comparison is what closes the scientific loop.

---

## Theoretical companion

The mathematical derivations underlying every backend, decomposition,
and order-selection criterion are in [`doc/THEORY.md`](./doc/THEORY.md).
The companion is the formal counterpart to the software: derivations
for the FFT convergence on Lorentzian baths, the Matrix-Pencil "U vs V"
subtlety, the **MaxEnt Prony order selector** (claimed novel
contribution), the TCL2 pseudomode reduction, and the documented
divergence zones between backends — all cross-referenced to the
corresponding source files and tests.

Reading the companion before running the tool is the recommended path
for a reviewer or experimentalist who wants to verify what the software
does and why.

---

## Citation

<div align="center">

**DESVAUX G.J.Y.** (2026). *BoltZ-Kernel: Non-Markovian Quantum Dynamics Solver with Boltzmann Memory Kernel.* Hope 'n Mind SASU - Research.

[![DOI](https://img.shields.io/badge/DOI-10.5281%2Fzenodo.19648837-c9a84c?style=flat-square&logo=doi&logoColor=white)](https://doi.org/10.5281/zenodo.19648837)
[![ORCID](https://img.shields.io/badge/ORCID-0009--0008--9813--4627-a6794e?style=flat-square&logo=orcid&logoColor=white)](https://orcid.org/0009-0008-9813-4627)

</div>

BibTeX:
```bibtex
@software{desvaux_boltz_kernel_2026,
  author       = {DESVAUX, G.J.Y.},
  title        = {BoltZ-Kernel: Non-Markovian Quantum Dynamics Solver
                  with Boltzmann Memory Kernel},
  year         = {2026},
  publisher    = {Hope 'n Mind SASU - Research},
  version      = {1.1.0},
  doi          = {10.5281/zenodo.19648837},
  url          = {https://github.com/hopenmind/hopenmind-suite},
}
```

---

## License

**Dual-licensed** — pick the option that matches your use:

- **Academic / non-commercial use** → [Apache License 2.0](./LICENSE) — cite the DOI and you're done. No request required.
- **Commercial use** → Proprietary licence. Contact [contact@hopenmind.com](mailto:contact@hopenmind.com) for terms.

See [LICENSE](./LICENSE) for full legal text and the guidance section at the bottom of the file.

---

<div align="center">

*Built on the Maximum Entropy principle — because nature's memory deserves the least-biased representation.*

</div>
