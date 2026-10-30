#!/bin/sh
set -eu
export ARCH=arm
make -C /src O=/out sunxi_defconfig
/src/scripts/config --file /out/.config \
  --enable BLK_DEV_INITRD --set-str INITRAMFS_SOURCE /work/linux-usb-initramfs.list \
  --enable DEVTMPFS --enable DEVTMPFS_MOUNT --enable BINFMT_ELF --enable BINFMT_SCRIPT \
  --enable PROC_FS --enable SYSFS --enable TTY --enable PRINTK \
  --enable IKCONFIG --enable IKCONFIG_PROC \
  --enable USB --enable USB_GADGET --enable USB_MUSB_HDRC \
  --enable USB_MUSB_SUNXI --enable USB_MUSB_GADGET \
  --disable USB_MUSB_HOST --disable USB_MUSB_DUAL_ROLE \
  --enable USB_G_SERIAL --enable U_SERIAL_CONSOLE \
  --disable USB_CONFIGFS --disable USB_ETH --disable USB_MASS_STORAGE \
  --disable USB_EHCI_HCD --disable USB_OHCI_HCD --disable USB_XHCI_HCD \
  --disable USB_STORAGE --disable USB_UAS \
  --disable MTD --disable MMC --disable ATA --disable SCSI --disable NVME_CORE \
  --disable DRM --disable FB --disable SOUND --disable MEDIA_SUPPORT \
  --disable INPUT --disable NET --disable WLAN --disable BT \
  --disable PM --disable CPU_FREQ --disable CPU_IDLE --disable WDT \
  --disable WATCHDOG --disable MODULES --disable DEBUG_INFO \
  --disable EXT4_FS --disable VFAT_FS --disable NFS_FS --disable EFI \
  --set-str LOCALVERSION -eutb710mdq-usbdiag --disable LOCALVERSION_AUTO
make -C /src O=/out olddefconfig
python3 - <<'PY'
from pathlib import Path
s = Path('/out/.config').read_text().splitlines()
for entry in ['CONFIG_ARCH_SUNXI=y', 'CONFIG_USB_MUSB_SUNXI=y',
              'CONFIG_USB_MUSB_GADGET=y', 'CONFIG_USB_G_SERIAL=y',
              'CONFIG_U_SERIAL_CONSOLE=y', 'CONFIG_DEVTMPFS=y',
              'CONFIG_INITRAMFS_SOURCE="/work/linux-usb-initramfs.list"']:
    assert entry in s, entry
for symbol in ['MTD', 'MMC', 'USB_STORAGE', 'ATA', 'SCSI', 'NET', 'MODULES',
               'USB_MUSB_HOST', 'USB_MUSB_DUAL_ROLE', 'CPU_FREQ']:
    assert f'CONFIG_{symbol}=y' not in s, symbol
PY
make -C /src O=/out -j"${JOBS:-6}" zImage
arm-linux-gnueabihf-readelf -h /out/vmlinux > /out/vmlinux-header.txt
arm-linux-gnueabihf-gcc -E -nostdinc -undef -D__DTS__ -x assembler-with-cpp \
  -I/src/arch/arm/boot/dts/allwinner -I/src/include \
  /board/sun8i-a23-eurocase-eutb710mdq-linux-usb.dts > /out/eurocase-usb.dts
dtc -I dts -O dtb -o /out/eurocase-usb.dtb /out/eurocase-usb.dts
arm-linux-gnueabihf-as -o /out/linux-entry.o /work/a23-linux-entry.S
arm-linux-gnueabihf-ld -Ttext=0x41000000 -e _start -o /out/linux-entry.elf /out/linux-entry.o
arm-linux-gnueabihf-objcopy -O binary /out/linux-entry.elf /out/linux-entry.bin
arm-linux-gnueabihf-objdump -d /out/linux-entry.elf > /out/linux-entry-disassembly.txt
arm-linux-gnueabihf-as -o /out/cpu-probe.o /work/a23-fel-cpu-probe.S
arm-linux-gnueabihf-ld -Ttext=0x41002000 -e _start -o /out/cpu-probe.elf /out/cpu-probe.o
arm-linux-gnueabihf-objcopy -O binary /out/cpu-probe.elf /out/cpu-probe.bin
arm-linux-gnueabihf-objdump -d /out/cpu-probe.elf > /out/cpu-probe-disassembly.txt
