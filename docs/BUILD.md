# Build architecture and reproducibility

## Current state

The tested images were built using this workstation's source trees, generated
patches, earlier image/configuration baselines and Docker volumes. The sources
under `tools/` are valuable, but copying that directory alone is insufficient
to reproduce the installed image.

Do not describe `prepare-sd.sh` as a build of the latest panel v5 release. It
constructs an earlier base, while later kernel, power, Wi-Fi and panel steps
reuse artifacts from previous builds.

## Components observed in the local build

| Component | Version or identifier |
| --- | --- |
| Linux | 6.12, plus local board/display/Wi-Fi changes |
| U-Boot source | `5508406582f6f7120dce0c4b3059819a41788db2` |
| Buildroot | 2025.02.19 |
| External toolchain | Bootlin ARMv7 hard-float/musl, 2024.05-1 |
| LVGL | 9.4.0 |
| cJSON | Vendored source; bundled license retained |
| Host collector | Python standard library, systemd and udev |

These identify the development inputs, not a claim about current upstream
releases. Source archive hashes and all local modifications must accompany a
reproducible release.

## Existing source map

| Location | Role |
| --- | --- |
| `tools/board/` | Device tree variants; SD includes display and peripheral variants |
| `tools/buildroot/` | External tree, defconfig, root overlay and image layout |
| `tools/build/prepare-sd.sh` | Earlier SD base-build orchestration |
| `tools/build/build-a23-sd-uboot.sh` | SD bootloader adaptations and boot script generation |
| `tools/build/patch-g739-panel.py` | Display driver generation/patch tooling |
| `tools/build/build-a23-power-kernel.sh` | Watchdog/reset support on a previous kernel baseline |
| `tools/build/patch-eurocase-wifi.py` | Board Wi-Fi calibration fallback patch |
| `tools/build/build-a23-wifi-kernel.sh` | Later kernel configuration changes |
| `tools/build/prepare-wifi-image.sh` | Adds Wi-Fi tools and kernel to an earlier image |
| `tools/build/tablet-poc.c` | Minimal local test application |
| `tools/panel/` | Dashboard, parser, transport, collector and host integration |

Review the full include chain and each script's input paths before exporting
files. Several diagnostic variants intentionally target earlier experiments.

## Inputs that must be recovered into the firmware source repository

- The complete display driver currently supplied as
  `.tools/overlays/panel-simple-g739.c`, preferably as a reviewable patch.
- Exact initial kernel and U-Boot configuration baselines referenced from
  `analysis/usb-root/image/` and `analysis/bringup/`.
- All kernel changes needed for the final Wi-Fi/power build, not only defconfig
  fragments or generated binaries.
- The source/configuration of the validated recovery application; the current
  release chain checks a particular earlier executable hash.
- Touch firmware extraction inputs, extraction instructions and hashes, with
  distribution status recorded. Apply the same review to Realtek firmware and
  stock calibration data.
- Container setup and toolchain setup currently assumed by
  `tablet-a23-build:rootfs`, `tablet-a23-build:sd` and the
  `tablet-a23-sd-buildroot` volume.

The final panel packager uses an existing `/baseline` image. Its assertion that
`tablet-poc` has a specific SHA-256 protects that local chain but also makes it
unsuitable as a standalone build entry point.

## Public build target

A finished firmware build should fetch pinned upstream sources, verify hashes,
apply tracked patches, generate configs, build the bootloader/kernel/rootfs,
assemble regular image files and verify the output. It should run in an empty
build directory without this workstation's Docker volumes or `analysis/` tree.

Build a minimal firmware image first. Package the dashboard as an optional
application from a pinned panel release. Record both repository revisions in
any combined image manifest.

A clean build must check image boundaries, SPL checksums, kernel/DT/script
headers, required kernel options, rootfs contents and application self-checks.
Then test the resulting image on hardware: offline checks cannot establish
boot, touchscreen operation, power behavior or USB recovery.

No build or hardware operation was run for this documentation change.

## Inputs exported with this source publication

`config-baselines/` now preserves the earlier USB-root kernel config, initial
SPL config and final installed kernel/U-Boot configs. `patches/` preserves the
exact generated panel driver and Wi-Fi calibration changes as diffs against
Linux 6.12. They do not contain calibration bytes. The original generation
scripts are retained as research tools. Their historical `analysis/` and
`.tools/` input paths have not been converted into a clean build entry point.
Apply patches to the pinned original source, not an already patched tree.
