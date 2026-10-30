#!/usr/bin/env python3
"""Initialize fresh A23 FEL once and stage USB-debug U-Boot, without executing it."""
import hashlib
import json
from pathlib import Path
import re
import struct
import subprocess
import sys
import zlib

root=Path(__file__).resolve().parents[2]
image=(Path(sys.argv[2]).resolve() if len(sys.argv)==3 else
       root/'.tools/build/a23-sd-uboot-debug/u-boot-sunxi-with-spl.bin')
out=Path(sys.argv[1]).resolve();out.mkdir(parents=True,exist_ok=True)
assert not (out/'load-steps.json').exists(), 'Need fresh FEL and a new output directory'
blob=image.read_bytes();assert blob[4:12]==b'eGON.BT0'
header=bytearray(blob[32768:32832]);magic,hcrc,stamp,size,load,entry,dcrc=struct.unpack_from('>7I',header)
assert magic==0x27051956 and load==entry==0x4a000000
header[4:8]=b'\0'*4;assert zlib.crc32(header)==hcrc
payload=blob[32832:32832+size];assert len(payload)==size and zlib.crc32(payload)==dcrc
fel=str(root/'.tools/bin/sunxi-fel')
p=subprocess.run([fel,'--list'],capture_output=True,text=True,check=True,timeout=10)
devices=re.findall(r'USB device (\d+:\d+)\s+Allwinner A23',p.stdout)
assert len(devices)==1, 'Need one responding A23 FEL device'
device=devices[0];steps=[]
def run(args):
    p=subprocess.run([fel,'--dev',device]+args,capture_output=True,text=True,timeout=45)
    steps.append({'args':args,'rc':p.returncode,'stdout':p.stdout,'stderr':p.stderr})
    (out/'load-steps.json').write_text(json.dumps({'device':device,'steps':steps},indent=2)+'\n')
    assert p.returncode==0,p.stderr or p.stdout
    return p.stdout
assert 'soc=00001650(A23)' in run(['version'])
# The native "spl" command stages any appended U-Boot but does not execute it.
run(['-v','spl',str(image)])
assert 'soc=00001650(A23)' in run(['version'])
run(['read',hex(load),str(size),str(out/'uboot-readback.bin')])
assert (out/'uboot-readback.bin').read_bytes()==payload,'U-Boot RAM readback mismatch'
ready={'device':device,'entry':hex(entry),'verified':True,'bytes':size,
       'payload_sha256':hashlib.sha256(payload).hexdigest(),
       'combined_sha256':hashlib.sha256(blob).hexdigest(),'spl_executed_once':True}
(out/'ready.json').write_text(json.dumps(ready,indent=2)+'\n');print(json.dumps(ready,indent=2))
