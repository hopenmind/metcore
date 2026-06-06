"""
Analytical reference tests — verify the solver against known exact results.

These tests protect against regressions and give reviewers a concrete proof
that the numerical core reproduces standard analytical benchmarks:

  1. Markov limit: in the van Hove limit (tau_c → 0), Non-Markovian dynamics
     reduces to exponential Lindblad decay of the excited-state population.

  2. Trace preservation: Tr(ρ) = 1 is preserved by both solvers at all times.

  3. Bloch-vector bound: ||(x,y,z)|| ≤ 1 at all times.

  4. Lindblad analytical form: P_e(t) = P_e(0) · exp(-γ t) exactly for
     the Markovian solver (this checks the comparison baseline, not BoltZ itself).

SPDX-License-Identifier: Apache-2.0 OR LicenseRef-BoltZ-Commercial
"""

import numpy as np
import pytest


# ── Fixtures ───────────────────────────────────────────────────────────────────

@pytest.fixture
def narrow_ohmic():
    """Ohmic bath with very short correlation time (Markovian regime)."""
    from boltz_kernel import SpectralDensities
    return SpectralDensities.ohmic(eta=0.01, wc=50.0, s=1)


@pytest.fixture
def lorentzian_cavity():
    """Narrow Lorentzian — textbook structured environment."""
    from boltz_kernel import SpectralDensities
    return SpectralDensities.lorentzian(gamma=0.1, wc=5.0, width=0.5)


# ── Tests ──────────────────────────────────────────────────────────────────────

@pytest.mark.analytical
def test_backends_agree_in_convergent_regime():
    """quad and fft backends must agree at short τ (where quad converges).

    At large τ, quad fails to converge on the oscillatory integrand
    (documented IntegrationWarning); the FFT stays stable. The test
    restricts the comparison to τ < t_max/3 where quad is reliable.
    """
    from boltz_kernel import MemoryKernel, SpectralDensities

    J = SpectralDensities.lorentzian(gamma=0.1, wc=5.0, width=0.5)
    params = dict(g=0.3, T=0.05, omega0=5.0, t_max=30.0, dt=0.2)

    K_quad = MemoryKernel.from_spectral_density(J, backend="quad", **params)
    K_fft  = MemoryKernel.from_spectral_density(J, backend="fft",  **params)

    # Compare in the regime where quad is expected to converge
    tau_test = np.linspace(0.5, params["t_max"] / 3.0, 20)
    C_q = np.array([K_quad.C_func(t) for t in tau_test])
    C_f = np.array([K_fft.C_func(t)  for t in tau_test])

    scale = float(np.max(np.abs(C_q)))
    assert scale > 0, "Quad baseline produced zero correlation — test setup issue."

    # 5% relative tolerance — FFT truncation + interp + quad residual error
    np.testing.assert_allclose(
        C_q.real, C_f.real, atol=0.05 * scale,
        err_msg="quad and fft backends disagree on Re C(τ) at short τ",
    )
    np.testing.assert_allclose(
        C_q.imag, C_f.imag, atol=0.05 * scale,
        err_msg="quad and fft backends disagree on Im C(τ) at short τ",
    )


@pytest.mark.analytical
def test_unknown_backend_raises():
    """Requesting a non-existent backend gives a clear error."""
    from boltz_kernel import MemoryKernel, SpectralDensities

    J = SpectralDensities.lorentzian()
    with pytest.raises(ValueError, match="Unknown backend"):
        MemoryKernel.from_spectral_density(J, backend="bogus")


@pytest.mark.analytical
def test_nufft_backend_not_yet_implemented():
    """NUFFT backend is Phase C — must raise informative NotImplementedError."""
    from boltz_kernel import MemoryKernel, SpectralDensities

    J = SpectralDensities.lorentzian()
    with pytest.raises(NotImplementedError, match="Phase"):
        MemoryKernel.from_spectral_density(J, backend="nufft")


