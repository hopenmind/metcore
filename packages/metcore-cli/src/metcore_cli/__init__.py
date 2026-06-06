"""hopenmind-cli — unified command root for the suite.

Commands
--------
``hopenmind list``             — show installed suite packages + their status
``hopenmind install <pkg>``    — install/update a sub-package (PyPI or GitHub)
``hopenmind uninstall <pkg>``
``hopenmind doctor``           — environment + hardware diagnostic
``hopenmind triage <cfg>``     — run the full HPC-triage cascade on a config file
``hopenmind <sub> ...``        — forward to a sub-package's own CLI when exposed

Sub-packages expose themselves by declaring an entry-point under the
``hopenmind.subcommands`` group in their own ``pyproject.toml``:

    [project.entry-points."hopenmind.subcommands"]
    myname = "my_package.cli:app"

``hopenmind`` discovers them lazily via ``importlib.metadata`` so the
top-level CLI never hard-codes its sub-tools.

SPDX-License-Identifier: Apache-2.0 OR LicenseRef-HopenMind-Commercial
"""

from __future__ import annotations

__version__ = "0.1.0"
__author__ = "DESVAUX G.J.Y."
__license__ = "Apache-2.0 OR LicenseRef-HopenMind-Commercial"
