#!/bin/sh
set -eu
export ARCH=arm
cp -a /previous/. /out/
cp /baseline/kernel.config /out/.config
cp -a /iwsrc /tmp/iw
PKG_CONFIG_LIBDIR=/usr/lib/arm-linux-gnueabihf/pkgconfig \
  make -C /tmp/iw -j4 CC=arm-linux-gnueabihf-gcc CFLAGS=-Os LDFLAGS=-static
cp /tmp/iw/iw /out/iw
arm-linux-gnueabihf-gcc -static -Os -Wall -Wextra -Werror -o /out/read-events /work/read-input-events.c
arm-linux-gnueabihf-gcc -static -Os -Wall -Wextra -Werror -o /out/fb-bars /work/fb-bars.c
/src/scripts/config --file /out/.config \
  --set-str INITRAMFS_SOURCE /work/display-initramfs.list \
  --set-str LOCALVERSION -eutb710mdq-display1 \
  --enable DRM --enable DRM_SUN4I --enable DRM_SUN4I_BACKEND \
  --enable DRM_PANEL_SIMPLE --enable DRM_FBDEV_EMULATION --enable FB \
  --enable FRAMEBUFFER_CONSOLE --enable BACKLIGHT_PWM --enable PWM_SUN4I \
  --enable NET --enable NETDEVICES --enable WIRELESS --enable WLAN \
  --enable WLAN_VENDOR_REALTEK --enable CFG80211 --enable MAC80211 --enable RTL8XXXU \
  --enable INET --disable IP_PNP --disable IPV6 --disable PACKET \
  --enable SOUND --enable SND --enable SND_SOC \
  --enable SND_SUN4I_CODEC --enable SND_SUN8I_CODEC_ANALOG
make -C /src O=/out olddefconfig
python3 - <<'PY'
from pathlib import Path
s = Path('/out/.config').read_text().splitlines()
for name in ['DRM_SUN4I', 'DRM_PANEL_SIMPLE', 'DRM_FBDEV_EMULATION', 'RTL8XXXU',
             'CFG80211', 'SND_SUN4I_CODEC', 'SND_SUN8I_CODEC_ANALOG', 'TOUCHSCREEN_SILEAD']:
    assert f'CONFIG_{name}=y' in s, name
for name in ['MTD', 'MMC', 'ATA', 'SCSI', 'USB_STORAGE', 'CPU_FREQ', 'MODULES', 'IP_PNP', 'IPV6']:
    assert f'CONFIG_{name}=y' not in s, name
PY
make -C /src O=/out -j"${JOBS:-6}" zImage
arm-linux-gnueabihf-gcc -E -nostdinc -undef -D__DTS__ -x assembler-with-cpp \
  -I/src/arch/arm/boot/dts/allwinner -I/src/include \
  /board/sun8i-a23-eurocase-eutb710mdq-display.dts > /out/board.dts
dtc -I dts -O dtb -o /out/board.dtb /out/board.dts
