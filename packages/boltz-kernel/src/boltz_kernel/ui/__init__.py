"""
BoltZ-Kernel PyQt6 GUI package.

The GUI is an optional dependency: `pip install boltz-kernel[gui]`.
Core scientific use (CLI, batch, Python API) does not require PyQt6.

SPDX-License-Identifier: Apache-2.0 OR LicenseRef-BoltZ-Commercial
"""

__all__ = ["launch"]


def launch() -> int:
    """Start the PyQt6 main window. Returns Qt exit code."""
    try:
        from PyQt6.QtWidgets import QApplication
    except ImportError as exc:
        raise ImportError(
            "PyQt6 not installed. Install the GUI extra: "
            "pip install boltz-kernel[gui]"
        ) from exc

    import sys

    from .main_window import MainWindow  # existing window class preserved

    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return app.exec()
