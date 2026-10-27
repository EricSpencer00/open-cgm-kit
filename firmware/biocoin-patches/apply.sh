#!/bin/sh
# Build a patched copy of the pinned Biocoin firmware. vendor/ is never modified.
# Usage: firmware/biocoin-patches/apply.sh [build-dir]   (default build/biocoin-firmware)
set -eu
root=$(cd "$(dirname "$0")/../.." && pwd)
out=${1:-$root/build/biocoin-firmware}

rm -rf "$out"
mkdir -p "$out"
cp -R "$root/vendor/biocoin/firmware/." "$out/"
cp "$root/firmware/common/ock_frame.h" "$out/src/util/ock_frame.h"
(cd "$out" && shasum -a 256 -c "$root/firmware/biocoin-patches/upstream.sha256" >/dev/null) ||
  { echo "vendor/biocoin/firmware differs from the hashes the patches were made against" >&2; exit 1; }
for p in "$root"/firmware/biocoin-patches/*.patch; do
  patch -p1 -d "$out" < "$p"
done
(cd "$out" && shasum -a 256 -c "$root/firmware/biocoin-patches/patched.sha256" >/dev/null) ||
  { echo "patched tree does not match patched.sha256" >&2; exit 1; }
echo "patched firmware in $out; build with: pio run -d $out -e release"
