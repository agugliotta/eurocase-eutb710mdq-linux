#!/bin/sh
set -eu
export ARCH=arm
cp -a /previous/. /out/
/src/scripts/config --file /out/.config \
    --set-str LOCALVERSION -eutb710mdq-usbroot1 \
    --set-str INITRAMFS_SOURCE /work/usbroot-initramfs.list \
    --disable USB_G_SERIAL --enable CONFIGFS_FS --enable USB_CONFIGFS \
    --enable USB_CONFIGFS_ACM --enable USB_CONFIGFS_ECM --enable IPV6 \
    --disable USB_CONFIGFS_MASS_STORAGE --disable IP_PNP
make -C /src O=/out olddefconfig
python3 - <<'PY'
from pathlib import Path
s=Path('/out/.config').read_text().splitlines()
for name in ['USB_CONFIGFS','USB_CONFIGFS_ACM','USB_CONFIGFS_ECM','IPV6']:
    assert f'CONFIG_{name}=y' in s,name
for name in ['USB_G_SERIAL','USB_CONFIGFS_MASS_STORAGE','MTD','MMC','USB_STORAGE','IP_PNP','MODULES']:
    assert f'CONFIG_{name}=y' not in s,name
PY
make -C /src O=/out -j6 zImage
