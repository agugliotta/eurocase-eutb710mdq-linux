#!/bin/sh
set -eu
export ARCH=arm
cp -a /previous/. /out/
/src/scripts/config --file /out/.config --set-str LOCALVERSION -eutb710mdq-nandid1 \
    --enable MTD --enable MTD_RAW_NAND --enable MTD_NAND_SUNXI \
    --disable MTD_CHAR --disable MTD_BLOCK --disable MTD_UBI
make -C /src O=/out olddefconfig
make -C /src O=/out -j6 zImage
arm-linux-gnueabihf-gcc -E -nostdinc -undef -D__DTS__ -x assembler-with-cpp \
    -I/board -I/src/arch/arm/boot/dts/allwinner -I/src/include \
    /board/sun8i-a23-eurocase-eutb710mdq-nand-id.dts > /out/board.dts
dtc -I dts -O dtb -o /out/board.dtb /out/board.dts
