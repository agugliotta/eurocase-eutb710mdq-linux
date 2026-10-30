#!/bin/sh
# Only the separately prepared SD power kernel is eligible for active controls.
set -eu
grep -qx 'CONFIG_LOCALVERSION="-eutb710mdq-sd3power"' /candidate/kernel/kernel.config
grep -qx 'CONFIG_SUNXI_WATCHDOG=y' /candidate/kernel/kernel.config
/out/host/bin/arm-linux-gcc -Os -D_GNU_SOURCE -DPANEL_SD_BOOT -DPANEL_POWER_ACTIONS \
    -Wall -Wextra -Werror /work/build/tablet-poc.c \
    -o /candidate/tablet-poc -lasound -lm
qemu-arm -L /out/target /candidate/tablet-poc --self-check
