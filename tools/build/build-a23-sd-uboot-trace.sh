#!/bin/sh
set -eu
export CROSS_COMPILE=arm-linux-gnueabihf-
cp -a /previous/. /out/
/src/scripts/config --file /out/.config \
    --set-str PREBOOT 'mw.l 0x01c20cb8 0; bootz 0x42000000 - 0x43000000'
make -C /src O=/out olddefconfig
cat >> /out/uboot.dts <<'DTS'
/* Keep the 16s diagnostic watchdog running until the Linux handoff. */
&{/soc/watchdog@1c20ca0} { status = "disabled"; };
DTS
dtc -I dts -O dtb -o /out/uboot.dtb /out/uboot.dts
make -C /src O=/out -j6 EXT_DTB=/out/uboot.dtb all
arm-linux-gnueabihf-gcc -nostdlib -static -Wl,--build-id=none,-Ttext=0x41004000 \
    -o /out/watchdog-entry.elf /work/a23-uboot-watchdog-entry.S
arm-linux-gnueabihf-objcopy -O binary /out/watchdog-entry.elf /out/watchdog-entry.bin
arm-linux-gnueabihf-objdump -d /out/watchdog-entry.elf > /out/watchdog-entry.dis
arm-linux-gnueabihf-nm -n /out/u-boot > /out/symbols.txt
