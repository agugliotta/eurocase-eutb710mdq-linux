#!/usr/bin/env python3
"""Run in Linux against the captured physical pages and the compiled decoder."""
import subprocess
import tempfile
from pathlib import Path

decoder = '/out/decode-boot1-pages'
capture = Path('/out/head-test')
boot0 = '/boot/boot0-bch-corrected.bin'
rows = '/out/head-rows.bin'
with tempfile.TemporaryDirectory() as tmp:
    tmp = Path(tmp)
    results = []
    for label in ['a', 'b']:
        result = tmp / f'{label}.bin'
        run = subprocess.run([decoder, str(capture/'capture'/f'pass-{label}.bin'),
                              str(result), boot0, rows], capture_output=True, text=True)
        assert run.returncode == 0 and run.stdout.endswith('RECORDS=5 CODEWORDS=80 FAILED=0\n')
        data = result.read_bytes()
        headers = (capture/f'decoded-{label}.bin').read_bytes()
        assert len(data) == 81920
        assert all(data[i*16384:i*16384+1024] == headers[i*1024:(i+1)*1024] for i in range(5))
        results.append(data)
    assert results[0] == results[1]
    raw = (capture/'capture/pass-a.bin').read_bytes()
    for name, data, rowdata, expected in [
        ('truncated', raw[:-1], Path(rows).read_bytes(), 2),
        ('bad-row', raw, (0).to_bytes(4, 'little'), 2),
        ('empty-rows', raw, b'', 2),
        ('uncorrectable', bytes(b ^ 1 for b in raw[:100]) + raw[100:], Path(rows).read_bytes(), 1),
    ]:
        infile, rowfile = tmp/f'{name}.raw', tmp/f'{name}.rows'
        infile.write_bytes(data); rowfile.write_bytes(rowdata)
        run = subprocess.run([decoder, str(infile), str(tmp/f'{name}.bin'), boot0, str(rowfile)],
                             capture_output=True, text=True)
        assert run.returncode == expected, (name, run.returncode, run.stdout[-100:])
        if expected == 1:
            assert 'BCH_CORRECTED_BITS=-' in run.stdout
    print('BOOT1_PAGES_PHYSICAL_REGRESSION_AND_FAILURE_TEST_OK')
