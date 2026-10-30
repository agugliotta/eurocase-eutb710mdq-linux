#!/usr/bin/env python3
"""Convert the exact stock 1024x600 Silead table to Linux offset/value pairs."""
import hashlib
import json
from pathlib import Path
import re
import struct

root = Path(__file__).resolve().parents[2]
source = root / 'acquisition/originals/board-config/gslX680.cfg'
text = source.read_text()
name = 'gslX680_fw_data_1024x600'
arrays = re.findall(r'staticconststructfw_data' + name + r'\[\]\s*=\s*\{(.*?)\};', text, re.S)
assert len(arrays) == 1, 'Missing or ambiguous board firmware table'
body = arrays[0]
pattern = r'\{\s*(0x[0-9a-fA-F]+)\s*,\s*(0x[0-9a-fA-F]+)\s*\}\s*,?'
pairs = [(int(a, 16), int(b, 16)) for a, b in re.findall(pattern, body)]
assert not re.sub(pattern, '', body).strip(), 'Unparsed firmware content'
assert len(pairs) > 1000 and pairs[0][0] == 0xf0
assert all((a == 0xf0 or a % 4 == 0 and 0 <= a <= 0x7c) and 0 <= b <= 0xffffffff
           for a, b in pairs), 'Unexpected register address or value'
data = b''.join(struct.pack('<II', a, b) for a, b in pairs)
assert list(struct.iter_unpack('<II', data)) == pairs
output = root / 'analysis/peripherals/firmware/silead/eurocase-g739-gsl1680-1024x600.fw'
output.parent.mkdir(parents=True, exist_ok=True)
output.write_bytes(data)
metadata = {'source': str(source), 'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
            'selected_table': name, 'entries': len(pairs), 'bytes': len(data),
            'sha256': hashlib.sha256(data).hexdigest(),
            'format': 'Little-endian u32 offset + u32 value, as consumed by Linux silead.c',
            'hardware_tested': False}
output.with_suffix('.json').write_text(json.dumps(metadata, indent=2) + '\n')
print(json.dumps(metadata, indent=2))
