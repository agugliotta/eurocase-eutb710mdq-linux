# Owner-supplied board files

The build needs two stock files from your own supported tablet. These contain
the touch program and board Wi-Fi calibration, not your Wi-Fi password. They
are intentionally ignored by Git and must not be committed.

From the repository root, with stock Android running and ADB access available:

```sh
adb devices -l
adb pull /system/etc/config/polaris-g739/gslX680.cfg firmware/gslX680.cfg
adb pull /system/etc/config/polaris-g739/rtk_efuse_8188etv.map firmware/rtk_efuse_8188etv.map
make image
```

Select the intended tablet with `adb -s YOUR_SERIAL ...` if more than one device
is connected. ADB access and root permissions vary; the original unit already
provided root ADB. These commands only read the two files. Do not substitute a
file from another model merely because its name matches. If the stock paths
are missing or access is denied, resolve that before building; do not run a
flashing or recovery command to work around it.

Already have local backups? Copy those two files here instead. No live tablet
connection is needed to build after that. The build validates the exact touch
table name and calibration structure without logging their contents.

The Realtek radio program is fetched automatically from linux-firmware tag
20230210, checked by SHA-256 and accompanied by its redistribution license.
The firmware programs/calibration are embedded in the kernel to retain the
previously used early-probe behavior. The resulting image is an **owner-local
build**, not a cleared binary redistribution. Silead redistribution rights and
non-GPL firmware packaging still need resolution before publishing a binary.
