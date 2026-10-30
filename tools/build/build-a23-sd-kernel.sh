#!/bin/sh
set -eu
export ARCH=arm CROSS_COMPILE=arm-linux-gnueabihf-
mkdir -p /out
cp /baseline/kernel.config /out/.config
/src/scripts/config --file /out/.config \
    --set-str LOCALVERSION -eutb710mdq-sd2 \
    --set-str INITRAMFS_SOURCE '' \
    --enable MMC --enable MMC_BLOCK --enable MMC_SUNXI \
    --enable MSDOS_PARTITION --enable SQUASHFS --enable SQUASHFS_ZLIB \
    --enable DEVTMPFS --enable DEVTMPFS_MOUNT --enable U_SERIAL_CONSOLE --enable UNIX \
    --set-str EXTRA_FIRMWARE 'silead/eurocase-g739-gsl1680-1024x600.fw rtlwifi/rtl8188eufw.bin' \
    --set-str EXTRA_FIRMWARE_DIR /firmware \
    --disable MTD --disable MODULES --disable USB_CONFIGFS_ECM
make -C /src O=/out olddefconfig
python3 - <<'CHECK'
from pathlib import Path
s = Path('/out/.config').read_text().splitlines()
for name in ['MMC', 'MMC_BLOCK', 'MMC_SUNXI', 'SQUASHFS', 'SQUASHFS_ZLIB',
             'MSDOS_PARTITION', 'DRM_SUN4I', 'DRM_PANEL_SIMPLE',
             'FRAMEBUFFER_CONSOLE', 'TOUCHSCREEN_SILEAD', 'INPUT_EVDEV',
             'USB_MUSB_SUNXI', 'USB_CONFIGFS_ACM', 'DEVTMPFS_MOUNT', 'UNIX']:
    assert f'CONFIG_{name}=y' in s, name
for name in ['MTD', 'MODULES', 'USB_CONFIGFS_ECM']:
    assert f'CONFIG_{name}=y' not in s, name
CHECK
make -C /src O=/out -j"${JOBS:-6}" zImage
arm-linux-gnueabihf-gcc -E -nostdinc -undef -D__DTS__ -x assembler-with-cpp \
    -I/src/arch/arm/boot/dts/allwinner -I/src/include \
    /board/sun8i-a23-eurocase-eutb710mdq-sd.dts > /out/board.dts
dtc -I dts -O dtb -o /out/board.dtb /out/board.dts
