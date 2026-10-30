#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Pinned source preparation for an owner-local build; never accesses hardware."""
import base64
import hashlib
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import urllib.request

SOURCES = {
    'linux': ('linux-6.12.tar.xz', 'https://cdn.kernel.org/pub/linux/kernel/v6.x/linux-6.12.tar.xz',
              'b1a2562be56e42afb3f8489d4c2a7ac472ac23098f1ef1c1e40da601f54625eb'),
    'uboot': ('u-boot-55084065.tar.gz', 'https://codeload.github.com/u-boot/u-boot/tar.gz/5508406582f6f7120dce0c4b3059819a41788db2',
              '9af5655e09851ece729f4bcdf36ab0c3617dbbbd2ea9f54afa3e1b01b1d589d9'),
    'buildroot': ('buildroot-2025.02.19.tar.xz', 'https://buildroot.org/downloads/buildroot-2025.02.19.tar.xz',
                  'e5e58bff1da91f022f60cefdfe280140c08023cd0aeec1e5f6f9da0ea866d69c'),
}
FIRMWARE_BASE = 'https://kernel.googlesource.com/pub/scm/linux/kernel/git/firmware/linux-firmware/+/20230210/'
RADIO_SHA = '1241ddbfc87f0495e0bf09d8b94c94680b60a3d8eeab89462b3c4d8d3e8a1ee0'
LICENSE_SHA = 'a61351665b4f264f6c631364f85b907d8f8f41f8b369533ef4021765f9f3b62e'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fetch(url, dest, expected, encoded=False):
    if dest.exists():
        if digest(dest) != expected:
            raise ValueError(f'Cached download has an invalid SHA-256: {dest.name}; remove it and retry')
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    temporary = dest.with_suffix(dest.suffix + '.part')
    print(f'Downloading {dest.name}', flush=True)
    try:
        with urllib.request.urlopen(url, timeout=120) as response, temporary.open('wb') as output:
            shutil.copyfileobj(response, output)
        if encoded:
            temporary.write_bytes(base64.b64decode(temporary.read_bytes(), validate=False))
        if digest(temporary) != expected:
            raise ValueError(f'Download SHA-256 mismatch: {dest.name}')
        temporary.replace(dest)
    finally:
        temporary.unlink(missing_ok=True)


def touch_firmware(text):
    arrays = re.findall(r'static\s*const\s*struct\s*fw_data\s*gslX680_fw_data_1024x600\s*\[\]\s*=\s*\{(.*?)\};', text, re.S)
    if len(arrays) != 1:
        raise ValueError('Expected exactly one stock gslX680_fw_data_1024x600 table')
    pattern = r'\{\s*(0x[0-9a-fA-F]+)\s*,\s*(0x[0-9a-fA-F]+)\s*\}\s*,?'
    body = arrays[0]
    pairs = [(int(a, 16), int(b, 16)) for a, b in re.findall(pattern, body)]
    if re.sub(pattern, '', body).strip() or len(pairs) < 1000 or pairs[0][0] != 0xf0:
        raise ValueError('Invalid stock touch firmware table')
    if not all((a == 0xf0 or a % 4 == 0 and 0 <= a <= 0x7c) and 0 <= b <= 0xffffffff for a, b in pairs):
        raise ValueError('Invalid touch register/value pair')
    return b''.join(struct.pack('<II', a, b) for a, b in pairs)


def calibration(text):
    data = bytes.fromhex(text)
    if len(data) != 512 or data[:2] != b'\x29\x81' or data[0xb9] == 255 or any(v > 63 for v in data[0x10:0x1b]):
        raise ValueError('Invalid RTL8188EU stock calibration map')
    return data


def prepare(project, cache):
    # Validate user input before downloading or compiling anything.
    touch = touch_firmware((project/'firmware/gslX680.cfg').read_text())
    efuse = calibration((project/'firmware/rtk_efuse_8188etv.map').read_text())
    firmware = cache/'firmware'
    (firmware/'silead').mkdir(parents=True, exist_ok=True)
    (firmware/'rtlwifi').mkdir(parents=True, exist_ok=True)
    (firmware/'silead/eurocase-g739-gsl1680-1024x600.fw').write_bytes(touch)
    (firmware/'rtlwifi/eurocase-g739-rtl8188eu-efuse.bin').write_bytes(efuse)
    fetch(FIRMWARE_BASE+'rtlwifi/rtl8188eufw.bin?format=TEXT', firmware/'rtlwifi/rtl8188eufw.bin', RADIO_SHA, True)
    fetch(FIRMWARE_BASE+'LICENCE.rtlwifi_firmware.txt?format=TEXT', firmware/'LICENCE.rtlwifi_firmware.txt', LICENSE_SHA, True)
    for name, (filename, url, sha) in SOURCES.items():
        archive = cache/'downloads'/filename
        fetch(url, archive, sha)
        target = cache/'sources'/name
        patches = sorted((project/'patches').glob('linux-*.patch')) if name == 'linux' else []
        stamp = sha + ''.join(digest(p) for p in patches)
        if (target/'.tablet-source-stamp').exists() and (target/'.tablet-source-stamp').read_text() == stamp:
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=target.parent) as directory:
            extracted = Path(directory)
            subprocess.run(['tar', '-xf', str(archive), '--strip-components=1', '-C', str(extracted)], check=True)
            for patch in patches:
                subprocess.run(['patch', '-p1', '-i', str(patch)], cwd=extracted, check=True)
            if name == 'uboot':
                board = extracted/'arch/arm/mach-sunxi/board.c'
                text = board.read_text()
                needle = '#if CONFIG_CONS_INDEX == 1 && defined(CONFIG_UART0_PORT_F)'
                if text.count(needle) != 1:
                    raise ValueError('U-Boot serial pinmux patch no longer matches')
                board.write_text(text.replace(needle, '#if !CONFIG_IS_ENABLED(SERIAL)\n\t/* Keep SD pins free when no serial console is built. */\n#elif CONFIG_CONS_INDEX == 1 && defined(CONFIG_UART0_PORT_F)'))
            if target.exists():
                shutil.rmtree(target)
            extracted.rename(target)
        (target/'.tablet-source-stamp').write_text(stamp)


if __name__ == '__main__':
    prepare(Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve())
