"""
BoltZ-Kernel command-line interface.

Subcommands:
    run         Single comparison (NM vs Lindblad) with full format output
    wizard      Interactive guided session (opt-in)
    gui         Launch PyQt6 GUI
    batch       Run a batch pipeline from a YAML config
    bench       Run a reference benchmark case
    branding    Manage persistent branding configuration
    version     Print version and exit

All subcommands are first-class: the same core engine, same output layer.

SPDX-License-Identifier: Apache-2.0 OR LicenseRef-BoltZ-Commercial
"""

from __future__ import annotations

import sys
from enum import Enum
from pathlib import Path
from typing import Optional

import typer

from . import __version__

app = typer.Typer(
    name="boltz-kernel",
    help=(
        "Non-Markovian quantum dynamics solver with Boltzmann memory kernel "
        "(MaxEnt-Jaynes). Diagnostic for open quantum systems beyond Lindblad."
    ),
    no_args_is_help=True,
    add_completion=True,
    pretty_exceptions_enable=False,
)


# ── Enums for CLI choices (typer introspects these) ────────────────────────────

class Spectral(str, Enum):
    ohmic = "ohmic"
    super_ohmic = "super_ohmic"
    lorentzian = "lorentzian"
    band_edge = "band_edge"
    photonic_crystal = "photonic_crystal"
    waveguide = "waveguide"


class StructuredFormat(str, Enum):
    json = "json"
    yaml = "yaml"
    xml = "xml"
    jsonld = "jsonld"
    none = "none"


class VisualFormat(str, Enum):
    svg = "svg"
    pdf = "pdf"
    png = "png"
    tiff = "tiff"
    eps = "eps"
    none = "none"


class RawFormat(str, Enum):
    csv = "csv"
    hdf5 = "hdf5"
    parquet = "parquet"
    none = "none"


class Backend(str, Enum):
    auto = "auto"
    fft = "fft"
    quad = "quad"
    prony = "prony"
    nufft = "nufft"


# ── `run` — single comparison ──────────────────────────────────────────────────

