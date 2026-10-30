# Tracked configuration seeds

- `installed/kernel.config`: effective kernel config accompanying the tested
  panel v5 image. The build changes its local version and firmware directory.
- `bringup/u-boot-spl.config`: the initial SPL config, transformed by the tracked
  SD U-Boot script into its complete SD bootloader configuration.

These are text inputs. No previous kernel or image binary is needed. See
[BUILD.md](../docs/BUILD.md) for the complete Docker build procedure.
