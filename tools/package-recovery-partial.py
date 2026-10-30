#!/usr/bin/env python3
"""Create and fully verify a LOCAL partial recovery archive, never a flash image."""
import gzip
import hashlib
import io
import json
from pathlib import Path
import tarfile

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'analysis/install/recovery-package'
OUT.mkdir(exist_ok=True)
archive=OUT/'eutb710mdq-PARTIAL-recovery.tar.gz'
assert not archive.exists(), 'Existing recovery archive preserved'
selected=set()
for folder in ['acquisition/originals','acquisition/physical-boot','analysis/usb-root/image',
               'analysis/install/nand-raw/bch-include',
               'analysis/peripherals/revision3/image','tools/build','tools/board']:
    selected.update(p for p in (ROOT/folder).rglob('*') if p.is_file() and not p.is_symlink() and '__pycache__' not in p.parts)
for name in ['acquisition/SHA256SUMS','analysis/install/nand-raw/capture/pass-a.bin',
             'analysis/install/nand-raw/capture/pass-b.bin','analysis/install/nand-raw/capture/transfer.json',
             'analysis/install/nand-raw/capture/decoded-corrected-a.bin','analysis/install/nand-raw/capture/decoded-corrected-b.bin',
             'analysis/install/nand-raw/capture/bch-a.log','analysis/install/nand-raw/capture/bch-b.log',
             'analysis/install/nand-raw/layout.json','analysis/install/nand-raw/RESULTADOS.md',
             'analysis/rootfs-usb/rootfs.tar.gz','analysis/rootfs-usb/manifest.json',
             'analysis/install/boot1/RESULTADOS.md','analysis/install/boot1/loader-layout.json',
             'analysis/bringup/eutb710mdq-a23-fel-candidate-spl.bin','tools/run-tablet.py',
             'tools/backup-stock-partitions.py','tools/pull-nand-ram.py','tools/serve-usb-rootfs.py',
             'tools/package-recovery-partial.py']:
    p=ROOT/name;assert p.is_file(),name;selected.add(p)
source=ROOT/'.tools/sources/u-boot-5508406582f6f7120dce0c4b3059819a41788db2'
for name in ['lib/bch.c','include/linux/bch.h','tools/sunxi-spl-image-builder.c']:
    selected.add(source/name)
selected.update(p for p in (ROOT/'analysis/install/boot1').glob('rea-*.json') if p.stat().st_size)

def digest(file):
    h=hashlib.sha256()
    while data:=file.read(1024*1024):h.update(data)
    return h.hexdigest()

files={}
for p in sorted(selected):
    with p.open('rb') as f:h=digest(f)
    files[p.relative_to(ROOT).as_posix()]={'bytes':p.stat().st_size,'sha256':h}
manifest={'device':'Eurocase EUTB_710MDQ / A23 / polaris-g739','status':'PARTIAL RECOVERY; NOT A FLASH IMAGE',
          'physical_boot0_validated':True,'physical_boot1_available':False,'full_nand_available':False,
          'restore_hardware_tested':False,'files':files}
readme=('PARTIAL RECOVERY ARCHIVE - LOCAL MAC FILES ONLY\n'
        'This is NOT an installer and must NOT be written directly to NAND.\n'
        'Contains original Android artifacts and validated decoded boot0, plus RAM Linux baselines.\n'
        'Missing boot1 and full physical NAND/OOB; full restoration remains unproven.\n'
        'boot0-bch-corrected.bin is a decoded payload, requiring correct ECC/randomizer/page layout to restore.\n'
        'No automatic firmware-write procedure is included. Stock reboot efex in the RAM launcher writes BCB/misc after backup.\n'
        'Keep this archive on the Mac/off-device. Extract to a new local folder for inspection.\n'
        'RECOVERY-MANIFEST.json records every file size and SHA256. This package was re-read and verified after creation.\n').encode()
with archive.open('xb') as file,gzip.GzipFile(fileobj=file,mode='wb',mtime=0) as gz,tarfile.open(fileobj=gz,mode='w',format=tarfile.USTAR_FORMAT) as tar:
    for name,data in [('README-RECOVERY.txt',readme),('RECOVERY-MANIFEST.json',(json.dumps(manifest,indent=2)+'\n').encode())]:
        info=tarfile.TarInfo(name);info.size=len(data);info.mode=0o600;tar.addfile(info,io.BytesIO(data))
    for name,record in files.items():
        p=ROOT/name;info=tarfile.TarInfo(name);info.size=record['bytes'];info.mode=0o600
        with p.open('rb') as f:tar.addfile(info,f)
with tarfile.open(archive,'r:gz') as tar:
    seen=set()
    for info in tar:
        assert info.isfile() and not info.name.startswith('/') and '..' not in Path(info.name).parts
        if info.name in ['README-RECOVERY.txt','RECOVERY-MANIFEST.json']:continue
        assert info.name in files and info.size==files[info.name]['bytes']
        with tar.extractfile(info) as file:assert digest(file)==files[info.name]['sha256'],info.name
        seen.add(info.name)
    assert seen==set(files)
with archive.open('rb') as f:h=digest(f)
(OUT/'archive.sha256').write_text(h+'  '+archive.name+'\n')
(OUT/'inventory.json').write_text(json.dumps({'archive':archive.name,'bytes':archive.stat().st_size,'sha256':h,
    'verified_members':len(files),'partial_recovery_only':True,'restore_tested':False},indent=2)+'\n')
print(f'LOCAL_PARTIAL_RECOVERY_ARCHIVE_VERIFIED files={len(files)} bytes={archive.stat().st_size} sha256={h}')
