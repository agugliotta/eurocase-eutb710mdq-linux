#!/bin/sh
set -eu
host=${1:?Mac link-local IPv6 required}
digest=${2:?Expected rootfs SHA256 required}
case "$host" in fe80:*) ;; *) echo 'Expected fe80:: link-local address'; exit 2;; esac
case "$host" in *[!0-9a-fA-F:]*) exit 2;; esac
test "${#digest}" = 64
case "$digest" in *[!0-9a-f]*) exit 2;; esac
test ! -e /run/usbroot
wget -O /usb-rootfs.tar.gz "http://[$host%usb0]:8080/rootfs.tar.gz"
printf '%s  /usb-rootfs.tar.gz\n' "$digest" | sha256sum -c -
mkdir -p /run/usbroot
mount -t tmpfs -o size=64m,mode=755 tmpfs /run/usbroot
gunzip -c /usb-rootfs.tar.gz | tar -xf - -C /run/usbroot
mount --bind /dev /run/usbroot/dev
mount --bind /proc /run/usbroot/proc
mount --bind /sys /run/usbroot/sys
mount -t tmpfs -o size=16m,mode=1777 tmpfs /run/usbroot/tmp
mount -t tmpfs -o size=16m,mode=755 tmpfs /run/usbroot/var
mount -t tmpfs -o remount,ro tmpfs /run/usbroot
chroot /run/usbroot /bin/busybox sh -c 'test "$((6*7))" = 42; cat /etc/os-release; echo USB_ROOTFS_SHELL_OK'
chroot /run/usbroot /poc/lib/ld-linux-armhf.so.3 --library-path /poc/lib /poc/bin/tablet-poc --self-check
setsid chroot /run/usbroot /usr/bin/start-poc < /dev/null > /usbroot-ui.log 2>&1 &
echo "USB_ROOTFS_UI_LAUNCH_PID=$!"
echo USB_ROOTFS_READY
