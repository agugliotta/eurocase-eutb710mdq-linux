#!/usr/bin/env python3
"""Prepare/read stock logical backups; never reboot, mount or write on tablet."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

ROOT=Path(__file__).resolve().parents[1]
SERIAL='REPLACE_WITH_YOUR_ADB_SERIAL'
PARTS={'boot-resource':('nanda',32768),'env':('nandb',16384),'boot':('nandc',16384),
       'system':('nandd',655360),'misc':('nandf',16384),'recovery':('nandg',32768),
       'databk':('nandi',131072)}


def command(args,timeout=120):
    p=subprocess.run(['adb','-s',SERIAL,*args],capture_output=True,text=True,timeout=timeout)
    if p.returncode:raise RuntimeError(p.stderr or p.stdout)
    return p.stdout.replace('\r','').strip()


def mounted_rw(mounts,block,alias):
    for line in mounts.splitlines():
        fields=line.split()
        points={'/'+alias}
        if alias=='boot-resource':points.add('/bootloader')
        if len(fields)>=4 and (fields[0] in ['/dev/block/'+block,'/dev/block/by-name/'+alias] or fields[1] in points):
            if 'rw' in fields[3].split(','):return True
    return False


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--read-from-adb',action='store_true')
    p.add_argument('--parts',nargs='+',choices=PARTS,default=list(PARTS))
    args=p.parse_args()
    total=sum(PARTS[n][1]*1024 for n in args.parts)
    print(json.dumps({'mode':'ADB READS' if args.read_from_adb else 'PLAN ONLY; no USB access',
        'serial':SERIAL,'partitions':args.parts,'total_bytes':total,
        'physical_boot0_boot1_included':False,'data_and_UDISK_included':False},indent=2),flush=True)
    if not args.read_from_adb:return
    if command(['shell','getprop ro.product.model'])!='EUTB_710MDQ' or not command(['shell','id']).startswith('uid=0('):
        raise RuntimeError('Expected rooted stock tablet; no reads started')
    partitions=command(['shell','cat /proc/partitions'])
    mounts=command(['shell','cat /proc/mounts'])
    busybox=command(['shell','command -v busybox'])
    if not re.fullmatch(r'/(?:system/(?:xbin|bin)|sbin)/busybox',busybox):
        raise RuntimeError('No trusted-path stock BusyBox for device SHA256; no fallback/push performed')
    for name in args.parts:
        block,kib=PARTS[name]
        if not re.search(r'^\s*93\s+\d+\s+'+str(kib)+r'\s+'+block+r'\s*$',partitions,re.M):
            raise RuntimeError('Unexpected partition map: '+name)
        if mounted_rw(mounts,block,name):
            raise RuntimeError('Selected filesystem mounted RW: '+name+'; use a suitable stock recovery session')
    parent=ROOT/'acquisition/logical-stock';parent.mkdir(exist_ok=True)
    if shutil.disk_usage(parent).free<total+512*1024*1024:raise RuntimeError('Insufficient Mac free space')
    output=Path(tempfile.mkdtemp(prefix='read-',dir=parent))
    (output/'mounts.txt').write_text(mounts+'\n');(output/'partitions.txt').write_text(partitions+'\n')
    manifest={'serial':SERIAL,'physical_nand_backup':False,'requested_parts':args.parts,'complete':False,'files':{}}
    (output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    for name in args.parts:
        block,kib=PARTS[name];device='/dev/block/'+block
        def device_hash():
            value=command(['shell',busybox,'sha256sum',device],timeout=900).split()[0]
            if not re.fullmatch('[0-9a-f]{64}',value):raise RuntimeError('Invalid device hash')
            return value
        before=device_hash()
        command(['pull',device,str(output/(name+'.img'))],timeout=1800)
        target=output/(name+'.img')
        h=hashlib.sha256()
        with target.open('rb') as file:
            while data:=file.read(1024*1024):h.update(data)
        if target.stat().st_size!=kib*1024 or h.hexdigest()!=before or device_hash()!=before:
            raise RuntimeError('Length/hash changed; copy not validated: '+name)
        manifest['files'][name+'.img']={'device':device,'bytes':target.stat().st_size,'sha256':before,
                                      'device_hash_before_and_after_match':True}
        (output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
        print('Verified '+name,flush=True)
    manifest['complete']=True
    (output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(str(output))


if __name__=='__main__':main()
