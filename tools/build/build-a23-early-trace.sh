#!/bin/sh
set -eu
# Patch an ephemeral source tree; retain both upstream and prior build evidence.
cp -a /original /src
cp -a /previous/. /out/
python3 /work/instrument-a23-early-trace.py
sh /work/build-a23-uboot-usb.sh
cp /src/arch/arm/cpu/armv7/start.S /out/instrumented-start.S
cp /src/include/initcall.h /out/instrumented-initcall.h
arm-linux-gnueabihf-objdump -d /out/u-boot > /out/uboot-disassembly.txt
