#!/usr/bin/env python3
"""Write one explicitly identified external USB SD and verify every image byte."""
import argparse
import errno
import hashlib
import json
import os
from pathlib import Path
import plistlib
import re
import subprocess


def require(ok, message):
    if not ok:
        raise SystemExit(message)


def file_hash(path):
    h = hashlib.sha256()
    with path.open('rb') as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--device', required=True)
    parser.add_argument('--expected-device-size', required=True, type=int)
    parser.add_argument('--image', required=True, type=Path)
    parser.add_argument('--expected-sha256', required=True)
    args = parser.parse_args()
    require(os.geteuid() == 0, 'Administrative privileges are required.')
    require(re.fullmatch(r'/dev/disk[0-9]+', args.device), 'Use an explicit whole disk device.')
    image = args.image.resolve()
    require(image.is_file(), 'Image must be a regular file.')
    length = image.stat().st_size
    require(length > 1024 * 1024 and length % 512 == 0, 'Invalid image size/alignment.')
    require(file_hash(image) == args.expected_sha256, 'Image hash mismatch; nothing written.')
    info = plistlib.loads(subprocess.check_output(['diskutil', 'info', '-plist', args.device]))
    require(info.get('DeviceNode') == args.device, 'Device identity mismatch.')
    require(info.get('WholeDisk') is True and info.get('Internal') is False,
            'Refusing a partition or an internal disk.')
    require(info.get('BusProtocol') == 'USB' and info.get('RemovableMedia') is True,
            'Refusing non-removable or non-USB media.')
    require(info.get('WritableMedia') is True, 'Media is not writable.')
    require(info.get('TotalSize') == args.expected_device_size and length <= info['TotalSize'],
            'Device size changed or image does not fit; nothing written.')
    require(info.get('DeviceBlockSize') == 512, 'Unexpected sector size.')
    subprocess.run(['diskutil', 'unmountDisk', args.device], check=True)
    raw = args.device.replace('/dev/disk', '/dev/rdisk', 1)
    fd = os.open(raw, os.O_RDWR)
    try:
        with image.open('rb') as source:
            for chunk in iter(lambda: source.read(1024 * 1024), b''):
                pending = memoryview(chunk)
                while pending:
                    count = os.write(fd, pending)
                    require(count > 0, 'Short device write.')
                    pending = pending[count:]
        try:
            os.fsync(fd)
        except OSError as error:
            if error.errno not in (errno.EINVAL, errno.ENOTSUP):
                raise
        subprocess.run(['/bin/sync'], check=True)
        os.lseek(fd, 0, os.SEEK_SET)
        h, remaining = hashlib.sha256(), length
        while remaining:
            chunk = os.read(fd, min(1024 * 1024, remaining))
            require(chunk, 'Unexpected EOF while verifying SD.')
            h.update(chunk)
            remaining -= len(chunk)
        require(h.hexdigest() == args.expected_sha256, 'SD readback mismatch; do not boot this card.')
    finally:
        os.close(fd)
    subprocess.run(['diskutil', 'eject', args.device], check=True)
    print(json.dumps({'device': args.device, 'device_size': info['TotalSize'],
                      'image_bytes': length, 'sha256': h.hexdigest(),
                      'sd_written': True, 'readback_verified': True, 'ejected': True}, indent=2))


if __name__ == '__main__':
    main()
