# Exported configuration baselines

Text configurations preserved from the local development build:

- `usb-root/kernel.config`: input expected by the earlier SD kernel stage.
- `bringup/u-boot-spl.config`: input expected by the SD U-Boot stage.
- `installed/`: kernel and U-Boot configs accompanying the tested panel v5 image.

These are not all build inputs and do not reconstruct the image alone. Scripts
still refer to their original `analysis/` paths. Paths and generated inputs need
to be unified for a clean build; see ../docs/BUILD.md. No binaries or calibration
maps are included.
