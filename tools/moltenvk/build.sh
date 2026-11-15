#!/usr/bin/env bash
# Build the pinned MoltenVK with iOS resource-lifetime fixes.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
SDK="${1:-iphoneos}"
case "$SDK" in
  iphoneos) PLATFORM=ios; SLICE=ios-arm64 ;;
  iphonesimulator) PLATFORM=iossim; SLICE=ios-arm64_x86_64-simulator ;;
  *) echo "Expected iphoneos or iphonesimulator" >&2; exit 2 ;;
esac
REV=db66022459ffb663aa2b50f6b018bc2e124f5edf
SOURCE="${MOLTENVK_SOURCE:?Set MOLTENVK_SOURCE to a new external source directory}"
OUT="${MOLTENVK_BUILD:?Set MOLTENVK_BUILD to an external build directory}"
python3 -B - "$ROOT" "$SOURCE" "$OUT" <<'CHECK'
import sys
from pathlib import Path
root=Path(sys.argv[1]).resolve()
for arg in sys.argv[2:]:
    p=Path(arg).resolve()
    if p==root or root in p.parents:
        raise SystemExit('Keep upstream sources and build outputs outside the public checkout')
CHECK
PATCHES=("$ROOT"/tools/moltenvk/00*.patch)
mkdir -p "$OUT"
STAMP="$( { printf '%s\n' "$REV" "$SDK"; xcodebuild -version; cat "$0" "${PATCHES[@]}"; } | shasum -a 256 | cut -d' ' -f1)"
if [ -f "$OUT/libMoltenVK.a" ] && [ -f "$OUT/source-stamp" ] && [ "$(cat "$OUT/source-stamp")" = "$STAMP" ]; then
  echo "MoltenVK $SDK: patched library is current"
  exit 0
fi
if [ ! -d "$SOURCE/.git" ]; then
  git clone --depth 1 --branch v1.4.2 https://github.com/KhronosGroup/MoltenVK.git "$SOURCE"
fi
if [ "$(git -C "$SOURCE" rev-parse HEAD)" != "$REV" ]; then
  echo "Unexpected MoltenVK source revision in $SOURCE" >&2
  exit 1
fi
for PATCH in "${PATCHES[@]}"; do
  if ! git -C "$SOURCE" apply --reverse --check "$PATCH" 2>/dev/null; then
    git -C "$SOURCE" apply --check "$PATCH"
    git -C "$SOURCE" apply "$PATCH"
  fi
done
(
  cd "$SOURCE"
  ./fetchDependencies --"$PLATFORM" --keep-cache
  make "$PLATFORM"
)
LIB="$SOURCE/Package/Release/MoltenVK/static/MoltenVK.xcframework/$SLICE/libMoltenVK.a"
test -s "$LIB"
cp "$LIB" "$OUT/libMoltenVK.a"
printf '%s\n' "$STAMP" > "$OUT/source-stamp"
echo "Built patched MoltenVK: $OUT/libMoltenVK.a"