@app.command()
def run(
    # Source of J(ω)
    spectral: Optional[Spectral] = typer.Option(
        None, "--spectral", "-s",
        help="Built-in spectral density (exclusive with --csv and --formula).",
    ),
    csv_file: Optional[Path] = typer.Option(
        None, "--csv", exists=True, dir_okay=False, readable=True,
        help="CSV with two columns [omega, J].",
    ),
    formula: Optional[str] = typer.Option(
        None, "--formula", "-f",
        help="Python expression for J(ω). Variable: w. Example: '0.1*w*np.exp(-w/10)'",
    ),
    stdin: bool = typer.Option(
        False, "--stdin",
        help="Read CSV from stdin (for pipelines).",
    ),
    # Physics parameters
    g: float = typer.Option(1.0, "--g", help="System-environment coupling."),
    T: float = typer.Option(0.05, "--T", help="Effective temperature (ℏ = k_B = 1)."),
    omega0: float = typer.Option(1.0, "--omega0", help="Emitter frequency."),
    t_max: float = typer.Option(50.0, "--t-max", help="Maximum simulation time."),
    dt: float = typer.Option(0.2, "--dt", help="Time step."),
    # Built-in spectral-density tunables (used when --spectral is given)
    eta: float = typer.Option(0.1, help="Ohmic: coupling strength η."),
    wc: float = typer.Option(5.0, help="Lorentzian/Ohmic: centre/cutoff frequency."),
    width: float = typer.Option(0.5, help="Lorentzian: linewidth Δ."),
    s_ohmic: int = typer.Option(1, help="Ohmic: s exponent (1=ohmic, 3=super-ohmic)."),
    beta: float = typer.Option(0.05, help="Band-edge: β coefficient."),
    we: float = typer.Option(5.0, help="Band-edge: edge frequency ωe."),
    gap_width: float = typer.Option(2.0, help="Photonic-crystal: band-gap width."),
    gamma_1d: float = typer.Option(0.5, help="Waveguide: 1-D decay rate."),
    tau_rt: float = typer.Option(1.0, help="Waveguide: round-trip time."),
    r: float = typer.Option(0.9, help="Waveguide: mirror reflectivity."),
    # Output configuration
    output_dir: Path = typer.Option(
        Path("./results"), "--output", "-o",
        help="Directory for output artefacts.",
    ),
    structured: StructuredFormat = typer.Option(
        StructuredFormat.json, "--structured",
        help="Structured metadata format (interpretable text).",
    ),
    visual: VisualFormat = typer.Option(
        VisualFormat.svg, "--visual",
        help="Visual export format.",
    ),
    raw: RawFormat = typer.Option(
        RawFormat.csv, "--raw",
        help="Raw time-series format.",
    ),
    # Branding overrides
    institute: Optional[str] = typer.Option(None, "--institute", help="Override institute name."),
    subtitle: Optional[str] = typer.Option(None, "--subtitle", help="Override subtitle."),
    reference: Optional[str] = typer.Option(None, "--reference", help="Override reference line."),
    logo: Optional[Path] = typer.Option(None, "--logo", exists=True, help="Logo image file."),
    footer: Optional[str] = typer.Option(None, "--footer", help="Override footer text."),
    # Solver backend
    backend: Backend = typer.Option(
        Backend.auto, "--backend",
        help=(
            "Bath-correlation backend. "
            "'auto' (default)→'fft'. "
            "'fft': uniform FFT, fast, stable at large τ. "
            "'quad': legacy scipy.quad, robust small-τ, slow. "
            "'prony': FFT + exponential decomposition + pseudomode solver "
            "(fastest .solve() for J with low-order exponential structure)."
        ),
    ),
    prony_order: Optional[int] = typer.Option(
        None, "--prony-order",
        help="Fix Prony order K (default: auto-select by variance threshold).",
    ),
    prony_maxent: bool = typer.Option(
        False, "--prony-maxent",
        help="Use MaxEnt criterion for Prony order K selection (novel).",
    ),
    # Output-style knobs
    as_json: bool = typer.Option(False, "--json", help="Print JSON summary to stdout."),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Suppress non-essential output."),
    plain: bool = typer.Option(False, "--plain", help="Plain text output (no colours/boxes)."),
) -> None:
    """
    Run a single Non-Markovian vs Lindblad comparison.

    Exit codes:
      0  Lindblad valid (trace distance < 1%)
      1  Lindblad invalid (publishable deviation detected)
      2  Input error (malformed CSV, negative J, etc.)
      3  Internal error
    """
    # Implementation intentionally deferred to cli_impl.run_command to keep
    # this module light and importable without side effects.
    from .cli_impl import run_command

    exit_code = run_command(
        spectral=spectral.value if spectral else None,
        csv_file=csv_file,
        formula=formula,
        stdin=stdin,
        g=g, T=T, omega0=omega0, t_max=t_max, dt=dt,
        eta=eta, wc=wc, width=width, s_ohmic=s_ohmic,
        beta=beta, we=we, gap_width=gap_width,
        gamma_1d=gamma_1d, tau_rt=tau_rt, r=r,
        output_dir=output_dir,
        structured=structured.value,
        visual=visual.value,
        raw=raw.value,
        institute=institute, subtitle=subtitle,
        reference=reference, logo=logo, footer=footer,
        as_json=as_json, quiet=quiet, plain=plain,
        backend=backend.value,
        prony_order=prony_order,
        prony_maxent=prony_maxent,
    )
    raise typer.Exit(code=exit_code)


# ── `wizard` — interactive mode (opt-in) ───────────────────────────────────────

@app.command()
def wizard() -> None:
    """
    Interactive guided session. Prompts for spectral density, parameters, preview,
    and export formats. Opt-in; never invoked by default.
    """
    from .wizard import run_wizard
    raise typer.Exit(code=run_wizard())


# ── `mcp` — launch MCP server for LLM-agent integration ───────────────────────

@app.command()
def mcp(
    transport: str = typer.Option(
        "stdio", "--transport",
        help="MCP transport: 'stdio' (default, for Claude Desktop/Code) "
             "or 'http' (streamable HTTP for browser-based agents).",
    ),
    host: str = typer.Option("127.0.0.1", "--host", help="HTTP transport bind host."),
    port: int = typer.Option(7787, "--port", help="HTTP transport port."),
) -> None:
    """Launch the BoltZ-Kernel MCP server.

    Exposes the solver tools (run_comparison, prony_decompose, bench,
    branding) so an LLM agent can invoke them directly from its context.
    Requires: pip install boltz-kernel[mcp]
    """
    try:
        from .mcp import start_server
    except ImportError as exc:
        typer.secho(
            f"MCP dependencies not available: {exc}\n"
            "Install with:  pip install boltz-kernel[mcp]",
            err=True, fg=typer.colors.RED,
        )
        raise typer.Exit(code=2) from exc
    raise typer.Exit(code=start_server(transport=transport, host=host, port=port))


# ── `gui` — launch PyQt6 desktop app ───────────────────────────────────────────

