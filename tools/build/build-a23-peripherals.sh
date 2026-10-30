#!/bin/sh
set -eu
export ARCH=arm
cp -a /previous/. /out/
cp /baseline/kernel.config /out/.config
/src/scripts/config --file /out/.config \
  --set-str INITRAMFS_SOURCE /work/peripherals-initramfs.list \
  --set-str LOCALVERSION -eutb710mdq-periph1 \
  --disable U_SERIAL_CONSOLE \
  --enable INPUT --enable INPUT_EVDEV --enable INPUT_TOUCHSCREEN \
  --enable TOUCHSCREEN_SILEAD --enable IIO --enable BMC150_ACCEL \
  --enable BMC150_ACCEL_I2C --enable I2C_CHARDEV \
  --enable USB_EHCI_HCD --enable USB_EHCI_HCD_PLATFORM \
  --enable USB_OHCI_HCD --enable USB_OHCI_HCD_PLATFORM \
  --disable PM_DEVFREQ --disable HID_SUPPORT --disable USB_HID --disable RC_CORE
make -C /src O=/out olddefconfig
python3 - <<'PY'
from pathlib import Path
s = Path('/out/.config').read_text().splitlines()
for entry in ['CONFIG_USB_G_SERIAL=y', 'CONFIG_USB_MUSB_GADGET=y',
              'CONFIG_TOUCHSCREEN_SILEAD=y', 'CONFIG_BMC150_ACCEL_I2C=y',
              'CONFIG_USB_EHCI_HCD_PLATFORM=y', 'CONFIG_USB_OHCI_HCD_PLATFORM=y']:
    assert entry in s, entry
for symbol in ['MTD', 'MMC', 'ATA', 'SCSI', 'USB_STORAGE', 'NET', 'CPU_FREQ',
               'MODULES', 'U_SERIAL_CONSOLE', 'PM_DEVFREQ']:
    assert f'CONFIG_{symbol}=y' not in s, symbol
PY
arm-linux-gnueabihf-gcc -static -Os -Wall -Wextra -Werror \
  -o /out/read-events /work/read-input-events.c
make -C /src O=/out -j"${JOBS:-6}" zImage
arm-linux-gnueabihf-gcc -E -nostdinc -undef -D__DTS__ -x assembler-with-cpp \
  -I/src/arch/arm/boot/dts/allwinner -I/src/include \
  /board/sun8i-a23-eurocase-eutb710mdq-peripherals.dts > /out/eurocase-peripherals.dts
dtc -I dts -O dtb -o /out/eurocase-peripherals.dtb /out/eurocase-peripherals.dts
