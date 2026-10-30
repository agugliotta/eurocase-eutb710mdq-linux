#!/usr/bin/env python3
"""Validate local candidates; never connects to the tablet."""
from pathlib import Path
import hashlib
import json
import struct

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'analysis/bringup'


def validate_spl(data):
    assert len(data) >= 32 and len(data) % 4 == 0, 'truncated or unaligned SPL'
    assert data[4:12] == b'eGON.BT0', 'unexpected SPL magic'
    length = struct.unpack_from('<I', data, 16)[0]
    assert length == len(data) and length <= 32768, 'SPL length outside diagnostic budget'
    words = list(struct.unpack('<' + str(length // 4) + 'I', data))
    expected = words[3]
    words[3] = 0x5f0a6c39
    assert sum(words) & 0xffffffff == expected, 'SPL checksum mismatch'


spl = (OUT / 'eutb710mdq-a23-fel-candidate-spl.bin').read_bytes()
validate_spl(spl)
corrupt = bytearray(spl)
corrupt[-1] ^= 1
try:
    validate_spl(corrupt)
except AssertionError:
    pass
else:
    raise AssertionError('checksum check failed to reject corruption')

config = (OUT / 'u-boot-spl.config').read_text().splitlines()
values = dict(line.split('=', 1) for line in config if line.startswith('CONFIG_') and '=' in line)
assert len(spl) <= int(values['CONFIG_SPL_MAX_SIZE'], 0) + int(values['CONFIG_SPL_TEXT_BASE'], 0), 'SPL exceeds configured load window'
for entry in ['CONFIG_MACH_SUN8I_A23=y', 'CONFIG_DRAM_CLK=552',
              'CONFIG_DRAM_ZQ=63351', 'CONFIG_DRAM_ODT_EN=y',
              'CONFIG_UART0_PORT_F=y', 'CONFIG_CONS_INDEX=1',
              'CONFIG_ENV_IS_NOWHERE=y', 'CONFIG_AXP_DCDC3_VOLT=1260']:
    assert entry in config, entry
for name in ['SPL_MMC', 'SPL_MMC_WRITE', 'SPL_NAND_SUPPORT', 'SPL_SPI',
             'SPL_VIDEO', 'SPL_OF_CONTROL', 'ENV_IS_IN_FAT', 'ENV_IS_IN_MMC']:
    assert f'CONFIG_{name}=y' not in config, name

dtb = (OUT / 'eutb710mdq-diagnostic.dtb').read_bytes()
assert struct.unpack_from('>I', dtb)[0] == 0xd00dfeed, 'invalid DTB magic'
assert struct.unpack_from('>I', dtb, 4)[0] == len(dtb), 'invalid DTB size'
check = json.loads((OUT / 'fex-crosscheck.json').read_text())
assert check['sections'] == 98 and not check['differences']
manifest = {
    'validation_scope': 'local static checks only',
    'hardware_execution_report': 'runtime/RESULTADOS.md',
    'u_boot_commit': '5508406582f6f7120dce0c4b3059819a41788db2',
    'sunxi_tools_commit': 'a08a24a2aa5804bde7fa6ea8cdb08135d018da33',
    'files': [
        {'name': p.name, 'bytes': p.stat().st_size,
         'sha256': hashlib.sha256(p.read_bytes()).hexdigest()}
        for p in [OUT / 'eutb710mdq-a23-fel-candidate-spl.bin',
                  OUT / 'eutb710mdq-diagnostic.dtb', OUT / 'u-boot-spl.config',
                  OUT / 'script0-official.fex']
    ],
    'checks': ['SPL header/length/checksum', 'corruption rejection',
               'configuration constraints', 'DTB header/length',
               'official FEX scalar crosscheck'],
}
(OUT / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
print(json.dumps(manifest, indent=2))
