# Reproduce the system without repeating the investigation

For a new owner, the intended path is now:

1. Verify that the hardware matches the supported Eurocase EUTB_710MDQ board.
2. Read the two stock board files from your own unit (or use your backups).
3. Run `make image` with Docker running.
4. Verify and write `dist/sdcard.img` to a spare microSD, then test that new image.

The exact prerequisites, commands, cache behavior and output limits are in
[BUILD.md](BUILD.md). The owner-file acquisition commands are in
[firmware/README.md](../firmware/README.md). Installation is separate from
compilation: see [INSTALLATION.md](INSTALLATION.md).

The default build produces the minimal tablet Linux system; the Proxmox panel
is preserved in its own repository and is not pulled into this build.

## Why the research scripts are no longer required

The [bring-up account](BRINGUP.md) explains how stock identification, FEL, DRAM,
display, touch, NAND diagnostics and SD boot led to the current configuration.
Those experiments are valuable context, but repeating them is not necessary
for this build. Historical Python diagnostics were removed from the active
source tree once their required outputs became tracked configuration or patches.
They remain in the initial Git commit, rather than being prerequisites of the
new build entry point.

The remaining Python implementation is limited to source/input preparation,
image validation and a small offline regression suite. All compilation-related
Python runs inside Docker.

## Report a reproduction precisely

Record the board/component identification without personal serials, repository
revision, resulting image SHA-256, effective configurations, sanitized build/boot
logs and exactly which physical behaviors passed or failed. Compare those
results with [OPEN-ISSUES.md](OPEN-ISSUES.md). A compilation success is not a
camera, speaker, suspend, charging or long-term stability test.
