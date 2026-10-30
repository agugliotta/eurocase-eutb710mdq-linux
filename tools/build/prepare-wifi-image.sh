#!/bin/sh
# Regular-file candidate only: /baseline is the validated active v3 image.
set -eu
export PATH="/out/host/bin:/out/host/sbin:$PATH"
test -f /candidate/kernel/zImage
grep -qx 'CONFIG_LOCALVERSION="-eutb710mdq-sd4wifi"' /candidate/kernel/kernel.config
grep -qx 'CONFIG_SUNXI_WATCHDOG=y' /candidate/kernel/kernel.config
mkdir /candidate/image
unsquashfs -d /tmp/wifi-root /baseline/rootfs.squashfs
test "$(sha256sum /tmp/wifi-root/usr/bin/tablet-poc | cut -d ' ' -f1)" = 787396e97d2cc5618267ab765035183fa529fa4ff4428ba5b82b37aebf0dd42f
mkdir -p /tmp/wifi-root/opt
tar -C /tmp/wifi-root/opt -xzf /candidate/wifi-bundle.tar.gz
qemu-arm -L /tmp/wifi-root /tmp/wifi-root/usr/bin/tablet-poc --self-check
qemu-arm -L /tmp/wifi-root -E LD_LIBRARY_PATH=/tmp/wifi-root/opt/wifi/lib /tmp/wifi-root/opt/wifi/bin/wpa_supplicant -v
mksquashfs /tmp/wifi-root /candidate/image/rootfs.squashfs \
    -noappend -comp gzip -all-root -no-xattrs -no-progress
for file in board.dtb boot.scr u-boot-sunxi-with-spl.bin u-boot.config; do
    cp "/baseline/$file" "/candidate/image/$file"
done
cp /candidate/kernel/zImage /candidate/kernel/kernel.config /candidate/image/
genimage --rootpath /tmp/wifi-root --tmppath /tmp/wifi-genimage \
    --inputpath /candidate/image --outputpath /candidate/image \
    --config /work/buildroot/board/genimage.cfg
