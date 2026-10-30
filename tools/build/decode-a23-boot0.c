// SPDX-License-Identifier: GPL-2.0-or-later
// Offline only: invert U-Boot's sunxi boot0 scrambler and BCH bit ordering.
#include <linux/bch.h>
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static uint16_t step(uint16_t state,unsigned n)
{
    while(n--)state=((state>>1)|(((state^(state>>1))&1)<<14))&0x7fff;
    return state;
}
static unsigned char reverse(unsigned char b)
{
    unsigned char r=0;
    for(unsigned i=0;i<8;i++)r=(r<<1)|((b>>i)&1);
    return r;
}
int main(int argc,char **argv)
{
    if(argc!=3 && argc!=4)return 2;
    int boot1_head=argc==4;
    if(boot1_head && strcmp(argv[3],"--boot1-head"))return 2;
    FILE *in=fopen(argv[1],"rb"),*out=fopen(argv[2],"wb");
    if(!in||!out)return 1;
    unsigned strength=boot1_head?40:64, parity=boot1_head?70:112;
    unsigned codeword=1028+parity;
    struct bch_control *bch=init_bch(14,strength,0x5803);
    if(!bch||bch->ecc_bytes!=parity)return 1;
    unsigned char raw[17664],buf[1140];unsigned errors[64],records=0,failed=0;
    size_t n;
    while((n=fread(raw,1,sizeof(raw),in))) {
        if(n!=sizeof(raw))return 1;
        if(boot1_head) {
            memcpy(buf,raw,1024);
            memcpy(buf+1024,raw+16384,4+parity);
        } else memcpy(buf,raw,codeword);
        uint16_t state=step(boot1_head?0x2b75:0x4a80,15);
        for(unsigned i=0;i<codeword;i++){buf[i]=reverse(buf[i]^(state&255));state=step(state,8);}
        int count=decode_bch(bch,buf,1028,buf+1028,NULL,NULL,errors);
        if(count>=0) {
            for(int i=0;i<count;i++) {
                if(errors[i]>=codeword*8)return 1;
                buf[errors[i]/8]^=1u<<(errors[i]%8);
            }
            if(decode_bch(bch,buf,1028,buf+1028,NULL,NULL,errors)!=0)return 1;
        } else failed++;
        printf("RECORD=%u BCH_CORRECTED_BITS=%d\n",records,count);
        for(unsigned i=0;i<codeword;i++)buf[i]=reverse(buf[i]);
        if(fwrite(buf,1,1024,out)!=1024)return 1;
        records++;
    }
    int bad=ferror(in)||ferror(out);
    if(fclose(in)||fclose(out))bad=1;
    free_bch(bch);
    printf("RECORDS=%u FAILED=%u\n",records,failed);
    return bad||failed?1:0;
}
