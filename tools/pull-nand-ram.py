#!/usr/bin/env python3
"""Pull only two already-captured RAM files over the dedicated USB IPv6 link."""
import hashlib
import http.client
import importlib.util
import json
from pathlib import Path
import socket
import subprocess
import sys

root=Path(__file__).resolve().parents[1]
assert len(sys.argv) in [3,4]
checks, output=map(Path,sys.argv[1:3])
expected_bytes=2260992
if len(sys.argv)==4:
    layout=json.loads(Path(sys.argv[3]).read_text())
    expected_bytes=layout['bytes_per_pass']
assert isinstance(expected_bytes,int) and 0<expected_bytes<=16*1024*1024
expected=json.loads(checks.read_text())
assert set(expected)=={'pass-a.bin','pass-b.bin'}
for digest in expected.values():
    assert len(digest)==64 and all(c in '0123456789abcdef' for c in digest)
spec=importlib.util.spec_from_file_location('usb_root_server',root/'tools/serve-usb-rootfs.py')
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
inventory=subprocess.run(['/sbin/ifconfig','-a'],check=True,capture_output=True,text=True).stdout
interface,_=module.usb_address(inventory)
scope=socket.if_nametoindex(interface)
output.mkdir(parents=True,exist_ok=False)
results={}
for name,digest in expected.items():
    sock=socket.socket(socket.AF_INET6,socket.SOCK_STREAM)
    sock.settimeout(15)
    conn=http.client.HTTPConnection('eutb-usb',8081,timeout=15)
    try:
        sock.connect(('fe80::2',8081,0,scope))
        conn.sock=sock
        conn.request('GET','/'+name,headers={'Connection':'close'})
        response=conn.getresponse()
        assert response.status==200
        assert response.getheader('Content-Length')==str(expected_bytes)
        h=hashlib.sha256();count=0
        with (output/name).open('xb') as file:
            while block:=response.read(65536):
                count+=len(block)
                assert count<=expected_bytes
                file.write(block);h.update(block)
        assert count==expected_bytes and h.hexdigest()==digest,'RAM transfer hash/length mismatch'
        results[name]={'bytes':count,'sha256':h.hexdigest(),'verified_against_tablet':True}
    finally:
        conn.close();sock.close()
(output/'transfer.json').write_text(json.dumps({'interface':interface,'files':results},indent=2)+'\n')
print(json.dumps(results,indent=2))
