#!/usr/bin/env python3
"""Run an explicit command file on the already identified Linux USB shell."""
import os
import fcntl
from pathlib import Path
import select
import sys
import struct
import termios
import time

assert len(sys.argv) in (4, 5)
port, commands, output = sys.argv[1:4]
command_timeout = float(sys.argv[4]) if len(sys.argv) == 5 else 40
assert 1 <= command_timeout <= 300
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
    fcntl.ioctl(fd, termios.TIOCMBIS, struct.pack('I', termios.TIOCM_DTR | termios.TIOCM_RTS))
    settle = time.monotonic() + 3
    while time.monotonic() < settle:
        ready, _, _ = select.select([fd], [], [], 0.2)
        if ready:
            data.extend(os.read(fd, 65536))
            Path(output).write_bytes(data)
    for index, command in enumerate(Path(commands).read_text().splitlines()):
        if not command.strip() or command.startswith('#'):
            continue
        marker = f'EU_QUERY_DONE_{index}'
        line = f'{command}; echo {marker}\r'.encode()
        assert len(line) < 1000, 'Command exceeds conservative console line limit'
        os.write(fd, b'\r' + line)
        start = len(data)
        deadline = time.monotonic() + command_timeout
        while time.monotonic() < deadline:
            ready, _, _ = select.select([fd], [], [], 0.2)
            if ready:
                data.extend(os.read(fd, 65536))
                Path(output).write_bytes(data)
                if b'\r\n' + marker.encode() + b'\r\n' in data[start:]:
                    break
        else:
            raise TimeoutError(f'No completion marker for command {index}')
    print(f'Console response saved: {output} ({len(data)} bytes)')
finally:
    termios.tcsetattr(fd, termios.TCSANOW, original)
    os.close(fd)
