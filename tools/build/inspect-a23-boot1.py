#!/usr/bin/env python3
"""Inspect decoded boot1 headers; never treat header-only output as a backup."""
import hashlib
import json
from pathlib import Path
import struct
import sys


def inspect(data, full=False):
    if len(data)<32 or data[4:12]!=b'uboot\0\0\0':
        raise ValueError('Not the boot1 signature used by this boot0')
    size=struct.unpack_from('<I',data,0x14)[0]
    if size<512 or size%512 or size>5*4*1024*1024:
        raise ValueError('Invalid boot1 length/alignment for blocks2..6')
    result={'signature':'uboot','declared_bytes':size,'complete_image':False,'checksum_verified':False}
    if full:
        if len(data)!=size:
            raise ValueError('Incomplete image or trailing bytes')
        words=list(struct.unpack('<'+str(size//4)+'I',data));stored=words[3];words[3]=0x5f0a6c39
        if sum(words)&0xffffffff!=stored:
            raise ValueError('Boot1 checksum mismatch')
        result.update(complete_image=True,checksum_verified=True,sha256=hashlib.sha256(data).hexdigest())
    return result


def main():
    if sys.argv[1:] == ['--self-test']:
        data=bytearray(512);data[4:12]=b'uboot\0\0\0';struct.pack_into('<I',data,0x14,512)
        words=list(struct.unpack('<128I',data));words[3]=0x5f0a6c39;struct.pack_into('<I',data,12,sum(words)&0xffffffff)
        assert inspect(data)['checksum_verified'] is False
        assert inspect(data,True)['checksum_verified'] is True
        for bad in [data[:32], bytes(512)]:
            try:inspect(bad,True)
            except ValueError:pass
            else:raise AssertionError('Accepted invalid/incomplete boot1')
        data[100]^=1
        try:inspect(data,True)
        except ValueError:pass
        else:raise AssertionError('Accepted damaged boot1')
        print('BOOT1_INSPECTOR_SELF_TEST_OK')
        return
    data=Path(sys.argv[1]).read_bytes();full=sys.argv[2:]==['--full']
    print(json.dumps(inspect(data,full),indent=2))


if __name__=='__main__':main()
