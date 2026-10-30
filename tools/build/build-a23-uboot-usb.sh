#!/bin/sh
set -eu
cp /baseline/u-boot-spl.config /out/.config
/src/scripts/config --file /out/.config \
  --disable DISTRO_DEFAULTS --disable BOOTSTD \
  --set-val BOOTDELAY -1 --enable USE_BOOTCOMMAND --set-str BOOTCOMMAND '' \
  --enable USE_PREBOOT \
  --set-str PREBOOT 'setenv stdin usbacm; setenv stdout usbacm; setenv stderr usbacm; version' \
  --enable USB_GADGET --enable DM_USB_GADGET --enable USB_MUSB_GADGET \
  --enable USB_GADGET_DOWNLOAD --enable USB_FUNCTION_ACM \
  --disable USB_ETHER --disable USB_FUNCTION_FASTBOOT \
  --disable USB_FUNCTION_MASS_STORAGE --disable CMD_DFU \
  --disable VIDEO_SUNXI --disable VIDEO --disable SPL_VIDEO \
  --disable REGULATOR_AXP_DRIVEVBUS --disable REGULATOR_AXP_USB_POWER \
  --disable CMD_SAVEENV --disable CMD_NVEDIT_EFI --disable EFI_LOADER
make -C /src O=/out olddefconfig
python3 - <<'PY'
from pathlib import Path
s=Path('/out/.config').read_text().splitlines()
for entry in ['CONFIG_USB_FUNCTION_ACM=y', 'CONFIG_USB_MUSB_GADGET=y',
              'CONFIG_DM_USB_GADGET=y', 'CONFIG_ENV_IS_NOWHERE=y',
              'CONFIG_BOOTDELAY=-1', 'CONFIG_BOOTCOMMAND=""']:
    assert entry in s, entry
for symbol in ['MMC','NAND','SPI_FLASH','USB_STORAGE','USB_MUSB_HOST',
               'USB_ETHER','VIDEO','CMD_SAVEENV','BOOTSTD','DISTRO_DEFAULTS',
               'USB_FUNCTION_FASTBOOT','USB_FUNCTION_MASS_STORAGE']:
    assert f'CONFIG_{symbol}=y' not in s, symbol
PY
make -C /src O=/out -j"${JOBS:-4}" EXT_DTB=/baseline/eutb710mdq-diagnostic.dtb u-boot.bin u-boot.img
arm-linux-gnueabihf-nm --defined-only /out/u-boot > /out/uboot-symbols.txt
