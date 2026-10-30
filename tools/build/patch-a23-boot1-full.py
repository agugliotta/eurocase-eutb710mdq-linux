#!/usr/bin/env python3
"""Prepare only: two 43-page copies, justified by physical boot1 headers."""
import json
from pathlib import Path

root = Path(__file__).resolve().parents[2]
report = root / 'analysis/install/boot1'
headers = json.loads((report / 'head-test/headers.json').read_text())['header_candidates']
assert [h['block'] for h in headers] == list(range(2, 7))
assert all(h['both_passes_bch_valid'] and h['headers_identical'] and
           h['header']['declared_bytes'] == 704512 for h in headers)
old = root / '.tools/overlays/boot1-head'
out = root / '.tools/overlays/boot1-full'
out.mkdir(exist_ok=True)
s = (old / 'nand_base.c').read_text()
changes = {
    '"eurocase-boot1-head-a", "eurocase-boot1-head-b"':
        '"eurocase-boot1-full-a", "eurocase-boot1-full-b"',
    'const unsigned int pages = 5;': 'const unsigned int pages = 86;',
    'unsigned int row = (index + 2) * 256;':
        'unsigned int row = (index / 43 + 2) * 256 + index % 43;',
    'EUROCASE_BOOT1_HEAD_CAPTURE_OK passes=2 records=5 stride=17664 rows=512,768,1024,1280,1536 bytes_per_pass=88320':
        'EUROCASE_BOOT1_FULL_CAPTURE_OK passes=2 records=86 stride=17664 rows=512..554,768..810 bytes_per_pass=1519104',
}
for before, after in changes.items():
    assert s.count(before) == 1, before
    s = s.replace(before, after, 1)
(out / 'nand_base.c').write_text(s)
for name in ['nand_ids.c', 'sunxi_nand.c']:
    (out / name).write_bytes((old / name).read_bytes())
rows = [block * 256 + page for block in [2, 3] for page in range(43)]
assert len(rows) == len(set(rows)) == 86
layout = dict(blocks=[2, 3], rows=rows, pages_per_copy=43,
              declared_image_bytes=704512, record_bytes=17664, passes=2,
              bytes_per_pass=1519104, hardware_executed=False,
              scope='Two candidate copies, first43pages each; every BCH codeword and full checksum must validate.')
(report / 'full-layout.json').write_text(json.dumps(layout, indent=2) + '\n')
print('Prepared read-only bounded boot1 capture; no device access.')
