# Boot, installation and recovery

## Availability

There is no public downloadable release yet. The latest tested image exists
locally at `analysis/panel/v5/image/sdcard.img`. Its hash is recorded in the
[root README](../README.md). The current build scripts are development tooling,
not yet a complete fresh-clone installation path.

This image runs Linux from microSD. It does not install Linux into internal NAND.
Writing an image erases the destination card's existing partition layout/data.
Always identify the card again; never reuse a disk number from a development log.

## Boot architecture

```text
Allwinner BootROM
  -> microSD SPL (DRAM initialization)
  -> U-Boot
  -> FAT boot.scr + zImage + board.dtb
  -> SquashFS root on microSD partition 2
  -> BusyBox init
  -> USB setup + supervised application
```

The image uses an MBR partition table. The bootloader begins at 8 KiB, the
64 MiB FAT partition begins at 1 MiB, and the root partition reserves 32 MiB.
The boot script reads from SD and does not save the U-Boot environment or
attempt a NAND fallback.

The root is read-only. `/run`, `/tmp` and `/dev/shm` are RAM-backed, and `/var`
points to `/run`. Logs and manually provisioned Wi-Fi credentials do not survive
power loss. The integrated panel image starts `/usr/bin/tablet-panel` under an
init-supervised wrapper and retains `/usr/bin/tablet-poc` as a recovery tool.

## Installation procedure for a reviewed release

1. Match the tablet hardware to the supported revision and read the release's
   known limitations. Keep a copy of the existing card contents if needed.
2. Verify the downloaded image against that release's SHA-256 checksum.
3. Identify the removable microSD by model, capacity and connection. Unmount its
   filesystems before writing. Do not select the computer's internal drive.
4. Write the complete image to the card device, not to an existing partition.
5. Read back and compare every byte covered by the image. Eject the card cleanly.
6. With the tablet off, insert the card and boot. The tested integrated build
   can boot with USB already connected to the host.
7. Check display, touch, Home and both USB functions. For the panel image, check
   that a working collector supplies real metrics and that UI restart recovers
   the panel and data without manually loading programs into RAM.

No disk-write command is prescribed here until there is a reviewed public
release and a portable installation guide. The existing local writer is
`tools/build/write-sd.py`; review its arguments and device checks before use.

## USB channels

| Tablet endpoint | Purpose |
| --- | --- |
| `/dev/ttyGS0` | Development root console and kernel messages |
| `/dev/ttyGS1` | Host-to-tablet metrics; no shell |

The development gadget identifies itself with serial `eutb710mdq-sd-poc`,
VID `1d6b`, PID `0104`. Linux host by-id links use `if00` for the console and
`if02` for data. The transport discovers the interface; do not assume that the
data channel will always be `/dev/ttyACM1`. macOS names also vary.

The console opens a root shell without authentication. This is an explicit
development-image property and must be disclosed in every binary release.
USB enumeration occurs after Linux configures the gadget. No USB device can
therefore mean an early boot problem, rather than only a cable/host problem.

## Troubleshooting and recovery

- **Black screen and no USB:** verify the card/image/readback and power supply.
  USB cannot report an SPL or U-Boot failure in this configuration.
- **Panel visible, no metrics:** inspect `tablet-panel.service` on the host,
  check data-interface discovery, and confirm the collector's API configuration.
  Only one sender should own the data port.
- **Stale metrics:** the receiver keeps the last sample and reports its age;
  an API failure must not be interpreted as stopped guests or zero usage.
- **Wi-Fi disconnected after reboot:** expected; persistent configuration is
  not implemented.
- **Application exits:** init supervises the wrapper and restarts it with a delay.

Use the UI's orderly power controls when available. Removing the SD while the
tablet is off is the intended route back to stock Android, but the final public
release still needs an explicitly documented stock-return test. Do not promise
a complete NAND restore from the partial acquisitions.

FEL was entered during research through Android's `adb reboot efex`; that
command writes a boot reason to misc. A physical Home/Power FEL entry sequence
has not been confirmed. FEL/research scripts are not a required installation
step for a normal microSD release.
