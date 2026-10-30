#!/usr/bin/env python3
"""Validate four BCH-corrected boot0 copies, without changing raw captures."""
import hashlib
import json
from pathlib import Path
import struct
import sys

capture, output = map(Path, sys.argv[1:])
assert not output.exists(), 'Choose a new output directory'
transfer=json.loads((capture/'transfer.json').read_text())
for name,info in transfer['files'].items():
    assert name in ['pass-a.bin','pass-b.bin']
    data=(capture/name).read_bytes()
    assert len(data)==2260992 and hashlib.sha256(data).hexdigest()==info['sha256']
images=[];results=[]
for name in ['a','b']:
    data=(capture/f'decoded-corrected-{name}.bin').read_bytes()
    assert len(data)==128*1024
    log=(capture/f'bch-{name}.log').read_text()
    assert log.rstrip().endswith('RECORDS=128 FAILED=0')
    for block in [0,1]:
        start=block*64*1024
        assert data[start+4:start+12]==b'eGON.BT0'
        length=struct.unpack_from('<I',data,start+16)[0]
        assert length==24576
        image=data[start:start+length]
        words=list(struct.unpack('<'+str(length//4)+'I',image))
        stored=words[3];words[3]=0x5f0a6c39
        assert sum(words)&0xffffffff==stored,'Boot0 checksum failed'
        images.append(image)
        results.append({'pass':name,'physical_block':block,'length':length,'checksum':hex(stored),
                        'sha256':hashlib.sha256(image).hexdigest()})
assert all(x==images[0] for x in images),'Corrected boot0 copies disagree'
output.mkdir(parents=True)
(output/'boot0-bch-corrected.bin').write_bytes(images[0])
(output/'validation.json').write_text(json.dumps({'copies':results,'all_four_copies_identical':True,
    'source':str(capture.resolve()),'format':'boot0 payload decoded from raw1k+BCH64 records',
    'boot1_obtained':False,'restore_procedure_hardware_tested':False},indent=2)+'\n')
print(f'BOOT0_FOUR_COPIES_VALIDATED sha256={results[0]["sha256"]}')
