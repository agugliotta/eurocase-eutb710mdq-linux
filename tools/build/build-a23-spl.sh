#!/bin/sh
set -eu
make -C /src O=/out q8_a23_tablet_800x480_defconfig
/src/scripts/config --file /out/.config \
  --set-val DRAM_CLK 552 --set-val DRAM_ZQ 63351 \
  --enable DRAM_ODT_EN --set-val DRAM_ODT_CORRECTION 0 \
  --set-val CONS_INDEX 1 --enable UART0_PORT_F \
  --set-val AXP_DCDC1_VOLT 3000 --set-val AXP_DCDC2_VOLT 1100 \
  --set-val AXP_DCDC3_VOLT 1260 --set-val AXP_DCDC4_VOLT 0 \
  --set-val AXP_DCDC5_VOLT 1500 \
  --disable VIDEO --disable SPL_VIDEO \
  --disable MMC --disable SPL_MMC --disable CMD_MMC \
  --disable NAND --disable SPL_NAND_SUPPORT --disable CMD_NAND \
  --disable SPI_FLASH --disable SPL_SPI --disable CMD_SF \
  --disable ENV_IS_IN_FAT --disable ENV_IS_IN_MMC \
  --enable ENV_IS_NOWHERE --disable CMD_SAVEENV \
  --disable USB_STORAGE --disable USB_EHCI_HCD --disable USB_OHCI_HCD \
  --disable USB_MUSB_HOST --disable TOOLS_MKEFICAPSULE
make -C /src O=/out olddefconfig
python3 - <<'PY'
from pathlib import Path
s=Path('/out/.config').read_text().splitlines()
for value in ['CONFIG_MACH_SUN8I_A23=y','CONFIG_DRAM_CLK=552','CONFIG_DRAM_ZQ=63351','CONFIG_DRAM_ODT_EN=y','CONFIG_UART0_PORT_F=y','CONFIG_CONS_INDEX=1','CONFIG_ENV_IS_NOWHERE=y','CONFIG_AXP_DCDC3_VOLT=1260']:
    assert value in s, value
for symbol in ['SPL_NAND_SUPPORT','SPL_MMC','SPL_MMC_WRITE','SPL_SPI','SPL_VIDEO','SPL_OF_CONTROL','ENV_IS_IN_FAT','ENV_IS_IN_MMC']:
    assert f'CONFIG_{symbol}=y' not in s, symbol
PY
make -C /src O=/out -j"${JOBS:-4}" spl/u-boot-spl.bin
test -s /out/spl/sunxi-spl.bin
arm-linux-gnueabihf-nm --defined-only /out/spl/u-boot-spl > /out/spl-symbols.txt
arm-linux-gnueabihf-objdump -d /out/spl/u-boot-spl > /out/spl-disassembly.txt
