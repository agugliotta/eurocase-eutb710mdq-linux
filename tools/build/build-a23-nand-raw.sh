#!/bin/sh
set -eu
export ARCH=arm
cp -a /previous/. /out/
/src/scripts/config --file /out/.config --set-str LOCALVERSION -eutb710mdq-nandraw1
make -C /src O=/out olddefconfig
make -C /src O=/out -j6 zImage
arm-linux-gnueabihf-gcc -E -nostdinc -undef -D__DTS__ -x assembler-with-cpp \
    -I/board -I/src/arch/arm/boot/dts/allwinner -I/src/include \
    /board/sun8i-a23-eurocase-eutb710mdq-nand-raw.dts > /out/board.dts
dtc -I dts -O dtb -o /out/board.dtb /out/board.dts
