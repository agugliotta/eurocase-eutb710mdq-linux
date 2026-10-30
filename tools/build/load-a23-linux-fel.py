#!/usr/bin/env python3
"""Load a verified diagnostic image in a FRESH A23 FEL session; do not jump."""
import hashlib
import json
from pathlib import Path
import re
import struct
import subprocess
import sys
import time

root = Path(__file__).resolve().parents[2]
image, out = [Path(p).resolve() for p in sys.argv[1:]]
out.mkdir(parents=True, exist_ok=True)
log = out / 'load-steps.json'
assert not log.exists(), 'Existing load attempt: recover a fresh FEL session and use a new output directory'
manifest = json.loads((image / 'manifest.json').read_text())
names = ['cpu-probe.bin', 'linux-entry.bin', 'zImage', 'board.dtb']
if 'initramfs.cpio.gz' in manifest['files']:
    names.append('initramfs.cpio.gz')
    assert 0 < (image/'initramfs.cpio.gz').stat().st_size < 16 * 1024 * 1024
    assert manifest['initrd_address'] == '0x44000000'
for name in names:
    assert hashlib.sha256((image/name).read_bytes()).hexdigest() == manifest['files'][name], name
spl = root / 'analysis/bringup/eutb710mdq-a23-fel-candidate-spl.bin'
assert hashlib.sha256(spl.read_bytes()).hexdigest() == 'bcb220f131b822f86b508b756526c520a6afcf3d8380660d97f5f1c3eb9ece7c'
fel = str(root / '.tools/bin/sunxi-fel')
device = None
for _ in range(10):
    p = subprocess.run([fel, '--list'], capture_output=True, text=True, timeout=12)
    devices = re.findall(r'USB device (\d+:\d+)\s+Allwinner A23', p.stdout)
    assert len(devices) <= 1, 'Ambiguous A23 targets'
    if devices:
        device = devices[0]
        break
    time.sleep(2)
assert device, 'No responding A23 FEL; no payload sent'
steps = []

def run(args):
    p = subprocess.run([fel, '--dev', device] + args, capture_output=True, text=True, timeout=45)
    steps.append({'args': args, 'returncode': p.returncode, 'stdout': p.stdout, 'stderr': p.stderr})
    log.write_text(json.dumps({'device': device, 'steps': steps}, indent=2) + '\n')
    if p.returncode:
        raise RuntimeError(p.stderr or p.stdout)
    return p.stdout

def transfer(address, name):
    source = image / name
    target = out / (name + '-readback.bin')
    run(['write', hex(address), str(source)])
    run(['read', hex(address), str(source.stat().st_size), str(target)])
    assert source.read_bytes() == target.read_bytes(), name

assert 'soc=00001650(A23)' in run(['version'])
run(['-v', 'spl', str(spl)])
run(['version'])
transfer(0x41002000, 'cpu-probe.bin')
run(['exe', '0x41002000'])
run(['read', '0x41001000', '20', str(out/'cpu-state.bin')])
run(['version'])
values = struct.unpack('<5I', (out/'cpu-state.bin').read_bytes())
state = dict(zip(['cpsr', 'sctlr', 'ttbr0', 'sp', 'lr'], map(hex, values)))
(out/'cpu-state.json').write_text(json.dumps(state, indent=2) + '\n')
assert values[0] & 31 == 19 and values[1] & 4 == 0, 'SVC/D-cache prerequisites failed'
for address, name in [(0x42000000, 'zImage'), (0x43000000, 'board.dtb'), (0x41000000, 'linux-entry.bin')]:
    transfer(address, name)
if 'initramfs.cpio.gz' in names:
    transfer(0x44000000, 'initramfs.cpio.gz')
(out/'ready-to-execute.json').write_text(json.dumps({
    'device': device, 'verified': True, 'entry': '0x41000000',
    'files': {name: manifest['files'][name] for name in names if name != 'cpu-probe.bin'},
}, indent=2) + '\n')
print('SPL ejecutado una vez; sonda CPU retornó a FEL; tres payloads verificados en RAM. Sin salto al kernel todavía.')
