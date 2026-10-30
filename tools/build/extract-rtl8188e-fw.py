#!/usr/bin/env python3
import hashlib
import json
from pathlib import Path
import struct
from elftools.elf.elffile import ELFFile

source = Path('/mods/8188eu.ko')
with source.open('rb') as stream:
    elf = ELFFile(stream)
    symbols = elf.get_section_by_name('.symtab').get_symbol_by_name('Rtl8188EFwImgArray')
    assert symbols and len(symbols) == 1
    symbol = symbols[0]
    section = elf.get_section(symbol['st_shndx'])
    offset, length = symbol['st_value'], symbol['st_size']
    data = section.data()[offset:offset+length]
    assert len(data) == length == 13904
signature = struct.unpack_from('<H', data)[0]
assert signature & 0xfff0 == 0x88e0, hex(signature)
out = Path('/out/rtlwifi/rtl8188eufw.bin')
out.parent.mkdir(parents=True, exist_ok=True)
out.write_bytes(data)
out.with_suffix('.json').write_text(json.dumps({
    'source': source.name, 'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
    'symbol': 'Rtl8188EFwImgArray', 'bytes': len(data), 'signature': hex(signature),
    'sha256': hashlib.sha256(data).hexdigest(), 'hardware_tested': False,
}, indent=2) + '\n')
print('Stock RTL8188E firmware extracted:', len(data), 'bytes')
