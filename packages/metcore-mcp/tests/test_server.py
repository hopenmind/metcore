"""End-to-end smoke tests for the unified Hope 'n Mind MCP server."""
import numpy as np
from metcore_mcp import server as S


def test_server_object_and_registration():
    assert S.mcp.name == "metcore"
    info = S.suite_info()
    assert info["version"] == "0.1.0"
    assert info["engines"]["memkern"]["available"] is True
    assert info["engines"]["obliquity_ng"]["available"] is True
    assert "prony_decompose" in info["live_tools"]


def test_prony_decompose_recovers_two_modes():
    # C(τ) = 2 e^{-0.5τ} + 1 e^{-2τ}  → Prony must find K=2 with tiny error
    tau = np.linspace(0, 10, 256)
    c = 2.0 * np.exp(-0.5 * tau) + 1.0 * np.exp(-2.0 * tau)
    out = S.prony_decompose(tau.tolist(), c.tolist(), n_exp=2)
    assert "error" not in out, out
    assert out["n_exp"] == 2
    assert out["rms_reconstruction_error"] < 1e-6


def test_prony_auto_order():
    tau = np.linspace(0, 8, 200)
    c = np.exp(-0.7 * tau)
    out = S.prony_decompose(tau.tolist(), c.tolist())  # auto K
    assert "error" not in out and out["n_exp"] >= 1


def test_maxent_select_order():
    out = S.maxent_select_order([10.0, 9.0, 0.01, 0.001])
    assert "error" not in out
    assert out["selected_order"] >= 1
    assert out["effective_number_of_modes"] > 0


def test_ng_revival_positive_dephasing_zero():
    rev = S.nonmarkovianity_ng(channel="revival", gamma=0.1, omega=2.0,
                               t_max=12.0, n_points=2048)
    deph = S.nonmarkovianity_ng(channel="dephasing", gamma=0.5,
                                t_max=8.0, n_points=512)
    assert "error" not in rev and "error" not in deph
    assert rev["N_G"] > 1e-2, rev
    assert deph["N_G"] < 1e-4, deph
    assert rev["verdict"].startswith("non-Markovian")
    assert deph["verdict"].startswith("Markovian")


def test_unknown_channel_is_graceful():
    out = S.nonmarkovianity_ng(channel="bogus")
    assert "error" in out
