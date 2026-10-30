#!/usr/bin/env python3
"""Stage Linux and U-Boot in fresh FEL; initialize DRAM once; do not jump."""
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import sys
import zlib

root = Path(__file__).resolve().parents[2]
out = Path(sys.argv[1]).resolve()
assert not out.exists(), 'Use a fresh FEL session and a new output directory'
image = (Path(sys.argv[2]).resolve() if len(sys.argv) >= 3 else
         root / '.tools/build/a23-sd-uboot-ram-handoff/u-boot-sunxi-with-spl.bin')
linux_image = (Path(sys.argv[3]).resolve() if len(sys.argv) == 4 else
               root / 'analysis/sd/ramboot-image')
blob = image.read_bytes()
header = bytearray(blob[32768:32832])
magic, hcrc, _, size, load, entry, dcrc = struct.unpack_from('>7I', header)
header[4:8] = bytes(4)
assert magic == 0x27051956 and zlib.crc32(header) == hcrc
payload = blob[32832:32832 + size]
assert len(payload) == size and zlib.crc32(payload) == dcrc
assert load == entry == 0x4a000000
assert (b'preboot=bootz 0x42000000 - 0x43000000\0' in payload or
        b'preboot=mw.l 0x01c20cb8 0; bootz 0x42000000 - 0x43000000\0' in payload)
watchdog = b'preboot=mw.l 0x01c20cb8 0; bootz 0x42000000 - 0x43000000\0' in payload
if watchdog:
    stub = image.parent / 'watchdog-entry.bin'
    manifest = json.loads((image.parent / 'trace-manifest.json').read_text())
    assert hashlib.sha256(blob).hexdigest() == manifest['combined_sha256']
    assert hashlib.sha256(stub.read_bytes()).hexdigest() == manifest['watchdog_entry_sha256']
subprocess.run([sys.executable, str(root / 'tools/build/load-a23-linux-fel.py'),
                str(linux_image), str(out)], check=True)
ready = json.loads((out / 'ready-to-execute.json').read_text())
assert ready['verified']
source = out / 'uboot-payload.bin'
source.write_bytes(payload)
steps = []
for args in [['write', hex(load), str(source)],
             ['read', hex(load), str(size), str(out / 'uboot-readback.bin')]]:
    p = subprocess.run([str(root / '.tools/bin/sunxi-fel'), '--dev',
                        ready['device']] + args, capture_output=True, text=True, timeout=45)
    steps.append(dict(args=args, rc=p.returncode, stdout=p.stdout, stderr=p.stderr))
    (out / 'uboot-load-steps.json').write_text(json.dumps(steps, indent=2) + '\n')
    assert p.returncode == 0, p.stderr
assert (out / 'uboot-readback.bin').read_bytes() == payload
if watchdog:
    clear = out / 'trace-clear.bin'
    clear.write_bytes(bytes(4112))
    for address, source in [(0x41004000, stub), (0x4f000000, clear)]:
        target = out / (source.name + '-readback.bin')
        for args in [['write', hex(address), str(source)],
                     ['read', hex(address), str(source.stat().st_size), str(target)]]:
            p = subprocess.run([str(root / '.tools/bin/sunxi-fel'), '--dev',
                                ready['device']] + args, capture_output=True, text=True, timeout=45)
            steps.append(dict(args=args, rc=p.returncode, stdout=p.stdout, stderr=p.stderr))
            (out / 'uboot-load-steps.json').write_text(json.dumps(steps, indent=2) + '\n')
            assert p.returncode == 0, p.stderr
        assert target.read_bytes() == source.read_bytes()
    entry = 0x41004000
result = dict(device=ready['device'], entry=hex(entry), verified=True,
              combined_sha256=hashlib.sha256(blob).hexdigest(),
              payload_sha256=hashlib.sha256(payload).hexdigest(),
              kernel_and_dtb_verified=True, spl_executed_once=True,
              watchdog_16s=watchdog)
(out / 'uboot-ready.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result, indent=2))
