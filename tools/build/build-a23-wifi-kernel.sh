#!/bin/sh
# Separate candidate; only a software efuse shadow fallback is added to v3.
set -eu
export ARCH=arm CROSS_COMPILE=arm-linux-gnueabihf-
cp /baseline/kernel.config /out/.config
/src/scripts/config --file /out/.config \
    --set-str LOCALVERSION -eutb710mdq-sd4wifi \
    --enable PACKET \
    --set-str EXTRA_FIRMWARE 'silead/eurocase-g739-gsl1680-1024x600.fw rtlwifi/rtl8188eufw.bin rtlwifi/eurocase-g739-rtl8188eu-efuse.bin' \
    --set-str EXTRA_FIRMWARE_DIR /firmware
make -C /src O=/out olddefconfig
grep -qx 'CONFIG_PACKET=y' /out/.config
make -C /src O=/out -j6 zImage
