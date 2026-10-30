#!/bin/sh
# Isolate the unsupported legacy PRCM bindings in U-Boot, keeping Linux's DT intact.
set -eu
export CROSS_COMPILE=arm-linux-gnueabihf-
cp -a /previous/. /out/
/src/scripts/config --file /out/.config \
    --disable AXP_GPIO --disable REGULATOR_AXP \
    --disable REGULATOR_AXP_DRIVEVBUS --disable REGULATOR_AXP_USB_POWER
make -C /src O=/out olddefconfig
python3 - <<'CHECK'
from pathlib import Path
s = Path('/out/.config').read_text().splitlines()
for name in ['AXP_GPIO', 'REGULATOR_AXP', 'MMC_WRITE', 'SPL_MMC_WRITE', 'NAND']:
    assert f'CONFIG_{name}=y' not in s, name
for setting in ['CONFIG_AXP221_POWER=y', 'CONFIG_AXP_PMIC_BUS=y',
                'CONFIG_SYS_I2C_SUN8I_RSB=y', 'CONFIG_DM_REGULATOR_FIXED=y',
                'CONFIG_AXP_DCDC1_VOLT=3000', 'CONFIG_AXP_DCDC3_VOLT=1260',
                'CONFIG_USB_FUNCTION_ACM=y', 'CONFIG_BOOTDELAY=-1']:
    assert setting in s, setting
CHECK
cp /previous/uboot.dts /out/uboot.dts
cat >> /out/uboot.dts <<'DTS'
/ {
    uboot_sd_supply: uboot-sd-supply {
        compatible = "regulator-fixed";
        regulator-name = "sd-3v-already-set-by-spl";
        regulator-min-microvolt = <3000000>;
        regulator-max-microvolt = <3000000>;
        regulator-always-on;
    };
};
&{/soc/mmc@1c0f000} { vmmc-supply = <&uboot_sd_supply>; };
/* Only USB0 peripheral is used; leave the USB1/Wi-Fi rail under SPL control. */
&{/soc/phy@1c19400} { /delete-property/ usb1_vbus-supply; };
DTS
dtc -I dts -O dtb -o /out/uboot.dtb /out/uboot.dts
make -C /src O=/out -j6 EXT_DTB=/out/uboot.dtb all