@pytest.mark.analytical
def test_prony_backend_builds_decomposition():
    """backend='prony' attaches a PronyResult; .solve() uses pseudomode path."""
    from boltz_kernel import MemoryKernel, SpectralDensities

    J = SpectralDensities.lorentzian(gamma=0.1, wc=10.0, width=0.5)
    K = MemoryKernel.from_spectral_density(
        J, g=0.3, T=0.1, omega0=10.0, t_max=20.0, dt=0.1,
        backend="prony",
    )
    # A Prony decomposition must be attached
    assert K._prony is not None
    assert K._prony.n_exp >= 1
    # For a single Lorentzian at zero detuning, Prony must capture
    # essentially all the variance. The residual is not machine-epsilon
    # because the FFT-reconstructed C(τ) itself carries truncation
    # ringing (Prony fits what FFT produced, not the analytical ideal).
    assert K._prony.variance_explained > 0.999, (
        f"Prony variance_explained too low: {K._prony.variance_explained:.6f}"
    )
    # Recovered beta should be near width=0.5 (real), imaginary part tiny
    beta_main = K._prony.betas[np.argmax(np.abs(K._prony.alphas))]
    assert abs(beta_main.real - 0.5) < 0.01, (
        f"Recovered β.real = {beta_main.real:.4f}, expected ~0.5"
    )
    assert abs(beta_main.imag) < 0.01, (
        f"Recovered β.imag = {beta_main.imag:.4f}, expected ~0 (zero detuning)"
    )


@pytest.mark.analytical
def test_prony_backend_solve_dispatches_to_pseudomode():
    """Calling .solve() on a prony-backed kernel uses the pseudomode solver
    and returns a physical Bloch trajectory starting at the given state."""
    from boltz_kernel import MemoryKernel, SpectralDensities

    J = SpectralDensities.lorentzian(gamma=0.1, wc=10.0, width=0.5)
    K = MemoryKernel.from_spectral_density(
        J, g=0.3, T=0.1, omega0=10.0, t_max=20.0, dt=0.1,
        backend="prony",
    )
    rho0 = np.array([0.0, 0.0, 1.0])  # |e⟩
    tspan = np.linspace(0, 20, 50)
    result = K.solve(rho0, tspan)

    # Initial condition preserved
    np.testing.assert_allclose(result.bloch[0], rho0, atol=1e-10)
    # Final population stays in [0, 1]
    pop_final = (1 + result.bloch[-1, 2]) / 2
    assert 0.0 <= pop_final <= 1.0 + 1e-9
    # Some decay must have occurred (the coupling is non-zero)
    assert pop_final < 0.999, "No population decay — solver may be inert"


@pytest.mark.analytical
def test_fft_bath_correlation_matches_lorentzian_analytical():
    """FFT C(τ) matches the analytical Lorentzian result in the wide-band limit.

    For J(ω) = (γ/2π) Δ² / ((ω-ωc)² + Δ²) with ωc ≫ Δ (so negative-ω
    contribution is negligible), the exact correlation is

        C(τ) = g² · γΔ/2 · exp(-Δ|τ|) · exp(-i (ωc - ω₀) τ).

    Here we pick ωc == ω₀ so the imaginary part vanishes and the real
    part is a pure exponential decay with rate Δ and amplitude g²γΔ/2.
    """
    from boltz_kernel import MemoryKernel, SpectralDensities

    g, gamma, wc, width, omega0 = 0.3, 0.1, 10.0, 0.5, 10.0
    J = SpectralDensities.lorentzian(gamma=gamma, wc=wc, width=width)

    K = MemoryKernel.from_spectral_density(
        J, g=g, T=0.1, omega0=omega0, t_max=20.0, dt=0.05
    )

    tau = np.linspace(0.5, 10.0, 25)
    amplitude = g**2 * gamma * width / 2.0
    expected_real = amplitude * np.exp(-width * tau)

    C_computed = np.array([K.C_func(t) for t in tau])

    # 10% relative tolerance: FFT discretisation + window taper + cubic interp
    np.testing.assert_allclose(
        C_computed.real, expected_real,
        rtol=0.10, atol=0.05 * amplitude,
        err_msg="FFT bath correlation diverges from analytical Lorentzian decay",
    )
    # Imaginary part should be near zero at zero detuning (ωc == ω₀)
    np.testing.assert_allclose(
        C_computed.imag, np.zeros_like(tau),
        atol=0.10 * amplitude,
        err_msg="FFT bath correlation spurious imaginary part at zero detuning",
    )


