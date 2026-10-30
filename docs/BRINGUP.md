# How this tablet reached a working Linux system

This account reconstructs the experiments performed on one Eurocase EUTB_710MDQ
between October 26 and October 29, 2026. It explains the reasoning behind the
working microSD port, including the paths that did not work. It is not a claim
that every intermediate diagnostic image should be run on another tablet.

The practical reproduction path is to build the final SD system. The historical
FEL and NAND experiments explain how its hardware configuration was discovered;
NAND extraction is not a requirement for running Linux from a card.

Historical script names below refer to the original research tree in the initial
Git commit. The active source tree now keeps only the supported build path;
see [BUILD.md](BUILD.md) to build without those experiments.

## 1. Identify the real hardware before choosing a board configuration

The starting point was stock Android 4.2.2 with a 3.4.39 kernel and root ADB.
The product strings were `polaris_wifionly` / `polaris-wifionly`. CPU information
and the vendor kernel configuration identified Allwinner A23, rather than
assuming the SoC from the tablet's marketing name.

Stock boot/recovery/resource/environment partitions, kernel configuration,
boot logs, vendor modules and board configuration were acquired. The Android
boot image was separated into kernel and ramdisk. `SCRIPT0.BIN` was recovered
from the boot-resource FAT filesystem and decoded as FEX board configuration.

FEX provided DRAM, regulator and LCD candidates. It was not treated as a complete
truth: it also contained an apparent AW5306 touchscreen configuration at 800×480,
while the running system loaded a GSLX680 driver and the display was 1024×600.
Vendor autodetection can leave unused candidates in configuration files.

**Reproduction checkpoint:** preserve your own stock artifacts and compare
configuration, loaded modules and live logs. Do not copy this unit's identifiers
or assume every FEX entry describes active hardware.

## 2. Reach a controllable boot environment

A physical FEL button sequence was not established. Stock recovery exposed ADB,
but its shell was unavailable because `/system/bin/sh` was not mounted there.
ADB pull still allowed acquisition of files and the misc partition.

Inspection of the stock reboot implementation showed that reboot arguments
are written into misc. After backing up misc, `adb reboot efex` was used and
the BootROM answered with `AWUSBFEX soc=00001650(A23)`. Thus this transition
was not entirely read-only, even though no firmware image was flashed.

**Reproduction checkpoint:** distinguish BootROM FEL from Android/recovery ADB.
Do not expect a shell or Linux console while FEL owns USB. Device addresses
change after reconnection. The model-specific physical entry method remains
unknown.

## 3. Initialize DRAM without installing a bootloader

A U-Boot SPL was built from the Q8 A23 configuration, using the stock-derived
DRAM and PMIC parameters. DRAM used 552 MHz, ZQ 63351 and ODT enabled. Storage
and environment-writing paths were disabled for the initial RAM experiment.

The 16 KiB candidate SPL executed and returned to FEL. Five patterns were
written to a backed-up 64 KiB window at `0x42000000`, read back, then the original
contents were restored and checked. Register observations and U-Boot's size
calculation were consistent with 1 GiB DRAM.

This proved a usable window and initialization path. It did not prove every
address, sustained stability or retention across temperature and load.

**Relevant source:** `tools/build/build-a23-spl.sh` and
`tools/build/test-fel-ram.py`.

## 4. Boot Linux directly to get USB observability

The early main U-Boot USB-console attempt did not provide the required visible
result. That failure was not used as evidence that Linux could not run. The
working route instead returned from SPL to FEL, uploaded a kernel and DTB,
verified their readback and jumped through a small ARM entry stub.

The first Linux 6.12 diagnostic used a built-in initramfs and stock static
BusyBox. The stub established the ARM kernel entry state. A USB CDC ACM shell
appeared with a kernel marker and native ARM CPU information. Persistent block
devices were disabled. Initially only one core was enabled to reduce variables;
later peripheral builds brought both cores online.

**What this established:** Linux was running on the physical tablet, with DRAM
and the USB peripheral controller usable. A black LCD at this stage was expected,
since the diagnostic did not enable the display.

**Relevant source:** `tools/build/a23-linux-entry.S`,
`tools/build/load-a23-linux-fel.py`, `tools/build/build-a23-linux-usb.sh`.

## 5. Bring up peripherals one at a time

The display needed more than a resolution copied from FEX. Stock configuration,
vendor module analysis and hardware observations were combined to describe the
panel power sequence, RGB output, backlight and VCOM PWM. The custom panel driver
and device tree produced a stable 1024×600 image; the user confirmed the color
bar order and visible text.

The touch firmware was extracted from the stock
`gslX680_fw_data_1024x600` table and converted to little-endian 32-bit
register/value pairs for Linux's Silead driver. An initial axis swap was removed
after physical tests. Five manual contacts established the correct orientation,
but bottom-edge Y values reached approximately 644–645 despite an advertised
maximum of 599. The stock driver also calls `gsl_alg_id_main` before reporting
input; mainline follows a different processing path. That difference is real,
but its exact contribution to scaling was not proved. Application-side Y/650
scaling was later used; it is not a full driver-level calibration.

Home and Power events were confirmed physically, and the accelerometer responded
to tilt. These were individual tests, not a blanket validation of every
peripheral or every operating condition.

**Relevant source:** `tools/board/`, `tools/build/patch-g739-panel.py`,
`tools/build/extract-g739-touch-fw.py`, `tools/build/read-input-events.c`.

