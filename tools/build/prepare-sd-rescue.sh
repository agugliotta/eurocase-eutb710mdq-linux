#!/bin/sh
# Reuse the existing Buildroot target without rebuilding packages.
set -eu
root=/tmp/tablet-rescue-root
mkdir "$root"
cp -a /build/target/. "$root/"
cp /work/sd-rescue-init.sh "$root/init"
chmod 0755 "$root/init"
mknod "$root/dev/console" c 5 1
mknod "$root/dev/null" c 1 3
python3 - "$root" <<'PATCH'
from pathlib import Path
import sys
p = Path(sys.argv[1])
s = p / 'etc/init.d/setup-usb'
text = s.read_text()
assert text.count('logger -t usb ') == 2
s.write_text(text.replace('logger -t usb ', 'echo '))
s = p / 'usr/bin/run-debug-console'
text = s.read_text()
assert text.count('EUROCASE_SD_DEBUG_CONSOLE') == 1
s.write_text(text.replace('EUROCASE_SD_DEBUG_CONSOLE', 'EUROCASE_RAM_RESCUE_DEBUG'))
PATCH
qemu-arm -L "$root" "$root/bin/busybox" sh -n "$root/init"
qemu-arm -L "$root" "$root/bin/busybox" sh -n "$root/etc/init.d/setup-usb"
cd "$root"
find . -print0 | LC_ALL=C sort -z | cpio --null -o --format=newc --owner=0:0 2>/out/cpio.log | gzip -n > /out/initramfs.cpio.gz
test "$(stat -c %s /out/initramfs.cpio.gz)" -lt 16777216
gzip -t /out/initramfs.cpio.gz
fdtput -t s /out/board.dtb /chosen bootargs 'console=tty0 maxcpus=2 clk_ignore_unused loglevel=7 panic=0 rdinit=/init consoleblank=0'
fdtput -t x /out/board.dtb /chosen linux,initrd-start 44000000
size=$(stat -c %s /out/initramfs.cpio.gz)
end=$(printf '%x' "$((0x44000000 + size))")
fdtput -t x /out/board.dtb /chosen linux,initrd-end "$end"
# USB0 debug must not depend on the USB1/Wi-Fi PMIC supply during rescue.
fdtput -d /out/board.dtb /soc/phy@1c19400 usb1_vbus-supply
fdtput -t s /out/board.dtb /soc/usb@1c1a000 status disabled
fdtput -t s /out/board.dtb /soc/usb@1c1a400 status disabled
dtc -I dtb -O dts /out/board.dtb > /out/board.dts
python3 - "$size" <<'PATCH'
from pathlib import Path
import sys
p = Path('/out/board.dts')
s = p.read_text()
assert s.count('/dts-v1/;') == 1
p.write_text(s.replace('/dts-v1/;', f'/dts-v1/;\n/memreserve/ 0x44000000 0x{int(sys.argv[1]):x};', 1))
PATCH
dtc -I dts -O dtb -o /out/board.dtb /out/board.dts
fdtget /out/board.dtb /chosen bootargs
