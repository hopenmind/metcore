"""local-dispatcher — local-only parallelism detection + backend choice.

No external credentials, no HPC account required. Queries the local
machine for:
  * CPU cores (physical + logical)
  * Available RAM
  * GPU presence (CUDA, Metal / MPS, ROCm)
  * Availability of joblib / dask / cupy / torch in the environment

Returns a backend recommendation (joblib-threadpool, cupy, dask,
serial) with a cost-vs-RAM verdict. When the problem exceeds every
local tier, escalates to the HPC cascade.

SPDX-License-Identifier: Apache-2.0 OR LicenseRef-HopenMind-Commercial
"""

from __future__ import annotations

from local_dispatcher.tool import (
    LocalDispatcherTool,
    detect_hardware,
    local_dispatcher_tool,
)

__all__ = ["LocalDispatcherTool", "detect_hardware", "local_dispatcher_tool"]

__version__ = "0.1.0"
__author__ = "DESVAUX G.J.Y."
__license__ = "Apache-2.0 OR LicenseRef-HopenMind-Commercial"
