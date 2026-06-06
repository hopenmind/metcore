"""
MCP server smoke tests — verify tools are registered, callable, and
return JSON-serialisable dicts.

We do NOT spin up the transport (stdio/HTTP); we call the wrapped
Python functions directly — that exercises all the solver wiring
while staying independent of the MCP protocol layer.

SPDX-License-Identifier: Apache-2.0 OR LicenseRef-BoltZ-Commercial
"""

import json

import pytest


@pytest.fixture
def mcp_server():
    from boltz_kernel.mcp import server as mcp_module
    return mcp_module


def test_mcp_module_imports(mcp_server):
    """MCP server module must import without side effects."""
    assert hasattr(mcp_server, "mcp")
    assert hasattr(mcp_server, "launch")


def test_mcp_version_tool(mcp_server):
    """boltz_version returns name, version, doi, tools list."""
    result = mcp_server.boltz_version()
    assert result["name"] == "BoltZ-Kernel"
    assert "version" in result and result["version"]
    assert "doi" in result and result["doi"]
    assert isinstance(result["mcp_tools"], list)
    assert len(result["mcp_tools"]) >= 5


def test_mcp_backends_info(mcp_server):
    """boltz_backends_info describes all 5 backends."""
    info = mcp_server.boltz_backends_info()
    for backend in ("auto", "fft", "quad", "prony", "nufft"):
        assert backend in info, f"Missing backend: {backend}"


def test_mcp_prony_decompose(mcp_server):
    """boltz_prony_decompose fits a single-exponential signal exactly."""
    import numpy as np

    alpha_true, beta_true = 1.5 + 0.2j, 0.3 + 0.7j
    tau = np.linspace(0, 15, 300)
    C = alpha_true * np.exp(-beta_true * tau)

    result = mcp_server.boltz_prony_decompose(
        tau=tau.tolist(),
        C_real=C.real.tolist(),
        C_imag=C.imag.tolist(),
        n_exp=1,
    )
    assert result["n_exp"] == 1
    assert result["variance_explained"] > 0.999
    # Result must be JSON-serialisable (pure Python primitives)
    json.dumps(result)


def test_mcp_prony_maxent_selector(mcp_server):
    """boltz_prony_decompose with use_maxent_selector=True picks a sensible K."""
    import numpy as np

    # A clean K=2 signal
    tau = np.linspace(0, 15, 300)
    C = 1.0 * np.exp(-(0.3 + 1.0j) * tau) + 0.5 * np.exp(-(0.7 - 0.4j) * tau)

    result = mcp_server.boltz_prony_decompose(
        tau=tau.tolist(),
        C_real=C.real.tolist(),
        C_imag=C.imag.tolist(),
        use_maxent_selector=True,
    )
    assert result["n_exp"] >= 1
    assert result["selection_criterion"] == "maxent"
    assert result["variance_explained"] > 0.99


def test_mcp_run_comparison_roundtrip(mcp_server, tmp_path):
    """boltz_run_comparison produces the full CLI-equivalent artefact set
    (structured JSON + visual SVG + raw CSV) and returns their paths."""
    result = mcp_server.boltz_run_comparison(
        spectral="lorentzian",
        omega0=5.0, g=0.3, t_max=20.0, dt=0.2,
        backend="fft",
        output_dir=str(tmp_path),
    )
    # Summary metrics
    assert "regime_kernel" in result
    assert "P_memory" in result
    assert "max_trace_distance" in result
    assert "lindblad_valid" in result
    # Artefact list (same shape as CLI output_writers)
    assert "artifacts" in result
    assert isinstance(result["artifacts"], list)
    artifact_types = {a["type"] for a in result["artifacts"]}
    assert "json" in artifact_types, f"Missing JSON artefact: {artifact_types}"

    # JSON artefact must exist on disk and be valid
    json_files = [a for a in result["artifacts"] if a["type"] == "json"]
    assert json_files, "No JSON artefact in result"
    written = json.loads(open(json_files[0]["path"], encoding="utf-8").read())
    assert written["tool"]["name"] == "BoltZ-Kernel"


def test_mcp_run_comparison_prony_backend(mcp_server, tmp_path):
    """backend='prony' through MCP exposes the Prony decomposition.

    The decomposition lives at result['output']['prony'] (full schema)
    or under a flattened 'prony' key (depending on the response shape
    chosen by the server). Accept either to keep the test robust to
    minor response-layout changes.
    """
    result = mcp_server.boltz_run_comparison(
        spectral="lorentzian",
        omega0=10.0, g=0.3, t_max=20.0, dt=0.1,
        wc=10.0, width=0.5,
        backend="prony", prony_maxent=True,
        output_dir=str(tmp_path),
    )
    # Prony block is exposed somewhere in the response
    prony = (
        result.get("prony")
        or result.get("output", {}).get("prony")
    )
    assert prony is not None, f"No prony block in MCP response: {list(result)}"
    assert prony["n_exp"] >= 1
    assert prony["variance_explained"] > 0.99


def test_mcp_branding_show_returns_defaults(mcp_server):
    """boltz_branding_show returns a dict with all branding fields."""
    result = mcp_server.boltz_branding_show()
    for key in (
        "institute_name", "subtitle", "reference",
        "logo_path", "logo_position", "footer_text",
    ):
        assert key in result
