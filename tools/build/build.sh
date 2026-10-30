#!/bin/sh
# SPDX-License-Identifier: GPL-2.0-or-later
set -eu
cd /project
exec 9>/cache/build.lock
flock -n 9 || { echo "This build cache is already in use; wait or choose another BUILD_VOLUME." >&2; exit 1; }
python3 tools/build/support.py /project /cache
python3 tools/build/check-sd-preparation.py --sources-only
mkdir -p /cache/kernel /cache/uboot /cache/buildroot /cache/buildroot-dl
ln -s /cache/firmware /firmware
ln -s /project/tools/build /work
ln -s /artifacts /kernel
ln -s /project/config-baselines/bringup /baseline
ln -s /cache/sources/linux /src
ln -s /cache/kernel /out
cp config-baselines/installed/kernel.config /out/.config
/src/scripts/config --file /out/.config --set-str LOCALVERSION -eutb710mdq-local \
    --set-str INITRAMFS_SOURCE '' --set-str EXTRA_FIRMWARE_DIR /firmware
make -C /src O=/out olddefconfig
for option in CONFIG_SUNXI_WATCHDOG=y CONFIG_PACKET=y CONFIG_MMC_SUNXI=y CONFIG_USB_CONFIGFS_ACM=y; do
    grep -qx "$option" /out/.config
done
# Stable build metadata, without the host owner's name, path or machine name.
export KBUILD_BUILD_USER=builder KBUILD_BUILD_HOST=container
export KBUILD_BUILD_TIMESTAMP='2024-11-17 00:00:00 UTC' KBUILD_BUILD_VERSION=1
make -C /src O=/out -j"$JOBS" zImage
arm-linux-gnueabihf-gcc -E -nostdinc -undef -D__DTS__ -x assembler-with-cpp \
    -I/src/arch/arm/boot/dts/allwinner -I/src/include \
    /project/tools/board/sun8i-a23-eurocase-eutb710mdq-sd.dts > /out/board.dts
dtc -I dts -O dtb -o /artifacts/board.dtb /out/board.dts
cp /out/arch/arm/boot/zImage /artifacts/zImage
cp /out/.config /artifacts/kernel.config
rm /src /out
ln -s /cache/sources/uboot /src
ln -s /cache/uboot /out
sh tools/build/build-a23-sd-uboot.sh
cp /out/u-boot-sunxi-with-spl.bin /out/boot.scr /artifacts/
cp /out/.config /artifacts/u-boot.config
unset ARCH CROSS_COMPILE
make -C /cache/sources/buildroot O=/cache/buildroot BR2_JLEVEL="$JOBS" \
    BR2_EXTERNAL=/project/tools/buildroot tablet_sd_defconfig
# Local application sources may change between incremental builds.
make -C /cache/sources/buildroot O=/cache/buildroot BR2_JLEVEL="$JOBS" \
    BR2_DL_DIR=/cache/buildroot-dl tablet-poc-rebuild
make -C /cache/sources/buildroot O=/cache/buildroot BR2_JLEVEL="$JOBS" \
    BR2_DL_DIR=/cache/buildroot-dl -j"$JOBS"
qemu-arm -L /cache/buildroot/target /cache/buildroot/target/usr/bin/tablet-poc --self-check
cp /cache/buildroot/images/rootfs.squashfs /cache/buildroot/images/sdcard.img /artifacts/
cp /cache/buildroot/.config /artifacts/buildroot.config
python3 tools/build/check-sd-preparation.py --image --image-dir /artifacts
cp /firmware/LICENCE.rtlwifi_firmware.txt /artifacts/
cd /artifacts
sha256sum sdcard.img > SHA256SUMS
echo 'Build complete: dist/sdcard.img. Offline checks passed; this new image has NOT been boot-tested.'
echo 'Contains owner-supplied firmware/calibration: for your local use, not a cleared public binary release.'
