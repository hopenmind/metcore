#!/usr/bin/env bash
# Package the built Linux binary into a self-contained .AppImage.
# Run on Linux, AFTER `python packaging/build_exe.py` has produced
# dist/metcore-linux-<arch>. Needs: wget, fuse (CI provides them).
#   bash packaging/make_appimage.sh
set -euo pipefail
cd "$(dirname "$0")/.."          # repo root

ARCH="$(uname -m)"               # x86_64 or aarch64
case "$ARCH" in
  x86_64)  NAME_ARCH=x86_64; AIT_ARCH=x86_64 ;;
  aarch64) NAME_ARCH=arm64;  AIT_ARCH=aarch64 ;;
  *) echo "unsupported arch $ARCH"; exit 1 ;;
esac

BIN="dist/metcore-linux-${NAME_ARCH}"
[ -f "$BIN" ] || { echo "missing $BIN (run build_exe.py first)"; exit 1; }

APPDIR="build/Metcore.AppDir"
rm -rf "$APPDIR"; mkdir -p "$APPDIR/usr/bin"
cp "$BIN" "$APPDIR/usr/bin/metcore"; chmod +x "$APPDIR/usr/bin/metcore"
cp packaging/AppRun "$APPDIR/AppRun"; chmod +x "$APPDIR/AppRun"
cp packaging/metcore.desktop "$APPDIR/metcore.desktop"
cp packaging/metcore.png "$APPDIR/metcore.png"

# fetch appimagetool for the build arch
TOOL="build/appimagetool-${AIT_ARCH}.AppImage"
if [ ! -f "$TOOL" ]; then
  wget -q -O "$TOOL" \
    "https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-${AIT_ARCH}.AppImage"
  chmod +x "$TOOL"
fi

export APPIMAGE_EXTRACT_AND_RUN=1   # CI runners often lack FUSE
OUT="dist/metcore-linux-${NAME_ARCH}.AppImage"
ARCH="$AIT_ARCH" "$TOOL" --no-appstream "$APPDIR" "$OUT"
echo "Built $OUT"
