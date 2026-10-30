# Build verification — October 30, 2026

The supported Docker build completed using a new isolated cache, without any
previous kernel, U-Boot, rootfs or original workstation build volume. Pinned
upstream archives were downloaded and verified; owner-supplied stock files were
provided locally and remained excluded from Git.

The first run exposed unnecessary CMake compilation and unreliable upstream
source servers. The final container uses Debian CMake (which satisfies
Buildroot's requirement), and package downloads prefer Buildroot's official
mirror with bounded timeouts. The build was resumed with its own cached outputs;
none came from the earlier research/installed images.

Validation completed:

- Five offline build-tool regression tests passed.
- Linux kernel and board DT compiled with tracked patches/configuration.
- SPL/U-Boot compiled from the pinned source with the SD adaptations.
- Buildroot compiled the musl userspace, local application and Wi-Fi tools.
- The ARM application passed `--self-check` under qemu-arm.
- Generated image checks passed for MBR/partition bounds, SPL placement/checksum,
  U-Boot layout, boot script checksums, device tree state, critical config and
  embedded root filesystem contents.
- SHA-256 checksums were generated and independently checked against the output.

The result is `dist/sdcard.img` (101711872 bytes), a new minimal-system image.
This image is **not** the previously installed Proxmox panel image. It has not
been written to an SD card or booted on hardware. Its generated manifest records
`hardware_boot_tested=false`, `sd_written=false` and
`public_distribution_cleared=false`. Owner firmware/calibration and binary
outputs were not published.

This verifies an end-to-end source-build procedure, not bit-for-bit
reproducibility across changing Debian package versions or a fresh hardware
validation. See [BUILD.md](BUILD.md) for reproduction commands and limits.
