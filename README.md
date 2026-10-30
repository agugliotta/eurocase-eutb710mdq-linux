# Linux on the Eurocase EUTB_710MDQ

Repurposing an Allwinner A23 Android tablet as a small Linux device, booting
from microSD. The working demonstration is a touchscreen Proxmox dashboard
receiving live metrics over USB.

The goal is to make the board support useful to other owners of this tablet,
independently of the dashboard application.

**Status as of October 29, 2026:** a microSD image has been installed and tested
on one tablet. Display, touch, Home, USB console/data, dashboard startup and
restart through the dashboard work on that unit. Internal NAND has not been
flashed. A self-contained Docker build is now provided; new outputs require their own
hardware validation. See [build verification](docs/BUILD-VERIFICATION.md).

> [!WARNING]
> **Experimental board-specific port for the Eurocase EUTB_710MDQ
> (EUTB-710 MDQ), Allwinner A23 / polaris-g739, 1024 × 600 LCD,
> Silead GSL1680 touch and RTL8188EU Wi-Fi.** Tested on one physical unit only.
> This is not a generic A23 tablet firmware, Android update, or NAND installer.
> Other models or board revisions may use incompatible DRAM, PMIC, panel or
> touch configurations. Incorrect board settings can prevent boot or affect
> hardware operation. Writing an SD image erases the selected card.
> The development image exposes an unauthenticated root shell over USB.
> No ready-to-flash binary release is provided; the build requires two owner-supplied stock files. Headphones worked, the built-in speaker is unresolved,
> and cameras were never tested.

## Build it

With Docker running, place the two stock board files from your own tablet in
`firmware/` as described in [the extraction guide](firmware/README.md), then run:

```sh
make image
```

`sh build.sh` is equivalent. The build downloads verified source archives,
compiles the system in its own container and writes `dist/sdcard.img`.
No old images, research directories or pre-existing build volumes are needed.
It never writes a card or accesses the tablet. See [the build guide](docs/BUILD.md).

This builds the minimal tablet system; the Proxmox panel remains a separate
archive. The resulting owner-local image is not a cleared binary release.

## Start here

- [How the port was developed, including failed approaches](docs/BRINGUP.md)
- [Reproduction stages and current prerequisites](docs/REPRODUCING.md)
- [Unresolved issues and untested hardware](docs/OPEN-ISSUES.md)
- [Hardware, supported features and limitations](docs/HARDWARE.md)
- [Boot, installation and recovery](docs/INSTALLATION.md)
- [One-command build and validation limits](docs/BUILD.md)
- [Repository split and publication plan](docs/PUBLISHING.md)

## Two related projects

The two related repositories are:

| Repository | Purpose |
| --- | --- |
| `eurocase-eutb710mdq-linux` | Board support, bootloader/kernel changes, root filesystem and microSD image tooling |
| `tablet-proxmox-panel` | LVGL application, USB protocol, Proxmox collector and host service |

This source repository contains the firmware tooling and distilled research.
The personal acquisition/build workspace is intentionally excluded.
Repositories: [tablet Linux](https://github.com/agugliotta/eurocase-eutb710mdq-linux)
and [panel archive](https://github.com/agugliotta/tablet-proxmox-panel).

The firmware project should boot a useful minimal system without requiring
Proxmox. The panel project is a preservation archive with an English description and
screenshots, rather than a separate product-development effort. Its
[archive README](https://github.com/agugliotta/tablet-proxmox-panel) explains what it does.

## What works

- Autonomous microSD boot using SPL, U-Boot, Linux and a read-only SquashFS root.
- 1024 × 600 display, touch input and physical Home button.
- Two USB ACM functions: a development console and a separate metrics channel.
- Supervised application startup and local shutdown/restart controls.
- Real Proxmox CPU, RAM, selected-storage usage and VM/container inventory.
- Automatic collector reconnection after tablet shutdown or restart.
- Wi-Fi association, DHCP and connectivity in a separate development test;
  credentials were held in RAM and automatic connection is not implemented.

The dashboard currently uses Spanish UI labels. The public documentation added
here is in English; older research findings are being distilled into English guides. Archived UI
strings and historical screenshots retain their original language.

## Scope and preservation

This is a port for a particular tablet board, not a universal Allwinner A23
image. Hardware revisions may differ. The development image exposes a local
root console over USB without a login; connect it only to a trusted host.

Raw stock firmware, device acquisitions, private host inventory, credentials,
large build outputs and chronological session notes do not belong in the
public source repository. Keep the originals locally. Publish reviewed release
assets separately, with checksums and the required source/license material.

## Release status

The latest local integrated image is panel v5, with Linux
`6.12.0-eutb710mdq-sd4wifi`. It was verified by complete image readback, booted
with USB connected to the Proxmox host, and restarted through the UI with
metrics returning automatically. This is evidence for the tested unit only.

| Artifact | SHA-256 |
| --- | --- |
| Integrated microSD image | `cd2d311fe82fd8cc38975b2bd3e41962f27f0af6b455535bafd9aa5650890e3f` |
| Installed panel executable | `2bd4b08afbee13661e0dd2c0cab76b452ca4311d70c98d36dc0ff05e7d2afa0f` |

These hashes identify local artifacts, not a downloadable public release.