@pytest.mark.analytical
def test_lindblad_exponential_decay(narrow_ohmic):
    """Markovian solver: excited-state population decays as exp(-γt) exactly."""
    from boltz_kernel import LindbladSolver

    L = LindbladSolver.from_spectral_density(narrow_ohmic, g=0.1, omega0=1.0)
    tspan = np.linspace(0, 10, 50)
    rho0 = np.array([0.0, 0.0, 1.0])  # excited
    res = L.solve(rho0, tspan)

    # P_e(t) = (1 + z(t)) / 2 with z(t) = -1 + 2 exp(-γ t)
    expected = np.exp(-L.gamma * tspan)
    np.testing.assert_allclose(res.populations, expected, rtol=1e-10, atol=1e-12)


@pytest.mark.analytical
def test_markov_limit_small_correlation_time(narrow_ohmic):
    """In the Markov limit, NM and Lindblad should agree within <5%."""
    from boltz_kernel import compare

    cmp = compare(narrow_ohmic, g=0.05, T=0.01, omega0=1.0, t_max=20.0, dt=0.2)
    assert cmp.max_deviation < 0.05, (
        f"Markov-limit deviation {cmp.max_deviation:.3f} exceeds 5% — "
        f"NM solver is not recovering Lindblad in the weak, short-correlation regime."
    )


@pytest.mark.analytical
def test_bloch_vector_bounded(lorentzian_cavity):
    """||(x,y,z)|| ≤ 1 at all times for both solvers (CPTP invariant)."""
    from boltz_kernel import compare

    cmp = compare(lorentzian_cavity, g=0.3, T=0.1, t_max=30.0, dt=0.2)

    for name, result in (("NM", cmp.nm), ("Lindblad", cmp.markov)):
        norms = np.sqrt(result.x ** 2 + result.y ** 2 + result.z ** 2)
        # small numerical slack; the clamping in kernel.solve caps at 1.0
        assert np.all(norms <= 1.0 + 1e-9), (
            f"{name} solver violates Bloch-sphere bound: max norm = {norms.max():.6f}"
        )


@pytest.mark.analytical
def test_population_physical_range(lorentzian_cavity):
    """Excited-state population must stay in [0, 1] for both solvers."""
    from boltz_kernel import compare

    cmp = compare(lorentzian_cavity, g=0.3, T=0.1, t_max=30.0, dt=0.2)
    for name, result in (("NM", cmp.nm), ("Lindblad", cmp.markov)):
        pops = result.populations
        assert np.all(pops >= -1e-9), f"{name}: negative population detected"
        assert np.all(pops <= 1.0 + 1e-9), f"{name}: population > 1 detected"


@pytest.mark.analytical
@pytest.mark.parametrize(
    "fixture_name, g, T",
    [
        ("narrow_ohmic",      0.05, 0.01),
        ("narrow_ohmic",      0.20, 0.01),
        ("lorentzian_cavity", 0.30, 0.05),
        ("lorentzian_cavity", 0.50, 0.05),
    ],
)
def test_regime_label_matches_P(request, fixture_name, g, T):
    """Regime label must be consistent with the numerical P value.

    This is the true invariant: we do not know in advance which regime each
    (fixture, g, T) combination yields — but whatever P the kernel computes,
    the human-readable label must map to it via the documented thresholds
    (0.1, 1.0).
    """
    from boltz_kernel import compare

    J = request.getfixturevalue(fixture_name)
    cmp = compare(J, g=g, T=T, t_max=30.0, dt=0.2)
    P = cmp.kernel.non_markovianity()

    if P < 0.1:
        expected = "Markovian"
    elif P < 1.0:
        expected = "Weakly non-Markovian"
    else:
        expected = "Strongly non-Markovian"

    assert cmp.regime == expected, (
        f"Inconsistent label: P = {P:.4f} → expected '{expected}', "
        f"got '{cmp.regime}' (fixture={fixture_name}, g={g}, T={T})"
    )
