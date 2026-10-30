#!/usr/bin/env python3
"""Prepare, but never execute, a five-page boot1-header capture candidate."""
from pathlib import Path

root=Path(__file__).resolve().parents[2]
old=root/'.tools/overlays/nand-raw';out=root/'.tools/overlays/boot1-head'
out.mkdir(parents=True,exist_ok=True)
for name in ['nand_ids.c','sunxi_nand.c']:
    (out/name).write_bytes((old/name).read_bytes())
s=(old/'nand_base.c').read_text()
changes={
    '"eurocase-nand-boot-raw-a", "eurocase-nand-boot-raw-b"':'"eurocase-boot1-head-a", "eurocase-boot1-head-b"',
    'const unsigned int pages = 128;':'const unsigned int pages = 5;',
    'unsigned int row = index < 64 ? index : 256 + index - 64;':'unsigned int row = (index + 2) * 256;',
    'EUROCASE_NAND_RAW_CAPTURE_OK passes=2 records=128 stride=17664 rows=0..63,256..319 bytes_per_pass=2260992':'EUROCASE_BOOT1_HEAD_CAPTURE_OK passes=2 records=5 stride=17664 rows=512,768,1024,1280,1536 bytes_per_pass=88320',
}
for oldtext,newtext in changes.items():
    assert s.count(oldtext)==1,oldtext
    s=s.replace(oldtext,newtext,1)
(out/'nand_base.c').write_text(s)
print('Prepared first-page capture for blocks2..6, two passes; no device access.')
