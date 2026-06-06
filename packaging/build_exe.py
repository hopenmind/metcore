#!/usr/bin/env python3
"""
Build a native Hope 'n Mind GUI executable for the current host architecture.

PyInstaller does not cross-compile: each target OS and CPU is built on its own
machine. Run this on each platform (Windows, macOS, Linux; x86_64 or arm64), or
let the CI matrix in `.github/workflows/build-exe.yml` build them all at once.

Usage:
    python packaging/build_exe.py [--onedir] [--name NAME]

Layout:
    packaging/   the build scripts (tracked by git)
    build/       PyInstaller scratch (ignored)
    dist/        the finished executable, named hopenmind-<os>-<arch>[.exe]
"""

from __future__ import annotations

import argparse
import platform
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PKG = ROOT / "packaging"
SPEC = PKG / "metcore.spec"


def _target_name() -> str:
    osname = {"windows": "windows", "darwin": "macos", "linux": "linux"}.get(
        platform.system().lower(), platform.system().lower())
    arch = platform.machine().lower()
    arch = {"amd64": "x86_64", "x64": "x86_64", "aarch64": "arm64"}.get(arch, arch)
    suffix = ".exe" if osname == "windows" else ""
    return f"metcore-{osname}-{arch}{suffix}"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--onedir", action="store_true",
                    help="build a folder instead of a single file (faster start)")
    ap.add_argument("--name", default=None, help="override the output name")
    args = ap.parse_args()

    if shutil.which("pyinstaller") is None:
        print("PyInstaller is not installed.")
        print("Install it with:  pip install -e packages/hopenmind-gui[exe]")
        return 1

    out_name = args.name or _target_name()
    print(f"Building {out_name} on {platform.platform()} ...")

    cmd = ["pyinstaller", "--clean", "--noconfirm",
           "--distpath", str(ROOT / "dist"),
           "--workpath", str(ROOT / "build" / "_work"),
           str(SPEC)]
    if args.onedir:
        cmd.insert(1, "--onedir")
    rc = subprocess.call(cmd, cwd=str(PKG))
    if rc != 0:
        print("PyInstaller failed.")
        return rc

    produced = ROOT / "dist" / ("metcore.exe"
               if platform.system().lower() == "windows" else "metcore")
    final = ROOT / "dist" / out_name
    if produced.exists() and produced != final:
        produced.replace(final)
    print(f"Done: {final}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
