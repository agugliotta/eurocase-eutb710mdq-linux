# Build a local microSD image

The supported entry point is a self-contained Docker build. The host needs
Docker running, internet access and a POSIX shell (Linux, macOS or WSL). `make` is a convenience:
`sh build.sh` runs the same build. Python and the cross compiler run inside the
container; no Python environment needs to be installed on the host to build.

## First build

1. Check the exact supported hardware and warnings in the root README.
2. Put your own two stock board files in `firmware/`, following
   [the extraction instructions](../firmware/README.md).
3. From the repository root, run:

```sh
make image
```

The output is `dist/sdcard.img`, accompanied by `SHA256SUMS`,
`manifest.json`, effective kernel/U-Boot/Buildroot configs, and component images.
`dist/` and the two stock files are ignored by Git. This command never writes
an SD card, invokes ADB/FEL, touches USB or accesses the tablet. Card installation
is a separate step described in [INSTALLATION.md](INSTALLATION.md).

The image contains the minimal local touchscreen application, USB debug/data
functions, read-only rootfs and local power controls. It does **not** include
the separately archived LVGL Proxmox dashboard or a Proxmox collector. Wi-Fi
userspace tools are included; no SSID/password or automatic Wi-Fi setup is added.
The existing local application retains its historical Spanish UI strings.

## What the command handles

- Builds its own tool container directly from Debian bookworm.
- Fetches pinned Linux 6.12, U-Boot commit
  `5508406582f6f7120dce0c4b3059819a41788db2` and Buildroot 2025.02.19 archives.
- Verifies each archive and the licensed Realtek firmware by SHA-256 before use.
- Applies the tracked display/Wi-Fi patches and U-Boot SD pinmux adjustment.
- Converts your stock touch table and calibration into the expected inputs.
- Builds kernel/DTB, SPL/U-Boot, musl userspace and the local application.
- Assembles the SD image and runs structural checks and the ARM application
  self-check under qemu-arm.

There is no dependency on an `analysis/` directory, an old image, a prebuilt
`tablet-a23-build:*` container or the original workstation's Docker volumes.
The configuration seeds under `config-baselines/` are tracked text inputs.

## Cache and resource use

Sources, downloads and build output use Docker volume `eutb710mdq-build`.
Allow several GB of disk space and expect a long first compilation. Later builds
reuse downloads/object files. The container uses `linux/amd64` because the
Bootlin host toolchain is x86-64; Apple Silicon therefore requires Docker
emulation and may build more slowly. The default parallelism is four jobs:

```sh
JOBS=8 make image
```

To exercise a separate empty build cache without deleting existing work:

```sh
BUILD_VOLUME=eutb710mdq-clean-check make image
```

A cached archive with an incorrect checksum causes an explicit failure; it is
not silently accepted. A failed/incomplete download never becomes a cached source
archive. Re-run after resolving the reported error. Changing a file in the
read-only mounted source tree while a build runs is not supported.

Source versions and archives are pinned, but the Debian base/package security
updates are not locked by digest. This is a reproducible procedure, not a claim
of bit-identical binaries across all dates, host architectures and compiler
package revisions.

## Offline checks and limitations

`make test` runs the small build-tool regression suite using host Python 3. It
checks input validation, malformed calibration/touch tables, cached-download
integrity and failure before Docker when owner inputs are absent. The complete
image build additionally checks the actual generated image and application.

A successful build does not prove that its output boots on the physical tablet.
Every new output manifest starts with `hardware_boot_tested=false` and
`sd_written=false`. Earlier installed-image evidence must not be copied to a
new image. No hardware test or SD write is performed automatically.

## Private builds and public releases

The two owner-supplied files remain necessary because their distribution status
is separate from the open-source build machinery. The current build embeds the
firmware to preserve early driver probing. Do not publish its binary output as
if it were a cleared generic firmware release. A distribution build still needs
separate firmware loading/provisioning, corresponding-source/license packaging
and hardware validation. See the draft release and [open issues](OPEN-ISSUES.md).
