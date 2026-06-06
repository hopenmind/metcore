# `hopenmind-gui`

Unified PyQt6 desktop application for the suite.

- Hosts one tab per installed module.
- Lifts the BoltZ-Kernel branding + 7-format academic export surface.
- Module panels discovered via entry-points (`hopenmind.gui_panels`).
- Designed for PyInstaller single-file `.exe` / `.app` / AppImage packaging.

## Run

```bash
pip install "hopenmind-gui[exe]"
hopenmind-gui
```

## Register a panel

Sub-packages add a panel by subclassing `ModulePanel` and declaring the
entry-point:

```python
# my_package/gui.py
from hopenmind_gui import ModulePanel

class MyPanel(ModulePanel):
    display_name = "My Tool"
    slug = "my-tool"
    def build(self):
        from PyQt6.QtWidgets import QLabel
        return QLabel("Hello from my tool")
```

```toml
# my_package/pyproject.toml
[project.entry-points."hopenmind.gui_panels"]
my-tool = "my_package.gui:MyPanel"
```

## Package as `.exe`

```bash
pip install "hopenmind-gui[exe]"
pyinstaller --onefile --windowed \
    --name HopenmindSuite \
    -m hopenmind_gui
```
