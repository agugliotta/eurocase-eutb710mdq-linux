#!/usr/bin/env python3
"""Capture a new Linux CDC ACM console and query read-only boot evidence."""
import glob
import json
import os
from pathlib import Path
import select
import sys
import termios
import time

out = Path(sys.argv[1])
before = set(sys.argv[2:])
out.mkdir(parents=True, exist_ok=True)
result = {'enumerated': False, 'linux_shell_observed': False}
deadline = time.monotonic() + 60
port = None
while time.monotonic() < deadline:
    ports = set(glob.glob('/dev/cu.usbmodem*')) - before
    if len(ports) > 1:
        raise RuntimeError(f'Ambiguous serial ports: {ports}')
    if ports:
        port = ports.pop()
        break
    time.sleep(0.2)
if port is None:
    (out / 'serial-result.json').write_text(json.dumps(result, indent=2) + '\n')
    sys.exit('No new CDC ACM port within 60 seconds')

fd = os.open(port, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
original = termios.tcgetattr(fd)
data = bytearray()
try:
    attrs = termios.tcgetattr(fd)
    attrs[0] = attrs[1] = attrs[3] = 0
    attrs[2] = termios.CS8 | termios.CREAD | termios.CLOCAL
    attrs[4] = attrs[5] = termios.B115200
    attrs[6][termios.VMIN] = attrs[6][termios.VTIME] = 0
    termios.tcsetattr(fd, termios.TCSANOW, attrs)
    result.update(enumerated=True, port=port)

    def collect(seconds):
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            ready, _, _ = select.select([fd], [], [], max(0, min(0.2, end-time.monotonic())))
            if ready:
                data.extend(os.read(fd, 65536))
                (out / 'console.txt').write_bytes(data)

    collect(3)
    os.write(fd, b'\r')
    collect(1)
    if b'EUROCASE_MAINLINE_USB_SHELL' not in data:
        raise RuntimeError('Port appeared without expected initramfs marker; commands withheld')
    result['linux_shell_observed'] = True
    for cmd in ['/bin/busybox uname -a', '/bin/busybox cat /proc/cmdline',
                '/bin/busybox cat /proc/meminfo', '/bin/busybox cat /proc/partitions',
                '/bin/busybox dmesg', 'echo EUROCASE_LINUX_DIAGNOSTICS_COMPLETE']:
        os.write(fd, cmd.encode() + b'\r')
        collect(2)
    result['diagnostics_complete'] = b'\r\nEUROCASE_LINUX_DIAGNOSTICS_COMPLETE\r\n' in data
    print(data.decode(errors='replace'))
finally:
    (out / 'serial-result.json').write_text(json.dumps(result, indent=2) + '\n')
    termios.tcsetattr(fd, termios.TCSANOW, original)
    os.close(fd)