@app.command()
def gui() -> None:
    """Launch the PyQt6 desktop GUI (requires `pip install boltz-kernel[gui]`)."""
    try:
        from .ui import launch
    except ImportError as exc:
        typer.secho(
            f"GUI dependencies not available: {exc}\n"
            "Install with:  pip install boltz-kernel[gui]",
            err=True, fg=typer.colors.RED,
        )
        raise typer.Exit(code=2) from exc
    raise typer.Exit(code=launch())


# ── `batch` — YAML/TOML/JSON pipeline ──────────────────────────────────────────

batch_app = typer.Typer(help="Run batch pipelines from declarative configs.",
                        no_args_is_help=True)
app.add_typer(batch_app, name="batch")


@batch_app.command("run")
def batch_run(
    config: Path = typer.Argument(..., exists=True, dir_okay=False, readable=True,
                                  help="Config file (YAML, TOML, or JSON)."),
    output_dir: Optional[Path] = typer.Option(None, "--output", "-o",
                                              help="Override output directory."),
    workers: int = typer.Option(0, "--workers", "-w",
                                help="Parallel workers (0 = auto, 1 = sequential)."),
    resume: bool = typer.Option(False, "--resume",
                                help="Resume from last completed run."),
    dry_run: bool = typer.Option(False, "--dry-run",
                                 help="List runs that would execute; compute nothing."),
    quiet: bool = typer.Option(False, "--quiet", "-q"),
    plain: bool = typer.Option(False, "--plain"),
) -> None:
    """Execute a batch of runs declared in a config file."""
    from .batch import run_batch
    raise typer.Exit(code=run_batch(
        config=config, output_dir=output_dir, workers=workers,
        resume=resume, dry_run=dry_run, quiet=quiet, plain=plain,
    ))


# ── `bench` — reproducible reference cases ─────────────────────────────────────

@app.command()
def bench(
    case: str = typer.Argument(
        ...,
        help="Reference case name (e.g. jaynes-cummings, pure-dephasing, ohmic-markov).",
    ),
    output_dir: Path = typer.Option(Path("./bench_results"), "--output", "-o"),
) -> None:
    """Run a reproducible reference benchmark against a known analytical solution."""
    from .bench import run_bench
    raise typer.Exit(code=run_bench(case=case, output_dir=output_dir))


# ── `branding` — persistent branding config ────────────────────────────────────

branding_app = typer.Typer(help="Manage persistent branding (~/.boltz-kernel/branding.json).",
                           no_args_is_help=True)
app.add_typer(branding_app, name="branding")


@branding_app.command("show")
def branding_show() -> None:
    """Print current branding configuration as JSON."""
    import json

    from .branding import BrandingConfig
    cfg = BrandingConfig.load()
    typer.echo(json.dumps({
        "institute_name": cfg.institute_name,
        "subtitle":       cfg.subtitle,
        "reference":      cfg.reference,
        "logo_path":      cfg.logo_path,
        "logo_position":  cfg.logo_position,
        "footer_text":    cfg.footer_text,
    }, indent=2, ensure_ascii=False))


@branding_app.command("set")
def branding_set(
    institute: Optional[str] = typer.Option(None, "--institute"),
    subtitle: Optional[str] = typer.Option(None, "--subtitle"),
    reference: Optional[str] = typer.Option(None, "--reference"),
    logo: Optional[Path] = typer.Option(None, "--logo"),
    logo_position: Optional[str] = typer.Option(None, "--logo-position"),
    footer: Optional[str] = typer.Option(None, "--footer"),
) -> None:
    """Set one or more branding fields persistently."""
    from .branding import BrandingConfig
    cfg = BrandingConfig.load()
    if institute is not None:      cfg.institute_name = institute
    if subtitle is not None:       cfg.subtitle = subtitle
    if reference is not None:      cfg.reference = reference
    if logo is not None:           cfg.logo_path = str(logo)
    if logo_position is not None:  cfg.logo_position = logo_position
    if footer is not None:         cfg.footer_text = footer
    cfg.save()
    typer.echo(f"Branding updated: {cfg.__dict__}")


@branding_app.command("reset")
def branding_reset() -> None:
    """Restore default branding."""
    from .branding import BrandingConfig
    cfg = BrandingConfig()
    cfg.save()
    typer.echo("Branding reset to defaults.")


# ── `version` ──────────────────────────────────────────────────────────────────

@app.command()
def version() -> None:
    """Print BoltZ-Kernel version and exit."""
    typer.echo(f"BoltZ-Kernel {__version__}")


if __name__ == "__main__":
    app()
