#!/usr/bin/env python3
"""Upload a POC payload to the verified Linux RAM shell via base64 uudecode."""
import base64
import fcntl
import hashlib
import os
from pathlib import Path
import select
import struct
import sys
import termios
import time

def verify_identity(data, mode):
    if mode == '--rescue':
        assert b'6.12.0-eutb710mdq-sd1\r\n' in data
        assert b'\r\ntablet-ram-rescue\r\n' in data
        assert b'rootfs / rootfs rw,' in data, 'Rescue root must be RAM-backed'
    elif mode in ('--sd', '--panel', '--panel-v2', '--panel-v3', '--panel-v4', '--panel-v5'):
        kernel = b'sd3power' if mode == '--sd' else b'sd4wifi'
        assert b'6.12.0-eutb710mdq-' + kernel + b'\r\n' in data
        assert b'\r\ntablet\r\n' in data
        assert b'/dev/root / squashfs ro,' in data, 'SD root must be read-only'
        assert b'tmpfs /run tmpfs rw,' in data, '/run must be RAM-backed'
    else:
        assert mode == ''
        assert b'6.12.0-eutb710mdq-display1\r\n' in data

if sys.argv[1:] == ['--self-check']:
    good = b'6.12.0-eutb710mdq-sd3power\r\ntablet\r\n/dev/root / squashfs ro,relatime\r\ntmpfs /run tmpfs rw,relatime\r\n'
    verify_identity(good, '--sd')
    verify_identity(good.replace(b'sd3power', b'sd4wifi'), '--panel')
    verify_identity(good.replace(b'sd3power', b'sd4wifi'), '--panel-v2')
    verify_identity(good.replace(b'sd3power', b'sd4wifi'), '--panel-v3')
    verify_identity(good.replace(b'sd3power', b'sd4wifi'), '--panel-v4')
    verify_identity(good.replace(b'sd3power', b'sd4wifi'), '--panel-v5')
    try:
        verify_identity(good, '--panel')
    except AssertionError:
        pass
    else:
        raise AssertionError('Wrong panel kernel accepted')
    for before, after in [(b'sd3power', b'sd2'), (b'tablet\r\n', b'other\r\n'),
                          (b'squashfs ro,', b'squashfs rw,'), (b'tmpfs /run', b'ext4 /run')]:
        try:
            verify_identity(good.replace(before, after), '--sd')
        except AssertionError:
            pass
        else:
            raise AssertionError('Unsafe SD identity accepted')
    print('USB_UPLOAD_IDENTITY_OK; no USB accessed')
    raise SystemExit(0)

assert len(sys.argv) in (4, 5)
port, source, output = sys.argv[1:4]
mode = sys.argv[4] if len(sys.argv) == 5 else ''
assert mode in ('', '--rescue', '--sd', '--panel', '--panel-v2', '--panel-v3', '--panel-v4', '--panel-v5')
destination = ('/run/tablet-panel-v5' if mode == '--panel-v5' else
               '/run/tablet-panel-v4' if mode == '--panel-v4' else
               '/run/tablet-panel-v3' if mode == '--panel-v3' else
               '/run/tablet-panel-v2' if mode == '--panel-v2' else
               '/run/tablet-panel-v1' if mode == '--panel' else
               '/run/wifi-bundle.tar.gz' if mode == '--sd' else '/poc-bundle.tar.gz')
raw = Path(source).read_bytes()
assert 0 < len(raw) < 10 * 1024 * 1024
encoded = base64.encodebytes(raw)
assert base64.decodebytes(encoded) == raw
digest = hashlib.sha256(raw).hexdigest()
fd = os.open(port, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
original = termios.tcgetattr(fd)
received = bytearray()

def write_all(data):
    view = memoryview(data)
    deadline = time.monotonic() + 120
    while view:
        if time.monotonic() > deadline:
            raise TimeoutError('USB write blocked')
        if select.select([], [fd], [], 0.2)[1]:
            try:
                n = os.write(fd, view[:4096])
                view = view[n:]
                time.sleep(0.005)
            except BlockingIOError:
                pass

def collect_until(marker, seconds):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if marker in received:
            return
        if select.select([fd], [], [], 0.2)[0]:
            block = os.read(fd, 65536)
            if not block:
                raise RuntimeError('USB closed')
            received.extend(block)
            Path(output).write_bytes(received)
            if marker in received:
                return
    raise TimeoutError('No expected shell marker')

try:
    attrs = termios.tcgetattr(fd)
    attrs[0] = attrs[1] = attrs[3] = 0
    attrs[2] = termios.CS8 | termios.CREAD | termios.CLOCAL
    attrs[4] = attrs[5] = termios.B115200
    attrs[6][termios.VMIN] = attrs[6][termios.VTIME] = 0
    termios.tcsetattr(fd, termios.TCSANOW, attrs)
    fcntl.ioctl(fd, termios.TIOCMBIS, struct.pack('I', termios.TIOCM_DTR | termios.TIOCM_RTS))
    time.sleep(3)
    write_all(b'\r/bin/busybox uname -r; /bin/busybox hostname; /bin/busybox cat /proc/mounts; echo POC_IDENTIFIED\r')
    collect_until(b'\r\nPOC_IDENTIFIED\r\n', 10)
    verify_identity(received, mode)
    write_all(b'/bin/busybox stty -echo; echo POC_UPLOAD_READY; /bin/busybox uudecode; r=$?; /bin/busybox stty echo; echo POC_UPLOAD_RC:$r\r')
    collect_until(b'\r\nPOC_UPLOAD_READY\r\n', 10)
    write_all(('begin-base64 644 ' + destination + '\n').encode() + encoded + b'====\n')
    collect_until(b'\r\nPOC_UPLOAD_RC:0\r\n', 30)
    write_all(('/bin/busybox sha256sum ' + destination + '; echo POC_HASH_DONE\r').encode())
    collect_until(b'\r\nPOC_HASH_DONE\r\n', 20)
    assert (digest + '  ' + destination).encode() in received, 'RAM upload hash mismatch; do not extract'
    print(f'RAM upload verified: {len(raw)} bytes SHA256={digest}')
except BaseException:
    try:
        write_all(b'\x03\r/bin/busybox stty echo\r')
    except Exception:
        pass
    raise
finally:
    termios.tcsetattr(fd, termios.TCSANOW, original)
    os.close(fd)
