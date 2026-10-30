#!/bin/sh
# Builds regular files only. Never formats, mounts or writes a block device.
set -eu
project=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
cd "$project"
task_image_dir=${1:-analysis/sd/image}
mkdir -p "$task_image_dir"
task_image_dir=$(CDPATH= cd -- "$task_image_dir" && pwd)
task_export_dir="$task_image_dir/../buildroot"
linux=.tools/sources/linux-6.12
uboot=.tools/sources/u-boot-5508406582f6f7120dce0c4b3059819a41788db2
buildroot=.tools/sources/buildroot-2025.02.19
for source in "$linux/Makefile" "$uboot/Makefile" "$buildroot/Makefile" \
    .tools/overlays/panel-simple-g739.c; do
    test -f "$source" || { echo "Missing source: $source" >&2; exit 1; }
done
mkdir -p "$task_export_dir" .tools/build/a23-sd \
    .tools/build/a23-sd-uboot .tools/buildroot-dl
python3 tools/build/check-sd-preparation.py --sources-only
python3 - <<'PATCH'
from pathlib import Path
source = Path('.tools/sources/u-boot-5508406582f6f7120dce0c4b3059819a41788db2/arch/arm/mach-sunxi/board.c').read_text()
needle = '#if CONFIG_CONS_INDEX == 1 && defined(CONFIG_UART0_PORT_F)'
assert source.count(needle) == 1
source = source.replace(needle, '#if !CONFIG_IS_ENABLED(SERIAL)\n\t/* No UART pinmux when the SPL has no serial console. */\n#elif CONFIG_CONS_INDEX == 1 && defined(CONFIG_UART0_PORT_F)')
Path('.tools/overlays/sd-sunxi-board.c').write_text(source)
PATCH
docker build -t tablet-a23-build:sd -f tools/build/Dockerfile.sd tools/build \
    > analysis/sd/docker-build.log 2>&1
docker run --rm \
    -v "$project/$linux:/src:ro" \
    -v "$project/.tools/overlays/panel-simple-g739.c:/src/drivers/gpu/drm/panel/panel-simple.c:ro" \
    -v "$project/.tools/build/a23-sd:/out" \
    -v "$project/analysis/usb-root/image:/baseline:ro" \
    -v "$project/tools/build:/work:ro" -v "$project/tools/board:/board:ro" \
    -v "$project/analysis/peripherals/firmware:/firmware:ro" \
    tablet-a23-build:sd sh /work/build-a23-sd-kernel.sh \
    > analysis/sd/kernel-build.log 2>&1
cp .tools/build/a23-sd/arch/arm/boot/zImage "$task_image_dir/zImage"
cp .tools/build/a23-sd/board.dtb "$task_image_dir/board.dtb"
cp .tools/build/a23-sd/.config "$task_image_dir/kernel.config"
docker run --rm \
    -v "$project/$uboot:/src:ro" -v "$project/.tools/build/a23-sd-uboot:/out" \
    -v "$project/.tools/overlays/sd-sunxi-board.c:/src/arch/arm/mach-sunxi/board.c:ro" \
    -v "$project/analysis/bringup:/baseline:ro" \
    -v "$task_image_dir:/kernel:ro" -v "$project/tools/build:/work:ro" \
    tablet-a23-build:sd sh /work/build-a23-sd-uboot.sh \
    > analysis/sd/uboot-build.log 2>&1
cp .tools/build/a23-sd-uboot/u-boot-sunxi-with-spl.bin "$task_image_dir/"
cp .tools/build/a23-sd-uboot/boot.scr "$task_image_dir/"
cp .tools/build/a23-sd-uboot/.config "$task_image_dir/u-boot.config"
docker run --rm -e FORCE_UNSAFE_CONFIGURE=1 \
    -v "$project/$buildroot:/src:ro" -v "$project/tools:/work/tools:ro" \
    -v tablet-a23-sd-buildroot:/out \
    -v "$task_export_dir:/export" \
    -v "$project/.tools/buildroot-dl:/downloads" \
    -v "$task_image_dir:/artifacts:ro" \
    -v "$project/analysis/peripherals/firmware:/firmware:ro" \
    tablet-a23-build:sd sh -ec '
        make -C /src O=/out BR2_EXTERNAL=/work/tools/buildroot tablet_sd_defconfig
        make -C /src O=/out BR2_DL_DIR=/downloads tablet-poc-rebuild
        make -C /src O=/out BR2_DL_DIR=/downloads -j6
        qemu-arm -L /out/target /out/target/usr/bin/tablet-poc --self-check
        mkdir -p /export/images
        cp -a /out/images/. /export/images/
        cp /out/.config /export/buildroot.config
        cp /out/build/busybox-*/.config /export/busybox.config
    ' > analysis/sd/buildroot-build.log 2>&1
cp "$task_export_dir/images/rootfs.squashfs" "$task_image_dir/"
cp "$task_export_dir/images/sdcard.img" "$task_image_dir/"
python3 tools/build/check-sd-preparation.py --image --image-dir "$task_image_dir"
