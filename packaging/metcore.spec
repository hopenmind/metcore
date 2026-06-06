# PyInstaller spec for the Metcore desktop GUI.
# Preferred build:   python packaging/build_exe.py   (sets the per-arch name)
# Direct:            pyinstaller packaging/metcore.spec

import os, sys
from PyInstaller.utils.hooks import (
    collect_submodules, copy_metadata, collect_data_files)

# Ship distribution metadata so entry-point discovery works in the bundle.
_PKGS = ["metcore-gui", "metcore-export", "memkern", "obliquity-ng"]
datas = []
for pkg in _PKGS:
    try:
        datas += copy_metadata(pkg)
    except Exception:
        pass

# Bundle the app icon asset so the window icon resolves in the frozen app.
try:
    datas += collect_data_files("metcore_gui", includes=["assets/*"])
    datas += collect_data_files("metcore_export", includes=["assets/*"])
except Exception:
    pass

hiddenimports = [
    "metcore_gui.ng_panel",
    "metcore_gui.rheology_panel",
    "metcore_gui.quantum_panel",
    "metcore_gui.neural_panel",
    "metcore_gui._builtin",
    "metcore_gui.panel_features",
    "metcore_gui.batch",
    "metcore_gui.batch_panel",
    "metcore_gui.preferences",
    "metcore_gui.shortcuts_panel",
    "matplotlib.backends.backend_qtagg",
]
hiddenimports += collect_submodules("memkern")

# Platform icon (used only if present; the build does not fail without it).
_icns = os.path.join(SPECPATH, "metcore.icns")
_ico  = os.path.join(SPECPATH, "metcore.ico")
if sys.platform == "darwin" and os.path.isfile(_icns):
    icon = _icns
elif sys.platform == "win32" and os.path.isfile(_ico):
    icon = _ico
else:
    icon = None

a = Analysis(
    ["launcher.py"],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    excludes=["tkinter", "PyQt5", "PySide6", "PySide2"],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, a.binaries, a.datas, [],
    name="metcore",
    debug=False, strip=False, upx=True,
    console=False,                 # windowed app
    target_arch=None,              # native arch of the build host
    icon=icon,
)

# On macOS, wrap the executable in a proper .app so it can be shipped in a .dmg.
if sys.platform == "darwin":
    app = BUNDLE(
        exe,
        name="Metcore.app",
        icon=icon,
        bundle_identifier="com.hopenmind.metcore",
    )
