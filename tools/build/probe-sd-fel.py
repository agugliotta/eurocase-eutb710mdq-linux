#!/usr/bin/env python3
"""Swap only the SD's first 8 KiB of SPL for the upstream FEL probe, or restore it."""
import argparse
import hashlib
import json
from pathlib import Path
import shlex
import subprocess
import uuid

ROOT = Path(__file__).resolve().parents[2]
FOLDER = ROOT / 'analysis/sd/fel-probe'
SIZE = '30535680'
DEVICE = '/dev/block/mmcblk0'
BB = '/system/bin/busybox'


def require(ok, message):
    if not ok:
        raise SystemExit(message)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--serial', required=True)
    parser.add_argument('mode', choices=['probe', 'restore'])
    args = parser.parse_args()
    adb = ['adb', '-s', args.serial]

    def shell(command):
        p = subprocess.run(adb + ['shell', command], capture_output=True, timeout=30)
        require(p.returncode == 0, p.stderr.decode(errors='replace'))
        return p.stdout.decode().replace('\r\n', '\n').strip()

    meta = json.loads((FOLDER / 'manifest.json').read_text())
    probe, restore = FOLDER / 'fel-sdboot.sunxi', FOLDER / 'restore-first8k.bin'
    for path in [probe, restore]:
        require(path.stat().st_size == 8192, 'Unexpected fragment length')
        require(hashlib.sha256(path.read_bytes()).hexdigest() == meta['files'][path.name],
                'Fragment hash mismatch')
    fragment, previous = (probe, restore) if args.mode == 'probe' else (restore, probe)
    wanted, old_hash = meta['files'][fragment.name], meta['files'][previous.name]
    require('uid=0(root)' in shell('id'), 'Android shell is not root')
    require(shell(f'{BB} cat /sys/block/mmcblk0/device/type') == 'SD', 'Not an SD card')
    require(shell(f'{BB} cat /sys/block/mmcblk0/size') == SIZE, 'Wrong card capacity')
    require('/sunxi-mmc.0/' in shell(f'{BB} readlink -f /sys/block/mmcblk0'),
            'Wrong MMC controller')
    require(any(line.startswith('tmpfs /dev tmpfs ') for line in shell('cat /proc/mounts').splitlines()),
            '/dev must be RAM-backed')
    read_hash = f'{BB} dd if={DEVICE} bs=512 skip=16 count=16 2>/dev/null | {BB} sha256sum'
    current = shell(read_hash).split()[0]
    require(current == old_hash, 'Current SD prefix is not the expected previous version; aborting')
    remote = '/dev/panel-sd-fragment-' + uuid.uuid4().hex + '.bin'
    subprocess.run(adb + ['push', str(fragment), remote], check=True, capture_output=True, timeout=30)
    q = shlex.quote(remote)
    command = f'''set -e
    test -b {DEVICE}
    test "$({BB} cat /sys/block/mmcblk0/size)" = {SIZE}
    test "$({BB} cat /sys/block/mmcblk0/device/type)" = SD
    test "$({BB} wc -c < {q})" -eq 8192
    uploaded="$({BB} sha256sum {q})"
    test "${{uploaded%% *}}" = {wanted}
    previous="$({read_hash})"
    test "${{previous%% *}}" = {old_hash}
    {BB} dd if={q} of={DEVICE} bs=1024 seek=8 count=8 conv=notrunc
    {BB} sync
    actual="$({read_hash})"
    test "${{actual%% *}}" = {wanted}
    {BB} rm {q}
    echo SD_FRAGMENT_VERIFIED_{wanted}
'''
    # Legacy ADB does not reliably propagate a remote exit status: require the marker.
    response = shell(command)
    require(f'SD_FRAGMENT_VERIFIED_{wanted}' in response,
            'No verified write marker; inspect SD before booting or retrying')
    result = {'mode': args.mode, 'device': DEVICE, 'offset_bytes': 8192,
              'written_bytes': 8192, 'readback_verified': True,
              'previous_sha256': old_hash, 'new_sha256': wanted,
              'android_firmware_written': False}
    (FOLDER / ('write-' + args.mode + '.json')).write_text(json.dumps(result, indent=2) + '\n')
    meta['written_to_sd'] = args.mode == 'probe'
    (FOLDER / 'manifest.json').write_text(json.dumps(meta, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
