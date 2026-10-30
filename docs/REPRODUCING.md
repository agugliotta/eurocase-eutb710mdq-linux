# Reproducing the work

There are two useful goals: reproduce the final microSD system, or investigate
how an unfamiliar tablet's board configuration was established. The [bring-up
account](BRINGUP.md) explains the latter. This guide lays out the order of work
and the evidence to require before moving to the next stage.

**Current limitation:** this workspace cannot yet be presented as a self-contained
fresh-clone build. [BUILD.md](BUILD.md) lists the exact missing/export-dependent
inputs. The commands below identify existing tools and stages; they do not
claim to replace those inputs or provide a verified end-to-end release recipe.

## 1. Compare your tablet and preserve its configuration

On stock Android with ADB access, collect identity and live configuration first.
These commands read metadata; they require a working Android shell and permissions
that may differ on another unit:

```sh
adb devices -l
adb shell 'id; cat /proc/version; cat /proc/cpuinfo; cat /proc/cmdline'
adb shell 'cat /proc/partitions; cat /proc/modules'
adb shell 'ls -l /dev/block/by-name'
adb shell dmesg > stock-dmesg.txt
```

Select the intended device explicitly if more than one is present. Save results
in a new local directory. Compare the SoC, loaded touch/Wi-Fi drivers and board
configuration against [HARDWARE.md](HARDWARE.md). Keep device serials, network
identifiers and private data out of a public report.

The original acquisition also pulled `/proc/config.gz`, vendor modules, board
configuration, init/fstab and selected stock partitions. The partition names and
sizes must be checked on the actual device before reading them. Android's block
nodes expose logical partitions, not necessarily physical boot0/boot1 or NAND
OOB/ECC. A collection of logical images is not a complete physical restore backup.

## 2. Recover board-specific inputs

Use the acquired boot-resource FEX alongside live logs and vendor drivers to
identify active hardware. Preserve original input hashes before extracting or
converting anything.

The touch converter expects the original board file at
`acquisition/originals/board-config/gslX680.cfg` and extracts the exact
`gslX680_fw_data_1024x600` array:

```sh
python3 tools/build/extract-g739-touch-fw.py
```

It checks parsing/register bounds and emits Linux offset/value pairs plus
metadata under `analysis/peripherals/firmware/silead/`. The original board file
is not supplied by a clean source checkout today. Do not run this conversion
against an arbitrary table simply because its dimensions match.

For Wi-Fi, preserve and inspect the unit's stock calibration source and separate
MAC-generation behavior. The mainline fallback must recreate the calibration
shadow, not program OTP or clone another unit's identity.

## 3. Build the board system as regular files

Recover the tracked patches/configuration inputs listed in [BUILD.md](BUILD.md),
then provision the pinned Linux, U-Boot, Buildroot and compiler inputs. The
existing base-stage entry point is:

```sh
sh tools/build/prepare-sd.sh <new-output-directory>
```

This script builds regular files, not a physical card. It requires local source
trees, overlays, older baseline configs, firmware and Docker setup. It builds an
earlier base system, not the installed v5 image by itself. Later power and Wi-Fi
kernel/image stages must also be reproduced with their exact inputs.

The public source release still needs a unified build entry point that assembles
these stages from tracked source instead of historical image baselines. There
is no honest single-command replacement to provide until that work is done.

Expected outputs include `zImage`, `board.dtb`, `boot.scr`,
`u-boot-sunxi-with-spl.bin`, `rootfs.squashfs`, effective configurations and
`sdcard.img`. Save source revisions, toolchain versions and hashes in a manifest.

## 4. Verify offline before touching a card

Require image-layout checks, SPL checksum, kernel/DT/script header checks,
required configuration assertions and rootfs inspection. The existing tooling
includes `tools/build/check-sd-preparation.py` and application self-checks under
qemu-arm. Use the checks appropriate to the produced image revision; later
images cannot be identified merely by the success of an older baseline's tests.

Offline success establishes properties of files. It does not establish that a
screen, card interface or power sequence works on the real tablet.

## 5. Write and validate the resulting SD system

Follow [INSTALLATION.md](INSTALLATION.md): identify the removable card afresh,
write the whole image, compare a full readback, eject, insert while powered off,
and boot. Record the exact image hash and test results.

Validate one observable behavior at a time: boot, console, display/colors,
touch orientation/edges, Home, orderly restart and startup with USB connected.
Use current USB discovery rather than copied device paths from an earlier log.
Keep an earlier verified SD image so a new experiment can be compared against it.

Audio tones, NAND operations and camera experiments are not installation checks.
They require their own deliberately scoped investigation.

## 6. Record what your result actually demonstrates

A useful reproduction report includes hardware identifiers without personal
serials, component revisions, image hash, build log, relevant sanitized boot log,
steps performed, observed output and failures. Separate tests passed from tests
not attempted. Compare unresolved behavior with [OPEN-ISSUES.md](OPEN-ISSUES.md).

For historical FEL research, require a reviewed board-specific SPL and memory
layout, saved input artifacts and readback checks before execution. The fact
that an old script exists is not an instruction to run it on a live tablet.
A normal SD installation does not require repeating physical NAND extraction.
