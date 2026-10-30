#!/bin/sh
set -eu
export CROSS_COMPILE=arm-linux-gnueabihf-
cp -a /previous/. /out/
/src/scripts/config --file /out/.config \
    --set-val BOOTDELAY -1 --enable USE_BOOTCOMMAND --set-str BOOTCOMMAND '' \
    --enable USE_PREBOOT \
    --set-str PREBOOT 'setenv stdin usbacm; setenv stdout usbacm; setenv stderr usbacm; version' \
    --enable USB --enable USB_GADGET --enable DM_USB_GADGET --enable USB_MUSB_GADGET \
    --enable USB_GADGET_DOWNLOAD --enable USB_FUNCTION_ACM \
    --disable USB_ETHER --disable USB_FUNCTION_FASTBOOT \
    --disable USB_FUNCTION_MASS_STORAGE --disable CMD_DFU \
    --disable REGULATOR_AXP_DRIVEVBUS --disable REGULATOR_AXP_USB_POWER
make -C /src O=/out olddefconfig
python3 - <<'CHECK'
from pathlib import Path
s=Path('/out/.config').read_text().splitlines()
for setting in ['CONFIG_MMC=y', 'CONFIG_USB_FUNCTION_ACM=y',
                'CONFIG_USB_MUSB_GADGET=y', 'CONFIG_DM_USB_GADGET=y',
                'CONFIG_ENV_IS_NOWHERE=y', 'CONFIG_BOOTDELAY=-1',
                'CONFIG_BOOTCOMMAND=""', 'CONFIG_DRAM_CLK=552',
                'CONFIG_DRAM_ZQ=63351']:
    assert setting in s, setting
for name in ['UART0_PORT_F', 'MMC_WRITE', 'CMD_SAVEENV', 'NAND', 'SPL_NAND_SUPPORT']:
    assert f'CONFIG_{name}=y' not in s, name
CHECK
make -C /src O=/out -j6 EXT_DTB=/out/uboot.dtb all
arm-linux-gnueabihf-readelf -h /out/u-boot > /out/elf-header.txt
