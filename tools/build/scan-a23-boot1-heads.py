#!/usr/bin/env python3
"""Inspect five decoded headers; requires successful BCH in both RAM captures."""
import importlib.util
import json
from pathlib import Path
import re
import sys

folder=Path(sys.argv[1])
spec=importlib.util.spec_from_file_location('boot1_format',Path(__file__).with_name('inspect-a23-boot1.py'))
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
payloads={};errors={}
for label in ['a','b']:
    payloads[label]=(folder/f'decoded-{label}.bin').read_bytes()
    assert len(payloads[label])==5*1024
    rows=re.findall(r'^RECORD=(\d+) BCH_CORRECTED_BITS=(-?\d+)$',(folder/f'decode-{label}.log').read_text(),re.M)
    assert [int(i) for i,n in rows]==list(range(5))
    errors[label]=[int(n) for i,n in rows]
result=[]
for index,block in enumerate(range(2,7)):
    a=payloads['a'][index*1024:(index+1)*1024];b=payloads['b'][index*1024:(index+1)*1024]
    entry={'block':block,'row':block*256,'bch_corrected_bits':[errors['a'][index],errors['b'][index]],
           'both_passes_bch_valid':min(errors['a'][index],errors['b'][index])>=0,
           'headers_identical':a==b,'complete_boot1_obtained':False}
    if entry['both_passes_bch_valid'] and entry['headers_identical']:
        try:entry['header']=module.inspect(a)
        except ValueError as error:entry['rejection']=str(error)
    result.append(entry)
print(json.dumps({'header_candidates':result,'complete_boot1_obtained':False},indent=2))
