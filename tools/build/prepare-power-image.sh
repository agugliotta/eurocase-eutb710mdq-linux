#!/bin/sh
# Container paths: validated /v2 (ro), Buildroot /out (ro), new /candidate (rw).
# Builds regular files only; no block device is opened.
set -eu
export PATH="/out/host/bin:/out/host/sbin:$PATH"
test "$(sha256sum /v2/rootfs.squashfs | cut -d ' ' -f1)" = dc11e92240a219c11559ca42db5e5db0976fb39e492cffaa79fd26e47e72ab33
test -f /candidate/kernel/zImage
test -f /candidate/kernel/kernel.config
grep -qx 'CONFIG_SUNXI_WATCHDOG=y' /candidate/kernel/kernel.config
mkdir /candidate/image
unsquashfs -d /tmp/power-root /v2/rootfs.squashfs
cp /candidate/tablet-poc /tmp/power-root/usr/bin/tablet-poc
chmod 755 /tmp/power-root/usr/bin/tablet-poc
qemu-arm -L /tmp/power-root /tmp/power-root/usr/bin/tablet-poc --self-check
mksquashfs /tmp/power-root /candidate/image/rootfs.squashfs \
    -noappend -comp gzip -all-root -no-xattrs -no-progress
for file in board.dtb boot.scr u-boot-sunxi-with-spl.bin u-boot.config; do
    cp "/v2/$file" "/candidate/image/$file"
done
cp /candidate/kernel/zImage /candidate/kernel/kernel.config /candidate/image/
genimage --rootpath /tmp/power-root --tmppath /tmp/power-genimage \
    --inputpath /candidate/image --outputpath /candidate/image \
    --config /work/buildroot/board/genimage.cfg
