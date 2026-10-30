#!/bin/sh
set -eu
TABLET_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
FDT_SOURCE="$TABLET_ROOT/.tools/sources/u-boot-5508406582f6f7120dce0c4b3059819a41788db2/scripts/dtc/libfdt"
SUNXI_SOURCE="$TABLET_ROOT/.tools/sources/sunxi-tools-a08a24a2aa5804bde7fa6ea8cdb08135d018da33"
FDT_OUTPUT="$TABLET_ROOT/.tools/build/host-libfdt"
mkdir -p "$FDT_OUTPUT" "$TABLET_ROOT/.tools/bin"
for source in "$FDT_SOURCE"/*.c; do
    object=$(basename "$source" .c)
    clang -O2 -I"$FDT_SOURCE" -c "$source" -o "$FDT_OUTPUT/$object.o"
done
ar rcs "$FDT_OUTPUT/libfdt.a" "$FDT_OUTPUT"/*.o
make -C "$SUNXI_SOURCE" -j4 CC=clang \
    LIBFDT_CFLAGS="-I$FDT_SOURCE" LIBFDT_LIBS="$FDT_OUTPUT/libfdt.a" \
    sunxi-fel sunxi-fexc sunxi-bootinfo
for name in sunxi-fel sunxi-fexc sunxi-bootinfo; do
    install -m 755 "$SUNXI_SOURCE/$name" "$TABLET_ROOT/.tools/bin/$name"
done
