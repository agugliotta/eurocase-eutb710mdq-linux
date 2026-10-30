# SPDX-License-Identifier: GPL-2.0-or-later
"""Offline regression checks for owner inputs and verified downloads."""
import hashlib
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import support


class BuildInputs(unittest.TestCase):
    def test_touch_accepts_stock_compact_syntax_and_preserves_bytes(self):
        text = 'staticconststructfw_datagslX680_fw_data_1024x600[]={'+ '{0xf0,0x1},'+ '{0x0,0x12345678},'*1000 + '};'
        result = support.touch_firmware(text)
        self.assertEqual(result[:16], bytes.fromhex('f0000000010000000000000078563412'))
        self.assertEqual(len(result), 1001*8)
        for bad in [text+text, text.replace('0x12345678', 'bad'), text.replace('0x0,', '0x81,'), '']:
            with self.subTest(value=bad[:60]), self.assertRaises(ValueError):
                support.touch_firmware(bad)

    def test_calibration_bounds(self):
        data = bytearray(512)
        data[:2] = b'\x29\x81'
        data[0xb9] = 0x1e
        self.assertEqual(support.calibration(data.hex()), data)
        for size, index, value in [(511, 0, 0x29), (512, 0, 0), (512, 0x10, 64), (512, 0xb9, 255)]:
            bad = data[:size]
            bad[index] = value
            with self.subTest(size=size, index=index), self.assertRaises(ValueError):
                support.calibration(bad.hex())

    def test_cached_download_is_verified_before_reuse(self):
        with tempfile.TemporaryDirectory() as directory:
            dest = Path(directory)/'source.tar'
            dest.write_bytes(b'verified')
            with patch.object(support.urllib.request, 'urlopen') as download:
                support.fetch('unused', dest, hashlib.sha256(b'verified').hexdigest())
                download.assert_not_called()
                with self.assertRaisesRegex(ValueError, 'Cached download'):
                    support.fetch('unused', dest, '0'*64)
            self.assertEqual(dest.read_bytes(), b'verified')

    def test_failed_download_is_not_cached(self):
        with tempfile.TemporaryDirectory() as directory:
            dest = Path(directory)/'source.tar'
            with patch.object(support.urllib.request, 'urlopen', side_effect=OSError('offline')):
                with self.assertRaises(OSError):
                    support.fetch('unused', dest, '0'*64)
            self.assertFalse(dest.exists())
            self.assertFalse(dest.with_suffix('.tar.part').exists())

    def test_missing_inputs_fail_before_docker(self):
        project = Path(__file__).resolve().parents[2]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/'build.sh').write_bytes((project/'build.sh').read_bytes())
            result = subprocess.run(['sh', str(root/'build.sh')], text=True, capture_output=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('Missing firmware/gslX680.cfg', result.stderr)
            self.assertNotIn('docker', result.stderr.lower())


if __name__ == '__main__':
    unittest.main()
