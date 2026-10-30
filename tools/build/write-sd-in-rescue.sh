#!/bin/sh
# This initial POC update accepts only the identified SD and its FEL-probe state.
set -eu
test "$#" -eq 3 || test "$#" -eq 4
image=$1
expected_sha=$2
expected_bytes=$3
test "${4:---check-only}" = --check-only || test "$4" = --write
test "${#expected_sha}" -eq 64
case "$expected_sha" in *[!0-9a-f]*) exit 1;; esac
test "$expected_bytes" = 101711872
test "$(hostname)" = tablet-ram-rescue
test "$(awk '$2 == "/" { print $1, $3 }' /proc/mounts)" = 'rootfs rootfs'
test -f "$image"
test "$(wc -c < "$image")" -eq "$expected_bytes"
test "$(sha256sum "$image" | cut -d ' ' -f 1)" = "$expected_sha"
device=/dev/mmcblk0
test -b "$device"
test "$(cat /sys/block/mmcblk0/device/type)" = SD
test "$(cat /sys/block/mmcblk0/size)" = 30535680
case "$(readlink -f /sys/block/mmcblk0)" in */1c0f000.mmc/*) ;; *) exit 1;; esac
if awk '$1 ~ /^\/dev\/mmcblk0/ { found=1 } END { exit !found }' /proc/mounts; then
    echo 'SD is mounted; refusing write' >&2
    exit 1
fi
prefix=$(dd if="$device" bs=512 skip=16 count=16 2>/dev/null | sha256sum | cut -d ' ' -f 1)
test "$prefix" = 2ccec08a026840571f3804671ba72afae840db27112a43f2b1f122075bc808bc
echo "SD_PREFLIGHT_OK $device $expected_bytes $expected_sha"
test "${4:---check-only}" = --write || exit 0
dd if="$device" of=/sd-prefix-before-v2.bin bs=1024 count=1024
dd if="$image" of="$device" bs=1048576 conv=fsync
sync
actual=$(head -c "$expected_bytes" "$device" | sha256sum | cut -d ' ' -f 1)
test "$actual" = "$expected_sha"
echo "SD_WRITE_READBACK_VERIFIED $expected_sha"
