#!/bin/sh
# Offline candidate based on SD v2; never writes a device or the v2 artifacts.
set -eu
export ARCH=arm CROSS_COMPILE=arm-linux-gnueabihf-
mkdir -p /out
cp /baseline/kernel.config /out/.config
/src/scripts/config --file /out/.config \
    --set-str LOCALVERSION -eutb710mdq-sd3power \
    --enable WATCHDOG --enable SUNXI_WATCHDOG \
    --disable WATCHDOG_NOWAYOUT --disable WATCHDOG_HANDLE_BOOT_ENABLED
make -C /src O=/out olddefconfig
python3 - <<'CHECK'
from pathlib import Path
s = Path('/out/.config').read_text().splitlines()
for name in ['WATCHDOG', 'WATCHDOG_CORE', 'SUNXI_WATCHDOG', 'UNIX',
             'SQUASHFS', 'MMC_SUNXI', 'TOUCHSCREEN_SILEAD', 'USB_CONFIGFS_ACM']:
    assert f'CONFIG_{name}=y' in s, name
for name in ['WATCHDOG_NOWAYOUT', 'WATCHDOG_HANDLE_BOOT_ENABLED', 'MTD', 'MODULES']:
    assert f'CONFIG_{name}=y' not in s, name
CHECK
make -C /src O=/out -j"${JOBS:-6}" zImage
