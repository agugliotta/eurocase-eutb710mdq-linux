#!/bin/sh
# Test U-Boot's core independently of its USB console and SD file loading.
set -eu
export CROSS_COMPILE=arm-linux-gnueabihf-
cp -a /previous/. /out/
/src/scripts/config --file /out/.config \
    --set-str PREBOOT 'bootz 0x42000000 - 0x43000000'
make -C /src O=/out olddefconfig
python3 - <<'CHECK'
from pathlib import Path
s = Path('/out/.config').read_text().splitlines()
for setting in ['CONFIG_USE_PREBOOT=y', 'CONFIG_CMD_BOOTZ=y',
                'CONFIG_PREBOOT="bootz 0x42000000 - 0x43000000"',
                'CONFIG_ENV_IS_NOWHERE=y']:
    assert setting in s, setting
CHECK
make -C /src O=/out -j6 EXT_DTB=/out/uboot.dtb all
