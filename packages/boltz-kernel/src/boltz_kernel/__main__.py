"""
BoltZ-Kernel entry point.

Invoked as:
    boltz-kernel            # → subcommand help (Unix convention)
    boltz-kernel run ...
    boltz-kernel wizard
    boltz-kernel gui
    boltz-kernel batch ...
    boltz-kernel bench ...
    boltz-kernel branding ...
    python -m boltz_kernel   # equivalent to `boltz-kernel`

SPDX-License-Identifier: Apache-2.0 OR LicenseRef-BoltZ-Commercial
"""

from .cli import app


def main() -> None:
    app()


if __name__ == "__main__":
    main()
