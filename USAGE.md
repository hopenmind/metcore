# Hope 'n Mind Scientific Suite - Usage Guide

One engine (the Markov Embedding Theorem), several ways to use it: a Python API,
an MCP server for any LLM client, and a desktop GUI with one tab per scientific
specialty. This guide is the quickstart for all three.

## Install

```bash
pip install metcore          # core engines + MCP server
pip install boltz-kernel             # optional: extra open-quantum-systems tools
# or, from the workspace checkout:
uv sync --all-packages
```

## The 60-second tour: diagnose any memory kernel

The single most useful entry point is `full_diagnosis`. Hand it a measured
correlation C(tau) and it runs the whole pipeline: is the kernel embeddable,
what is the embedding order K, is the dynamics CP-divisible, and how wrong is
the Lindblad approximation.

```python
import numpy as np
from memkern import full_diagnosis, zoo

k = zoo.get_kernel("underdamped")          # a canonical oscillating bath
tau = np.linspace(0, 25, 800)
report = full_diagnosis(tau, k.C(tau), t_max=25)
print(report["summary"])
# MET applies (regime=rational-embeddable, K=2). Dynamics is NOT CP-divisible ...
```

## Python API: the building blocks

```python
from memkern import (
    embeddability_report,   # is the MET even applicable to this kernel?
    prony_decompose,        # compile C(tau) into exponential modes
    cptp_certify,           # CP-divisibility (scalar matrix-Bernstein)
    lindblad_gap,           # how far the Lindblad approximation drifts
    full_diagnosis,         # all of the above, in one call
    zoo,                    # canonical benchmark kernels
)
from memkern.adapters import quantum_kernel, neural_kernel
```

Quick examples:

```python
# 1. Embeddability gate (run this before trusting any finite-K result)
rep = embeddability_report(tau, C)
print(rep["regime"], rep["K_est"], rep["advice"])

# 2. Quantum domain: spectral density J(omega) -> bath correlation C(tau)
tau, C = quantum_kernel("drude", T=0.2, lam=1.0, gamma=1.0)

# 3. Neural domain: synaptic rise/decay -> retarded memory kernel
t, K = neural_kernel(tau_rise=0.3, tau_decay=3.0)
```

## MCP server: drive the suite from any LLM

The unified server exposes nine tools to any MCP client (Claude Desktop, Cursor,
VS Code, local LLM front-ends, ...). One command wires it everywhere:

```bash
metcore-mcp configure            # auto-detect and configure installed clients
metcore-mcp serve                # run the server (stdio)
metcore-mcp serve --transport http --port 8787   # for local/remote HTTP clients
```

Tools available to the model:

```text
suite_info            list live engines and versions (call this first)
kernel_embeddability  is the MET applicable to this kernel?
prony_decompose       compile C(tau) into exponential modes
maxent_select_order   choose the Prony order K from a singular spectrum
nonmarkovianity_ng    geometric non-Markovianity N_G of a qubit channel
cptp_certify          CP-divisibility / Lindblad admissibility
lindblad_gap          how wrong is the Lindblad approximation here?
full_diagnosis        the whole pipeline in one call
kernel_zoo            list or sample canonical benchmark kernels
```

Full client-by-client setup is in `MCP_DEPLOYMENT.md`.

## Desktop GUI: one tab per specialty

```bash
metcore-gui
```

The window groups tools by scientific domain, each speaking its own native input
and feeding the same MET engine:

```text
Quantum               spectral density J(omega) -> C(tau) -> diagnosis
Classical & Rheology  relaxation modulus G(t) -> Maxwell-Wiechert (Prony) spectrum
Neural                synaptic kernel K(t) -> diagnosis
Diagnostics           N_G / obliquity, Lindblad-gap, embeddability (cross-domain)
```

Every panel computes, plots, and exports a branded figure (logo, institute,
header, footer) in seven academic formats. Set your branding once via the
"Branding" dialog; it is saved to `~/.metcore/branding.json` and reused
everywhere.

## The kernel zoo

A reference library of canonical kernels with their analytic Prony form and a
domain tag, handy for benchmarking and teaching:

```python
from memkern import zoo
zoo.list_zoo()                       # drude, underdamped, maxwell_wiechert, subohmic
k = zoo.get_kernel("maxwell_wiechert", moduli=(1.0, 0.5), times=(0.5, 3.0))
```

## License

Dual-licensed: Apache-2.0 OR LicenseRef-HopenMind-Commercial. Pick the one that
matches your use.
