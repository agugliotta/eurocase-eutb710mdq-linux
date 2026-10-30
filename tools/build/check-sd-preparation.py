#!/usr/bin/env python3
"""Check preparation sources, or built image files. Never open a device."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import zlib

ROOT = Path(__file__).resolve().parents[2]
IMAGE = ROOT / 'dist'


def require(condition, message):
    if not condition:
        raise SystemExit(message)


def check_sources():
    for path in [ROOT / 'build.sh', ROOT / 'tools/build/build.sh',
                 ROOT / 'tools/build/build-a23-sd-uboot.sh',
                 *ROOT.glob('tools/buildroot/board/*.sh'),
                 *ROOT.glob('tools/buildroot/board/rootfs-overlay/usr/bin/run-*'),
                 ROOT / 'tools/buildroot/board/rootfs-overlay/etc/init.d/setup-usb']:
        subprocess.run(['sh', '-n', str(path)], check=True)
    sd = (ROOT / 'tools/board/sun8i-a23-eurocase-eutb710mdq-sd.dts').read_text()
    boot = (ROOT / 'tools/build/sd-boot.cmd').read_text()
    require('root=/dev/mmcblk0p2 rootfstype=squashfs rootwait ro' in sd,
            'DT root filesystem does not match image partition 2')
    require('root=/dev/mmcblk0p2 rootfstype=squashfs rootwait ro' in boot,
            'Boot script root filesystem mismatch')
    require('&uart0 { status = "disabled"; };' in sd, 'UART/SD pin conflict')
    require('&nfc { status = "disabled"; };' in sd, 'NAND must stay disabled')
    require('broken-cd;' in sd and 'cd-gpios =' not in sd,
            'SD must not depend on the unreliable PB4 presence signal')
    usb = (ROOT / 'tools/buildroot/board/rootfs-overlay/etc/init.d/setup-usb').read_text()
    require('functions/acm.usb0' in usb and 'functions/acm.usb1' in usb,
            'Both debug and data ACM functions are required')
    init = (ROOT / 'tools/buildroot/board/rootfs-overlay/etc/inittab').read_text()
    require('run-debug-console' in init and 'run-panel' in init, 'Missing supervision')
    require('remount,rw' not in init and 'swapon' not in init, 'Unexpected disk writes')
    print('Tracked source checks OK; no historical baseline images required')


def fdt_properties(data):
    magic, total, off_struct, off_strings = struct.unpack_from('>4I', data)
    require(magic == 0xd00dfeed and total <= len(data), 'Invalid DTB')
    pos, stack, result = off_struct, [], {}
    while True:
        token = struct.unpack_from('>I', data, pos)[0]
        pos += 4
        if token == 1:
            end = data.index(0, pos)
            stack.append(data[pos:end].decode())
            pos = (end + 4) & ~3
        elif token == 2:
            stack.pop()
        elif token == 3:
            size, nameoff = struct.unpack_from('>2I', data, pos)
            pos += 8
            namepos = off_strings + nameoff
            end = data.index(0, namepos)
            name = data[namepos:end].decode()
            result[('/' + '/'.join(stack[1:]), name)] = data[pos:pos + size]
            pos = (pos + size + 3) & ~3
        elif token == 4:
            continue
        elif token == 9:
            return result
        else:
            raise SystemExit(f'Invalid FDT token: {token}')


def check_image():
    names = ['sdcard.img', 'zImage', 'board.dtb', 'boot.scr',
             'u-boot-sunxi-with-spl.bin', 'kernel.config', 'u-boot.config',
             'rootfs.squashfs']
    for name in names:
        require((IMAGE / name).is_file(), f'Missing build artifact: {name}')
    disk = (IMAGE / 'sdcard.img').read_bytes()
    spl = (IMAGE / 'u-boot-sunxi-with-spl.bin').read_bytes()
    require(len(spl) < 1024 * 1024 - 8192, 'Bootloader overlaps first partition')
    require(disk[8192:8192 + len(spl)] == spl, 'Bootloader offset/content mismatch')
    require(spl[4:12] == b'eGON.BT0', 'Missing Allwinner SPL header')
    spl_length = struct.unpack_from('<I', spl, 16)[0]
    require(32 <= spl_length <= 32768 and spl_length % 512 == 0, 'Invalid SPL size')
    spl_header = bytearray(spl[:spl_length])
    expected = struct.unpack_from('<I', spl_header, 12)[0]
    struct.pack_into('<I', spl_header, 12, 0x5f0a6c39)
    require(sum(struct.unpack('<' + 'I' * (spl_length // 4), spl_header)) & 0xffffffff == expected,
            'Invalid Allwinner SPL checksum')
    require(struct.unpack_from('>I', spl, 32768)[0] == 0x27051956,
            'U-Boot image missing at SPL raw-load offset')
    ub_config = (IMAGE / 'u-boot.config').read_text().splitlines()
    for setting in ['CONFIG_SYS_MMCSD_RAW_MODE_U_BOOT_SECTOR=0x40',
                    'CONFIG_SYS_MMCSD_RAW_MODE_U_BOOT_DATA_PART_OFFSET=0x10',
                    'CONFIG_DRAM_CLK=552', 'CONFIG_DRAM_ZQ=63351',
                    'CONFIG_DRAM_ODT_EN=y', 'CONFIG_AXP_DCDC1_VOLT=3000',
                    'CONFIG_AXP_DCDC2_VOLT=1100', 'CONFIG_AXP_DCDC3_VOLT=1260',
                    'CONFIG_AXP_DCDC5_VOLT=1500']:
        require(setting in ub_config, f'Unexpected boot setting: {setting}')
    require(disk[510:512] == b'\x55\xaa', 'Invalid MBR signature')
    partitions = []
    for index, kind in [(0, 0x0c), (1, 0x83)]:
        entry = disk[446 + index * 16:462 + index * 16]
        start, size = struct.unpack_from('<2I', entry, 8)
        require(entry[4] == kind, 'Unexpected partition type')
        require(start > 0 and (start + size) * 512 <= len(disk), 'Invalid partition bounds')
        partitions.append((start * 512, size * 512))
    require(partitions[0][0] == 1024 * 1024, 'Boot partition must start at 1 MiB')
    require(partitions[0][0] + partitions[0][1] <= partitions[1][0], 'Overlapping partitions')
    root = (IMAGE / 'rootfs.squashfs').read_bytes()
    require(root[:4] == b'hsqs', 'Invalid SquashFS header')
    start, size = partitions[1]
    require(len(root) <= size and disk[start:start + len(root)] == root,
            'Root filesystem partition mismatch')
    kernel = (IMAGE / 'zImage').read_bytes()
    require(struct.unpack_from('<I', kernel, 36)[0] == 0x016f2818, 'Invalid ARM zImage')
    props = fdt_properties((IMAGE / 'board.dtb').read_bytes())
    for path, status in [('/soc/mmc@1c0f000', b'okay\0'),
                         ('/soc/serial@1c28000', b'disabled\0'),
                         ('/soc/nand-controller@1c03000', b'disabled\0')]:
        require(props.get((path, 'status')) == status, f'Unexpected DT state: {path}')
    require(('/soc/mmc@1c0f000', 'broken-cd') in props and
            ('/soc/mmc@1c0f000', 'cd-gpios') not in props,
            'Built DT must use polling instead of PB4')
    script = (IMAGE / 'boot.scr').read_bytes()
    header = bytearray(script[:64])
    magic, hcrc, _, size, _, _, dcrc = struct.unpack_from('>7I', header)
    header[4:8] = b'\0' * 4
    require(magic == 0x27051956 and zlib.crc32(header) == hcrc, 'Invalid boot script header')
    require(zlib.crc32(script[64:64 + size]) == dcrc, 'Invalid boot script payload')
    for config, required, forbidden in [
        ('kernel.config', ['MMC', 'MMC_BLOCK', 'MMC_SUNXI', 'SQUASHFS',
                           'USB_CONFIGFS_ACM', 'U_SERIAL_CONSOLE', 'UNIX'], ['MTD', 'MODULES']),
        ('u-boot.config', ['MMC', 'SPL_MMC', 'ENV_IS_NOWHERE', 'SYS_MMCSD_RAW_MODE_U_BOOT_USE_SECTOR'],
         ['UART0_PORT_F', 'NAND', 'MMC_WRITE', 'SPL_MMC_WRITE', 'CMD_SAVEENV',
          'AXP_GPIO', 'REGULATOR_AXP'])]:
        lines = (IMAGE / config).read_text().splitlines()
        for symbol in required:
            require(f'CONFIG_{symbol}=y' in lines, f'{config}: missing {symbol}')
        for symbol in forbidden:
            require(f'CONFIG_{symbol}=y' not in lines, f'{config}: forbidden {symbol}')
    manifest = {'offline_checks_passed': True, 'hardware_boot_tested': False,
                'sd_written': False, 'public_distribution_cleared': False,
                'application': 'tablet-poc (minimal local UI; no Proxmox panel)',
                'files': {name: hashlib.sha256((IMAGE / name).read_bytes()).hexdigest()
                          for name in names}}
    (IMAGE / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print('Image structure and hashes OK; hardware boot remains UNTESTED')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--sources-only', action='store_true')
    group.add_argument('--image', action='store_true')
    parser.add_argument('--image-dir', type=Path, default=IMAGE)
    args = parser.parse_args()
    IMAGE = args.image_dir.resolve()
    check_sources()
    if args.image:
        check_image()
