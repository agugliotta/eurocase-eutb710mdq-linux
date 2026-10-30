#!/usr/bin/env python3
"""Compile the actual map validator and reject malformed or wrong-device maps."""
from pathlib import Path
import subprocess
import tempfile

root = Path(__file__).resolve().parents[2]
source = (root / '.tools/overlays/wifi-rtl8188e.c').read_text()
code = source[source.index('static bool eurocase_efuse_map_valid'):source.index('static int rtl8188eu_parse_efuse')]
firmware = root / 'analysis/wifi/v1/firmware/rtlwifi/eurocase-g739-rtl8188eu-efuse.bin'
otp = root / 'analysis/wifi/v1/mainline-efuse-map.bin'
main = '''
int main(int argc, char **argv) {
    assert(argc==3);
    u8 otp[512], map[512], bad[512];
    FILE *f=fopen(argv[1],"rb");assert(f);assert(fread(otp,1,512,f)==512);fclose(f);
    f=fopen(argv[2],"rb");assert(f);assert(fread(map,1,512,f)==512);fclose(f);
    assert(eurocase_efuse_map_valid(otp,map,512));
    assert(!eurocase_efuse_map_valid(NULL,NULL,0));
    assert(!eurocase_efuse_map_valid(otp,map,511));
    assert(!eurocase_efuse_map_valid(otp,map,513));
    const unsigned offsets[]={0,1,0x10,0x1a,0xb9,0x130,0x13c};
    for(unsigned i=0;i<sizeof(offsets)/sizeof(offsets[0]);i++) {
        memcpy(bad,map,512);bad[offsets[i]]=0xff;
        assert(!eurocase_efuse_map_valid(otp,bad,512));
    }
    puts("EUROCASE_EFUSE_VALIDATOR_OK");
}
'''
with tempfile.TemporaryDirectory(prefix='eurocase-wifi-') as directory:
    p = Path(directory)
    (p/'test.c').write_text('#include <assert.h>\n#include <stdbool.h>\n#include <stdio.h>\n#include <string.h>\ntypedef unsigned char u8;\n'+code+main)
    subprocess.run(['cc','-std=c11','-Wall','-Wextra','-Werror',str(p/'test.c'),'-o',str(p/'test')],check=True)
    subprocess.run([str(p/'test'),str(otp),str(firmware)],check=True)
