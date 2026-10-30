#!/usr/bin/env python3
"""Wait for a new CDC ACM port; collect read-only U-Boot diagnostics."""
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
deadline = time.monotonic() + 45
port = None
while time.monotonic() < deadline:
    ports = set(glob.glob('/dev/cu.usbmodem*')) - before
    if len(ports) > 1:
        raise RuntimeError(f'Ambiguous new serial ports: {ports}')
    if ports:
        port = ports.pop()
        break
    time.sleep(0.2)
if port is None:
    (out / 'serial-result.json').write_text(json.dumps({'enumerated': False}) + '\n')
    sys.exit('No new CDC ACM port within 45 seconds')

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

    def collect(seconds):
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            ready, _, _ = select.select([fd], [], [], min(0.2, end-time.monotonic()))
            if ready:
                chunk = os.read(fd, 65536)
                data.extend(chunk)
                (out / 'console.txt').write_bytes(data)

    collect(2)
    os.write(fd, b'\r')
    collect(1)
    if b'=> ' not in data:
        raise RuntimeError('USB enumerated, but no U-Boot prompt; diagnostics withheld')
    for command in ['version', 'bdinfo',
                    'printenv bootcmd bootdelay stdin stdout stderr fel_booted',
                    'echo EUROCASE_DIAGNOSTICS_COMPLETE']:
        os.write(fd, command.encode() + b'\r')
        collect(2)
    passed = b'\r\nEUROCASE_DIAGNOSTICS_COMPLETE\r\n' in data
    (out / 'serial-result.json').write_text(json.dumps({
        'enumerated': True, 'port': port, 'diagnostics_complete': passed,
        'commands': 'version, bdinfo, printenv, echo; no storage operations',
    }, indent=2) + '\n')
    print(data.decode(errors='replace'))
    if not passed:
        raise RuntimeError('Diagnostics completion marker absent')
finally:
    termios.tcsetattr(fd, termios.TCSANOW, original)
    os.close(fd)
