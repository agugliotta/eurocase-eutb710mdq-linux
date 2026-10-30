#!/usr/bin/env python3
"""Bounded FEL RAM test. Writes only the specified DRAM window, then restores it."""
from pathlib import Path
import hashlib
import json
import os
import struct
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'analysis/bringup/runtime'
TOOL = ROOT / '.tools/bin/sunxi-fel'
ADDRESS, SIZE = 0x42000000, 0x10000
if len(sys.argv) != 2:
    raise SystemExit('Usage: test-fel-ram.py BUS:DEVICE (device must already be initialized)')
device = sys.argv[1]
result = {'address': hex(ADDRESS), 'bytes': SIZE, 'device': device,
          'patterns': [], 'restored_and_verified': False,
          'scope': 'One DRAM window via FEL, not a full RAM stress test'}


def command(*args):
    run = subprocess.run([str(TOOL), '--dev', device, *map(str, args)],
                         capture_output=True, timeout=20)
    if run.returncode:
        raise RuntimeError(run.stderr.decode(errors='replace') or f'FEL exit {run.returncode}')


backup = OUT / 'ram-42000000-original.bin'
readback = OUT / 'ram-42000000-readback.bin'
pattern_file = OUT / 'ram-42000000-pattern.bin'
if backup.exists():
    raise SystemExit('Existing original RAM backup retained; use a fresh reviewed run directory')
command('read', hex(ADDRESS), hex(SIZE), backup)
original = backup.read_bytes()
assert len(original) == SIZE
with backup.open('rb') as handle:
    os.fsync(handle.fileno())
result['original_sha256'] = hashlib.sha256(original).hexdigest()
patterns = [('zero', bytes(SIZE)), ('ones', bytes([255]) * SIZE),
            ('checkerboard', bytes.fromhex('55aa') * (SIZE // 2)),
            ('word_address', b''.join(struct.pack('<I', ADDRESS + n)
                                    for n in range(0, SIZE, 4))),
            ('deterministic_hash', hashlib.shake_256(b'EUTB710MDQ-FEL-test-v1').digest(SIZE))]
try:
    for name, data in patterns:
        pattern_file.write_bytes(data)
        command('write', hex(ADDRESS), pattern_file)
        command('read', hex(ADDRESS), hex(SIZE), readback)
        observed = readback.read_bytes()
        passed = observed == data
        result['patterns'].append({'name': name, 'passed': passed,
                                   'sha256': hashlib.sha256(observed).hexdigest()})
        if not passed:
            raise RuntimeError(f'RAM comparison failed: {name}')
except Exception as error:
    result['error'] = str(error)
finally:
    try:
        command('write', hex(ADDRESS), backup)
        command('read', hex(ADDRESS), hex(SIZE), readback)
        result['restored_and_verified'] = readback.read_bytes() == original
    except Exception as error:
        result['restore_error'] = str(error)
    result['passed'] = (len(result['patterns']) == len(patterns)
                        and all(p['passed'] for p in result['patterns'])
                        and result['restored_and_verified'])
    (OUT / 'ram-window-test.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
if not result['passed']:
    raise SystemExit(1)
