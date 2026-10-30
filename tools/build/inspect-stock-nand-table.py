#!/usr/bin/env python3
"""Decode the stock Toshiba ID table using its own ELF/DWARF field layout."""
import hashlib
import io
import json
from pathlib import Path
import sys
from elftools.elf.elffile import ELFFile
from elftools.dwarf.dwarf_expr import DWARFExprParser

source, output = map(Path, sys.argv[1:])
with io.BytesIO(source.read_bytes()) as stream:
    elf = ELFFile(stream)
    assert elf.elfclass == 32 and elf.little_endian
    symbols = elf.get_section_by_name('.symtab').get_symbol_by_name('ToshibaNandTbl')
    assert len(symbols) == 1
    symbol = symbols[0]
    section = elf.get_section(symbol['st_shndx'])
    start = symbol['st_value'] - section['sh_addr']
    table = section.data()[start:start + symbol['st_size']]
    structs = []
    for cu in elf.get_dwarf_info().iter_CUs():
        for die in cu.iter_DIEs():
            name = die.attributes.get('DW_AT_name')
            if die.tag == 'DW_TAG_structure_type' and name and b'NandPhyInfoPar' in name.value:
                if 'DW_AT_byte_size' in die.attributes:
                    structs.append(die)
    assert structs
    struct = structs[0]
    stride = struct.attributes['DW_AT_byte_size'].value
    assert stride and len(table) % stride == 0
    fields = []
    for member in struct.iter_children():
        if member.tag != 'DW_TAG_member':
            continue
        name = member.attributes['DW_AT_name'].value.decode()
        offset = member.attributes['DW_AT_data_member_location'].value
        if not isinstance(offset, int):
            expr = DWARFExprParser(elf.get_dwarf_info().structs).parse_expr(offset)
            assert len(expr) == 1 and expr[0].op_name == 'DW_OP_plus_uconst'
            offset = expr[0].args[0]
        typ = member.get_DIE_from_attribute('DW_AT_type')
        while 'DW_AT_byte_size' not in typ.attributes and typ.tag in ['DW_TAG_typedef', 'DW_TAG_const_type', 'DW_TAG_volatile_type']:
            typ = typ.get_DIE_from_attribute('DW_AT_type')
        size = typ.attributes.get('DW_AT_byte_size')
        size = size.value if size else None
        fields.append({'name': name, 'offset': offset, 'bytes': size})
    actual = bytes.fromhex('98 de 84 93 72 57 09 04')
    matches = []
    for offset in range(0, len(table), stride):
        entry = table[offset:offset+stride]
        if all(a == b or a == 255 for a, b in zip(entry[:8], actual)) and entry[:2] == actual[:2]:
            decoded = {}
            for field in fields:
                size = field['bytes']
                if size in [1, 2, 4, 8]:
                    value = int.from_bytes(entry[field['offset']:field['offset']+size], 'little')
                    decoded[field['name']] = value
            matches.append({'table_offset': offset, 'id_pattern': entry[:8].hex(' '),
                            'raw_entry': entry.hex(), 'decoded_integer_fields': decoded})
    result = {'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
              'tool': 'pyelftools ELF/DWARF; not REA Evidence', 'symbol': 'ToshibaNandTbl',
              'struct_size': stride, 'field_layout': fields, 'observed_id': actual.hex(' '), 'matches': matches}
    output.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({'struct_size': stride, 'matches': matches}, indent=2))
