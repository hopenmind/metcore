"""Entry point for the ``hopenmind`` command."""

from __future__ import annotations

import importlib
import importlib.metadata as ilm
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(
    name="hopenmind",
    help="Unified CLI for the Hope 'n Mind Scientific Suite.",
    no_args_is_help=True,
    add_completion=False,
)
console = Console()


# ──────────────────────────────────────────────────────────────────────────────
#  Known suite packages (canonical order)
# ──────────────────────────────────────────────────────────────────────────────

_SUITE_PACKAGES = [
    "hopenmind-suite",
    "hopenmind-export",
    "memkern",
    "memkern-rheology",
    "obliquity-ng",
    "eternal-nm-sim",
    "hpc-triage",
    "kernel-audit",
    "memkern-ladder",
    "hpc-oracle",
    "bench-extrap",
    "local-dispatcher",
    "hpc-manifest",
    "hopenmind-mcp",
    "hopenmind-gui",
    "boltz-kernel",
]


def _pkg_version(name: str) -> str | None:
    try:
        return ilm.version(name)
    except ilm.PackageNotFoundError:
        return None


def _installer_binary() -> list[str]:
    """Prefer ``uv pip`` when available, else ``pip``."""
    if shutil.which("uv"):
        return ["uv", "pip"]
    return [sys.executable, "-m", "pip"]


def _iter_subcommand_eps():
    """Yield entry-points registered under ``hopenmind.subcommands``."""
    eps = ilm.entry_points()
    if hasattr(eps, "select"):                 # Python ≥ 3.10
        yield from eps.select(group="hopenmind.subcommands")
    else:
        yield from eps.get("hopenmind.subcommands", [])  # type: ignore[attr-defined]


# ──────────────────────────────────────────────────────────────────────────────
#  list
# ──────────────────────────────────────────────────────────────────────────────

@app.command("list")
def list_packages(no_banner: bool = typer.Option(False, "--no-banner")) -> None:
    """Show every suite package and its install status."""
    if not no_banner:
        from metcore_cli.banner import print_banner
        print_banner(console)
        console.print()
    table = Table(title="Hope 'n Mind Suite")
    table.add_column("Package", style="cyan", no_wrap=True)
    table.add_column("Version", style="green")
    table.add_column("Status")

    for name in _SUITE_PACKAGES:
        ver = _pkg_version(name)
        status = "[green]installed[/green]" if ver else "[dim]not installed[/dim]"
        table.add_row(name, ver or "—", status)

    console.print(table)

    # Discovered subcommands
    subs = list(_iter_subcommand_eps())
    if subs:
        console.print("\n[bold]Discovered subcommands:[/bold]")
        for ep in subs:
            console.print(f"  • hopenmind [cyan]{ep.name}[/cyan] → {ep.value}")
    else:
        console.print("\n[dim]No subcommands registered via "
                      "'hopenmind.subcommands' entry-points yet.[/dim]")


# ──────────────────────────────────────────────────────────────────────────────
#  install / uninstall / update
# ──────────────────────────────────────────────────────────────────────────────

def _pip_call(args: list[str]) -> int:
    return subprocess.call(_installer_binary() + args)


@app.command("install")
def install(
    package: str = typer.Argument(..., help="Package name or VCS URL (git+https://…)"),
    upgrade: bool = typer.Option(False, "--upgrade", "-U", help="Upgrade if already installed."),
    editable: bool = typer.Option(False, "--editable", "-e", help="Install in editable mode (local path)."),
) -> None:
    """Install a sub-package from PyPI or a GitHub URL.

    Examples:

      hopenmind install obliquity-ng
      hopenmind install git+https://github.com/hopenmind/hopenmind-suite
      hopenmind install -e ./packages/obliquity-ng
    """
    args = ["install"]
    if upgrade:
        args.append("--upgrade")
    if editable:
        args += ["-e"]
    args.append(package)
    console.print(f"[bold]$ {' '.join(_installer_binary() + args)}[/bold]")
    rc = _pip_call(args)
    if rc != 0:
        raise typer.Exit(rc)
    console.print(f"[green]OK[/green]. If a new CLI subcommand appeared, "
                  f"run [cyan]hopenmind list[/cyan] to see it.")


@app.command("uninstall")
def uninstall(
    package: str = typer.Argument(...),
) -> None:
    """Uninstall a suite sub-package."""
    rc = _pip_call(["uninstall", "-y", package])
    if rc != 0:
        raise typer.Exit(rc)


@app.command("update")
def update(
    package: Optional[str] = typer.Argument(None, help="Omit to update every installed suite package."),
) -> None:
    """Update one or all suite packages."""
    targets = [package] if package else [p for p in _SUITE_PACKAGES
                                         if _pkg_version(p) is not None]
    if not targets:
        console.print("[yellow]No suite packages installed to update.[/yellow]")
        raise typer.Exit(0)
    for pkg in targets:
        rc = _pip_call(["install", "--upgrade", pkg])
        if rc != 0:
            console.print(f"[red]update failed for {pkg}[/red]")


# ──────────────────────────────────────────────────────────────────────────────
#  doctor
# ──────────────────────────────────────────────────────────────────────────────

