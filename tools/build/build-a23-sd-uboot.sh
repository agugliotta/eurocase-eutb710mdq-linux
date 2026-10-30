#!/bin/sh
set -eu
export CROSS_COMPILE=arm-linux-gnueabihf-
cp /baseline/u-boot-spl.config /out/.config
/src/scripts/config --file /out/.config \
    --disable UART0_PORT_F --disable SPL_SERIAL --disable REQUIRE_SERIAL_CONSOLE \
    --disable AXP_GPIO --disable REGULATOR_AXP \
    --disable REGULATOR_AXP_DRIVEVBUS --disable REGULATOR_AXP_USB_POWER \
    --enable MMC --enable SPL_MMC --enable MMC_SUNXI --enable CMD_MMC \
    --disable MMC_WRITE --disable SPL_MMC_WRITE \
    --enable CMD_FAT --enable FS_FAT --disable FAT_WRITE \
    --disable VIDEO --disable VIDEO_SUNXI --disable SPL_VIDEO \
    --disable NAND --disable SPL_NAND_SUPPORT --disable CMD_NAND \
    --disable USB_GADGET --disable USB_STORAGE \
    --disable ENV_IS_IN_MMC --disable ENV_IS_IN_FAT --enable ENV_IS_NOWHERE \
    --disable CMD_SAVEENV --disable DISTRO_DEFAULTS --disable BOOTSTD \
    --disable EFI_LOADER --disable TOOLS_MKEFICAPSULE --disable SPL_LOAD_FIT \
    --set-val BOOTDELAY 0 --enable USE_BOOTCOMMAND \
    --set-str BOOTCOMMAND 'if mmc dev 0; then if fatload mmc 0:1 0x43100000 boot.scr; then source 0x43100000; fi; fi'
make -C /src O=/out olddefconfig
python3 - <<'CHECK'
from pathlib import Path
s = Path('/out/.config').read_text().splitlines()
for entry in ['CONFIG_DRAM_CLK=552', 'CONFIG_DRAM_ZQ=63351',
              'CONFIG_DRAM_ODT_EN=y', 'CONFIG_AXP_DCDC3_VOLT=1260',
              'CONFIG_MMC=y', 'CONFIG_SPL_MMC=y', 'CONFIG_MMC_SUNXI=y',
              'CONFIG_ENV_IS_NOWHERE=y', 'CONFIG_CMD_BOOTZ=y']:
    assert entry in s, entry
for name in ['UART0_PORT_F', 'SPL_SERIAL', 'REQUIRE_SERIAL_CONSOLE', 'MTD',
             'NAND', 'SPL_NAND_SUPPORT', 'CMD_NAND', 'MMC_WRITE',
             'SPL_MMC_WRITE', 'FAT_WRITE', 'CMD_SAVEENV', 'VIDEO', 'BOOTSTD',
             'AXP_GPIO', 'REGULATOR_AXP']:
    assert f'CONFIG_{name}=y' not in s, name
CHECK
# Linux's DT has no binman metadata. Add the standard sunxi image layout
# only to U-Boot's control DT; leave the Linux board.dtb untouched.
dtc -I dtb -O dts /kernel/board.dtb > /out/uboot.dts
cat >> /out/uboot.dts <<'DTS'
/ {
    uboot_sd_supply: uboot-sd-supply {
        compatible = "regulator-fixed";
        regulator-name = "sd-3v-already-set-by-spl";
        regulator-min-microvolt = <3000000>;
        regulator-max-microvolt = <3000000>;
        regulator-always-on;
    };
    binman {
        multiple-images;
        u-boot-sunxi-with-spl {
            filename = "u-boot-sunxi-with-spl.bin";
            pad-byte = <0xff>;
            blob {
                filename = "spl/sunxi-spl.bin";
                min-size = <0x8000>;
            };
            u-boot-img { };
        };
    };
};
// Keep the SPL's validated supply; U-Boot lacks this board's legacy PRCM clocks.
&{/soc/mmc@1c0f000} { vmmc-supply = <&uboot_sd_supply>; };
DTS
dtc -I dts -O dtb -o /out/uboot.dtb /out/uboot.dts
make -C /src O=/out -j"${JOBS:-6}" EXT_DTB=/out/uboot.dtb all
/out/tools/mkimage -A arm -T script -C none -n 'Eurocase SD POC' \
    -d /work/sd-boot.cmd /out/boot.scr
