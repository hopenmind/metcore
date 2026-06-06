#!/usr/bin/env bash
# Package the built macOS .app bundle into a .dmg.
# Run on macOS, AFTER `python packaging/build_exe.py` has produced
# dist/Metcore.app (the spec emits a BUNDLE on macOS).
#   bash packaging/make_dmg.sh
# Disk-frugal: CI mac runners are tight on space, so we drop the PyInstaller
# work dir first, MOVE (not copy) the .app into staging, and clean up after.
set -euo pipefail
cd "$(dirname "$0")/.."          # repo root

case "$(uname -m)" in
  arm64)  NAME_ARCH=arm64 ;;
  x86_64) NAME_ARCH=x86_64 ;;
  *) echo "unsupported arch $(uname -m)"; exit 1 ;;
esac

APP="dist/Metcore.app"
[ -d "$APP" ] || { echo "missing $APP (run build_exe.py first)"; exit 1; }

# Free as much disk as possible before hdiutil doubles the footprint.
rm -rf build || true
python3 -m pip cache purge >/dev/null 2>&1 || true
df -h . || true

STAGE="dmg_stage"
rm -rf "$STAGE"; mkdir -p "$STAGE"
mv "$APP" "$STAGE/"                            # move, do not duplicate
ln -s /Applications "$STAGE/Applications"      # drag-to-install affordance

OUT="dist/metcore-macos-${NAME_ARCH}.dmg"
rm -f "$OUT"
# Explicit size + HFS+: works around the APFS auto-sizing bug that makes
# hdiutil fail with a bogus "No space left on device" on CI runners.
SIZE_MB=$(( $(du -sm "$STAGE" | cut -f1) + 250 ))
hdiutil create -volname "Metcore" -srcfolder "$STAGE" -ov \
        -fs HFS+ -format UDZO -size "${SIZE_MB}m" "$OUT"
rm -rf "$STAGE"
echo "Built $OUT"
ls -lh dist/
