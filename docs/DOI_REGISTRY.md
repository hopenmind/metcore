# DOI Registry — Hope 'n Mind Scientific Suite

**Policy: divisionnaire.** The suite is cited at three granularity
levels, each with its own Digital Object Identifier on Zenodo:

1. **Suite** — umbrella DOI, cited when referring to the project as a whole.
2. **Module** — one DOI per `packages/<name>/` or top-level package.
3. **Atomic contribution** — one DOI per distinct novel function,
   equation, theorem, or algorithm that originates in an HNM framework.
   A different expression of the same underlying object (different
   parametrisation, different domain adaptation, different numerical
   scheme) **earns its own DOI** once it is public.

The policy exists to make scientific priority fine-grained and
traceable: reviewers and downstream users can point at the exact
atomic contribution they are building on, and appropriation at any
granularity can be addressed with a specific citation.

---

## Level 1 — Suite

| Item | Location | DOI | Status |
|------|----------|-----|--------|
| Hope 'n Mind Scientific Suite | `/` | [10.5281/zenodo.19486927](https://doi.org/10.5281/zenodo.19486927) | active |

## Level 2 — Modules

| Item | Location | DOI | Status |
|------|----------|-----|--------|
| BoltZ-Kernel (non-Markovian quantum solver) | `packages/boltz-kernel/` | [10.5281/zenodo.19648837](https://doi.org/10.5281/zenodo.19648837) | active (v1.1.0) |
| memkern (domain-agnostic memory-kernel engine) | `packages/memkern/` | *pending — to mint with 0.1.0 release* | reserved |
| memkern-rheology (Maxwell-Wiechert adapter) | `packages/memkern-rheology/` | *pending* | reserved |
| obliquity-ng (geometric non-Markovianity measure, §3.6 Eq. 26) | `packages/obliquity-ng/` | *pending* | reserved |
| eternal-nm-sim (Hall 2014 Pauli channel + BLP) | `packages/eternal-nm-sim/` | *pending* | reserved |
| hpc-triage (Problem/Verdict/cascade abstraction) | `packages/hpc-triage/` | *pending* | reserved |
| kernel-audit (pre-flight J(ω) tier estimator) | `packages/kernel-audit/` | *pending* | reserved |
| memkern-ladder (3-level NZ approximation ladder) | `packages/memkern-ladder/` | *pending* | reserved |
| hpc-oracle (cost & RAM oracle) | `packages/hpc-oracle/` | *pending* | reserved |
| bench-extrap (scaling-law extrapolator) | `packages/bench-extrap/` | *pending* | reserved |
| local-dispatcher (local CPU/GPU/RAM parallelism) | `packages/local-dispatcher/` | *pending* | reserved |
| hpc-manifest (SLURM/PBS/LSF script generator) | `packages/hpc-manifest/` | *pending* | reserved |
| hopenmind-export (7-format academic export + branding) | `packages/hopenmind-export/` | *pending* | reserved |
| hopenmind-cli (unified CLI with auto-install) | `packages/hopenmind-cli/` | *pending* | reserved |
| hopenmind-gui (PyQt6 unified desktop app, PyInstaller-ready) | `packages/hopenmind-gui/` | *pending* | reserved |
| hopenmind-mcp (unified MCP aggregator + auto-config) | `packages/hopenmind-mcp/` | *pending* | reserved |
| hopenmind (brand meta-package) | `packages/hopenmind/` | *not needed — pure redirect* | n/a |

## Level 3 — Atomic contributions

Each row here marks a distinct novel contribution that originates in
this suite. A contribution moves from *pending* to *active* once its
Zenodo record is created and the DOI populated in the docstring of
the corresponding code.

| Contribution | Parent module | Location | DOI | Status |
|--------------|---------------|----------|-----|--------|
| **`maxent_select_order`** — MaxEnt-based Prony order selector via Shannon entropy of the Hankel pencil spectrum. | memkern | `memkern.prony` | *pending* | reserved |
| **Boltzmann Memory Kernel** `K*(t,s) ∝ exp(-E(t,s)/T_eff)` — Jaynes MaxEnt-derived closed-form kernel for bath correlation. | boltz-kernel | `boltz_kernel.core.kernel` | *pending* | reserved |
| **Geometric non-Markovianity measure `N_G`** — Liouville-space simplex-volume integral, §3.6 Eq. 26, tetrahedron-optimal for qubits. | obliquity-ng | `obliquity_ng.measure` | *pending* | reserved (implemented) |
| **Hall 2026 reconstruction** — reproducible Pauli channel γ_x=γ_y=1, γ_z=-tanh(t) with BLP ≈ 0, N_G ≈ 0 side-by-side diagnostic. | eternal-nm-sim | `eternal_nm_sim.core` | *pending* | reserved (implemented) |
| **`Problem / Verdict / cascade` triage abstraction** — unified contract for HPC-triage tools. | hpc-triage | `hpc_triage.core` | *pending* | reserved (implemented) |
| **3-level NZ approximation ladder** with convergence stop — Markov / Born-Markov(1) / Prony-pseudomode. | memkern-ladder | `memkern_ladder.tool` | *pending* | reserved (implemented) |
| Planned: **GKSL-Projector** (SDP-based Lindblad-distance, H6 of the NZ-falsifiable paper). | gksl-projector *(package not yet created)* | — | *pending* | planned |
| Planned: **EnsembleNM decomposition** (local + bath-mediated + system-mediated split, §6 of the NZ-falsifiable paper). | ensemble-nm *(package not yet created)* | — | *pending* | planned |
| Planned: **NZ → HEOM explicit derivation** via Matsubara — unifies Breuer & Tanimura. | — *(theoretical note)* | — | *pending* | planned |
| Planned: **NZ → Smoluchowski classical limit** — fractional-diffusion with microscopic provenance. | — *(theoretical note)* | — | *pending* | planned |
| Planned: **Operator-valued-memory Lindblad + CPTP conditions**. | — *(theoretical note)* | — | *pending* | planned |
| Planned: **Kuramoto with memory + N_G phase diagram** — classical-system bridge for N_G. | kuramoto-mem *(package not yet created)* | — | *pending* | planned |
| Planned: **FalsifyKit** (generic falsifiable-hypothesis runner with ternary verdict). | falsify-kit *(package not yet created)* | — | *pending* | planned |

---

## How to add an entry

1. Publish the code and a minimal prose description (docstring +
   README section + CHANGELOG entry).
2. Create the Zenodo record with the matching title, abstract, and
   authorship. Link it as a *child* of the suite DOI via Zenodo's
   related-identifier field (`is part of`).
3. Fill the DOI in the table above **and** in the docstring of the
   code object (convention: `DOI: 10.5281/zenodo.NNNNNN` under the
   SPDX line).
4. Commit the update with message `doi(<module>): <item> →
   10.5281/zenodo.NNNNNN`.

## How to cite at the right granularity

- Using the suite as a tool — cite the **suite DOI**.
- Using one module — cite **module DOI** + suite DOI.
- Building on a specific novel function / equation — cite **atomic
  DOI** + module DOI + suite DOI. Give credit at every level.
