#!/bin/sh
set -eu
test ! -e /out/rootfs
mkdir -p /out/rootfs/bin /out/rootfs/dev /out/rootfs/proc /out/rootfs/sys /out/rootfs/tmp /out/rootfs/var /out/rootfs/etc /out/rootfs/root /out/rootfs/usr/bin
cp /opt/busybox-root/bin/busybox /out/rootfs/bin/
qemu-arm /out/rootfs/bin/busybox --list > /out/busybox-applets.txt
while read -r app; do
    case "$app" in */*|busybox|'') continue;; esac
    ln -s busybox "/out/rootfs/bin/$app"
done < /out/busybox-applets.txt
cp -a /poc/. /out/rootfs/poc/
printf '#!/bin/sh\nexec /poc/lib/ld-linux-armhf.so.3 --library-path /poc/lib /poc/bin/tablet-poc --ui\n' > /out/rootfs/usr/bin/start-poc
chmod 755 /out/rootfs/usr/bin/start-poc
printf 'NAME="Eurocase RAM POC"\nID=eutb710mdq-poc\nPRETTY_NAME="Eurocase BusyBox RAM rootfs"\n' > /out/rootfs/etc/os-release
printf 'root:x:0:0:root:/root:/bin/sh\n' > /out/rootfs/etc/passwd
printf 'root:x:0:\n' > /out/rootfs/etc/group
printf '127.0.0.1 localhost\n::1 localhost\n' > /out/rootfs/etc/hosts
chmod 1777 /out/rootfs/tmp
qemu-arm /out/rootfs/bin/busybox sh -c 'test "$((6*7))" = 42; echo ROOTFS_ARM_SHELL_OK'
qemu-arm /out/rootfs/poc/lib/ld-linux-armhf.so.3 --library-path /out/rootfs/poc/lib /out/rootfs/poc/bin/tablet-poc --self-check
cp /opt/busybox-package/*.deb /out/
tar --sort=name --mtime=@0 --owner=0 --group=0 --numeric-owner -C /out/rootfs -czf /out/rootfs.tar.gz .
