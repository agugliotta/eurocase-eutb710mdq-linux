#!/bin/sh
# Temporary RAM-only diagnostic init; never mount or write the SD.
export PATH=/sbin:/usr/sbin:/bin:/usr/bin
mount -t devtmpfs devtmpfs /dev
exec </dev/console >/dev/console 2>&1
mount -t proc proc /proc
mount -t sysfs sysfs /sys
mount -t tmpfs -o mode=0755,size=16m tmpfs /run
mount -t tmpfs -o mode=1777,size=32m tmpfs /tmp
mkdir -p /dev/pts /run/log /run/lock /run/tmp /sys/kernel/debug
mount -t devpts devpts /dev/pts
mount -t debugfs debugfs /sys/kernel/debug
hostname tablet-ram-rescue
echo EUROCASE_RAM_RESCUE
/etc/init.d/setup-usb
echo "USB setup status: $?"
sleep 3
echo '=== MMC / PMIC diagnostics ==='
dmesg | grep -Ei 'mmc|rsb|axp|regulator|defer|error'
cat /proc/partitions
cat /sys/kernel/debug/devices_deferred
echo '=== SD remains unmounted; USB0 provides debug shell ==='
while :; do
    /usr/bin/run-debug-console
    sleep 1
done