## 6. Run a usable root filesystem before depending on SD

A later development build exposed USB networking alongside the console, fetched
a root filesystem over USB, verified it and ran it in read-only RAM with writable
temporary areas. A simple framebuffer/touch application made the tablet usable
without a desktop. This separated rootfs/application problems from SD boot issues.

The final panel uses a different USB configuration: two ACM functions, one for
console and one for metrics. The old ECM networking arrangement is historical.

## 7. Investigate NAND, then use microSD for the working system

Internal installation was explored. Raw NAND identification exposed a mismatch
between generic geometry assumptions and the stock device. Limited guarded
reads, scrambling reconstruction and BCH decoding recovered physical boot0 and
boot1. The accepted boot1 copy was 704512 bytes and passed checksum after two
matching reconstructions; another copy was rejected after an uncorrectable BCH
error. A good header alone had not been accepted as a complete loader.

This did not solve safe mainline NAND installation. MLC page pairing, bad-block
handling, ECC/read-retry and a complete restore procedure remained issues. UBI's
MLC rejection was not bypassed to force an installation. A userspace chroot test
under the vendor kernel demonstrated some ABI compatibility, not a complete
replacement operating system boot.

The delivered system therefore boots from microSD. NAND and eFuse were not
flashed/programmed. The NAND work is useful research, not a prerequisite or a
recommended installation sequence for another owner.

## 8. Resolve SD boot and make the root filesystem predictable

UART0 on PF2/PF4 conflicted with SD bus use and was disabled. USB remained the
console path. An SD rootwait problem was isolated to PB4 card detection: removing
the problematic pull-up made the card/partitions appear. The working DT uses
`broken-cd` polling rather than claiming a validated card-detect electrical setup.

The bootloader also needed to preserve the already established SD supply rather
than depend on legacy regulator/clock handling it did not support for this board.
The system then booted autonomously from SD through SPL and U-Boot.

Buildroot supplied a musl userspace and read-only SquashFS root. Runtime files
and logs live in RAM. Two ACM functions keep a debug shell separate from
application data. Init supervises the UI. Software restart required enabling
the sunxi watchdog/restart driver; this did not add a periodic watchdog daemon.

Earlier sessions sometimes entered Android with USB already attached. The final
sequence later passed startup with USB attached to both Mac and Proxmox hosts.
No isolated cause or specific USB boot fix was demonstrated for the earlier
observation.

**Relevant source:** `tools/buildroot/`,
`tools/board/sun8i-a23-eurocase-eutb710mdq-sd.dts`,
`tools/build/build-a23-sd-uboot.sh`, `tools/build/build-a23-power-kernel.sh`.

## 9. Recover the Wi-Fi configuration the stock driver actually used

Passive scanning worked earlier, but that did not prove association would work.
Stock driver analysis showed a board-specific external calibration-map loader:
512 bytes were parsed into a RAM shadow before adapter configuration. This was
not an eFuse programming operation. Stock MAC generation was a separate path;
copying a calibration file's MAC would not reproduce that behavior correctly.

A software fallback restored the calibration path for mainline. An association
attempt then exposed a userspace prerequisite: wpa_supplicant needed PF_PACKET,
so `CONFIG_PACKET=y` was added. WPA2 association, DHCP, ping, DNS and an HTTP
request subsequently passed. Credentials and a temporary MAC were used in RAM.

That experiment established connectivity, not a finished persistent Wi-Fi setup.
Automatic reconnection/configuration after reboot remains unimplemented.

## 10. Validate the final use case without overstating board support

The Proxmox application was first exercised with demo data, then connected to a
read-only host collector. The final v5 image starts the LVGL UI directly from SD.
Write/readback, startup with USB connected, touch filters, scrolling, Home and
UI restart with automatic metrics recovery were verified.

The dashboard is one application of the port. It does not establish camera,
speaker, suspend or long-term stability support. The [open questions](OPEN-ISSUES.md)
record those boundaries separately.

## Evidence behind this account

The following are local research records, often in Spanish and with historical
status sections. They are provenance references for preparing the public repo,
not files to publish wholesale. Later results supersede earlier pending states.

| Stage | Local record |
| --- | --- |
| Stock identification/acquisition | `INVESTIGACION.md` |
| FEL entry and its misc write | `analysis/bringup/FEL-ENTRY.md` |
| SPL and memory-window test | `analysis/bringup/runtime/RESULTADOS.md` |
| First mainline shell | `analysis/bringup/linux-usb/RESULTADOS.md` |
| LCD/touch/input observations | `analysis/peripherals/RESULTADOS.md` |
| USB RAM rootfs | `analysis/usb-root/RESULTADOS.md` |
| Physical loaders and NAND limitations | `analysis/install/boot1/RESULTADOS.md` |
| Autonomous SD and power support | `analysis/sd/README.md`, `analysis/sd/v3-power/README.md` |
| Wi-Fi calibration and association | `analysis/wifi/v1/stock-efuse-findings.md`, `analysis/wifi/v2/README.md` |
| Headphones and unresolved speaker | `analysis/audio/v1/README.md` |
| Final installed image | `analysis/panel/v5/README.md`, `analysis/panel/v5/install/hardware-test.json` |

A self-contained public version must include sanitized evidence excerpts and
all required source changes alongside these explanations. See [build gaps](BUILD.md).
