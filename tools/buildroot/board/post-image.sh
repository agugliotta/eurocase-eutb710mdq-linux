#!/bin/sh
set -eu
export PATH="$HOST_DIR/bin:$HOST_DIR/sbin:$PATH"
for file in zImage board.dtb boot.scr u-boot-sunxi-with-spl.bin; do
    cp "/artifacts/$file" "$BINARIES_DIR/$file"
done
rm -rf "$BUILD_DIR/genimage-tablet.tmp"
exec "$HOST_DIR/bin/genimage" --rootpath "$TARGET_DIR" \
    --tmppath "$BUILD_DIR/genimage-tablet.tmp" --inputpath "$BINARIES_DIR" \
    --outputpath "$BINARIES_DIR" \
    --config "$BR2_EXTERNAL_TABLET_PATH/board/genimage.cfg"