@app.command("doctor")
def doctor() -> None:
    """Report environment + detected local hardware."""
    console.print(f"[bold]Python:[/bold] {sys.version.split()[0]}  ({sys.executable})")
    console.print(f"[bold]Platform:[/bold] {sys.platform}")

    # Lazy import so doctor works even if local-dispatcher is not installed
    try:
        from local_dispatcher import detect_hardware
        hw = detect_hardware()
        console.print("\n[bold]CPU:[/bold]",
                      f"{hw['cpu']['physical_cores']} physical / "
                      f"{hw['cpu']['logical_cores']} logical  "
                      f"[{hw['cpu']['architecture']}]")
        console.print(f"[bold]RAM:[/bold] {hw['ram']['total_gb']:.1f} GB")
        gpu = hw["gpu"]
        gpu_str = ", ".join([k for k in ("cuda", "metal", "rocm") if gpu.get(k)]) or "none detected"
        console.print(f"[bold]GPU:[/bold] {gpu_str}")
        libs = [k for k, v in hw["libraries"].items() if v]
        console.print(f"[bold]Libraries:[/bold] {', '.join(libs) or '(none of interest)'}")
    except ImportError:
        console.print("[yellow]local-dispatcher not installed — "
                      "`hopenmind install local-dispatcher` for hardware report.[/yellow]")


# ──────────────────────────────────────────────────────────────────────────────
#  triage — dispatcher for the full HPC-triage cascade
# ──────────────────────────────────────────────────────────────────────────────

@app.command("triage")
def triage(
    spectral: str = typer.Option(..., "--spectral", "-s",
                                 help="Python expression in `w` for J(ω). "
                                      "Example: 'exp(-w**2)'."),
    t_max: float = typer.Option(10.0, help="Target time horizon."),
    n_time_steps: int = typer.Option(1024, help="Number of time points."),
    target_accuracy: float = typer.Option(1e-3, help="Required relative accuracy."),
    coupling: float = typer.Option(0.1, help="System-bath coupling g."),
) -> None:
    """Run the full HPC-triage cascade on a problem described inline."""
    try:
        import numpy as np
        from hpc_triage import Problem, cascade
    except ImportError as exc:
        console.print(f"[red]hpc-triage not installed: {exc}[/red]")
        raise typer.Exit(1)

    # Build the ladder from whichever tier tools are importable
    ladder = []
    for mod_name, attr in (
        ("kernel_audit",     "kernel_audit_tool"),
        ("memkern_ladder",   "memkern_ladder_tool"),
        ("hpc_oracle",       "hpc_oracle_tool"),
        ("bench_extrap",     "bench_extrap_tool"),
        ("local_dispatcher", "local_dispatcher_tool"),
        ("hpc_manifest",     "hpc_manifest_tool"),
    ):
        try:
            mod = importlib.import_module(mod_name)
            ladder.append(getattr(mod, attr))
        except Exception:
            console.print(f"[dim]skipped {mod_name} (not installed)[/dim]")

    if not ladder:
        console.print("[red]No triage tools installed. "
                      "Try:  hopenmind install kernel-audit memkern-ladder[/red]")
        raise typer.Exit(1)

    ns: dict = {"__builtins__": {}, "exp": np.exp, "cos": np.cos, "sin": np.sin,
                "pi": np.pi, "sqrt": np.sqrt, "log": np.log, "abs": np.abs,
                "where": np.where}
    J = eval(f"lambda w: {spectral}", ns)  # noqa: S307 (safe ns, scientific use)

    problem = Problem(
        spectral_density=lambda w: np.asarray(J(np.asarray(w, dtype=float)),
                                              dtype=float),
        system_hamiltonian=__import__("numpy").diag([0.0, 1.0]).astype(complex),
        coupling_strength=coupling,
        t_max=t_max,
        n_time_steps=n_time_steps,
        target_accuracy=target_accuracy,
    )

    verdict = cascade(problem, ladder, verbose=False)
    console.print(f"\n[bold]Verdict:[/bold] {verdict.status.value} @ "
                  f"[cyan]{verdict.tier.value}[/cyan]")
    console.print(f"[bold]Reason:[/bold]  {verdict.message}")
    if verdict.cost_estimate_seconds is not None:
        console.print(f"[bold]Cost:[/bold] ~{verdict.cost_estimate_seconds:.1f} s")
    if verdict.memory_estimate_gb is not None:
        console.print(f"[bold]RAM:[/bold]  ~{verdict.memory_estimate_gb:.2f} GB")


# ──────────────────────────────────────────────────────────────────────────────
#  Lazy subcommand forwarding — expose each registered entry-point
# ──────────────────────────────────────────────────────────────────────────────

def _register_discovered_subcommands() -> None:
    """Each entry-point under ``hopenmind.subcommands`` becomes a command."""
    for ep in _iter_subcommand_eps():
        name = ep.name
        try:
            target = ep.load()
        except Exception as exc:                 # noqa: BLE001
            _make_broken_cmd(name, exc)
            continue

        # Accept either a typer.Typer instance or a callable (function)
        if isinstance(target, typer.Typer):
            app.add_typer(target, name=name)
        elif callable(target):
            _wrap_callable(name, target)


def _make_broken_cmd(name: str, exc: Exception) -> None:
    def _broken() -> None:  # pragma: no cover — defensive only
        console.print(f"[red]Subcommand {name!r} failed to load: {exc!r}[/red]")
        raise typer.Exit(1)
    app.command(name, help=f"[unavailable: {exc}]")(_broken)


def _wrap_callable(name: str, fn) -> None:
    def _cmd() -> None:
        fn()
    _cmd.__doc__ = getattr(fn, "__doc__", None) or ""
    app.command(name)(_cmd)


# Run entry-point discovery at import time — adds commands to ``app``
_register_discovered_subcommands()


if __name__ == "__main__":
    app()
