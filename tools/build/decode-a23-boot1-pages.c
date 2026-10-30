// SPDX-License-Identifier: GPL-2.0-or-later
// Offline BCH40 decoder for the observed 16KiB+1280 A23 boot1 page layout.
#include <linux/bch.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

static uint16_t step(uint16_t s, unsigned n)
{
    while (n--) s = ((s >> 1) | (((s ^ (s >> 1)) & 1) << 14)) & 0x7fff;
    return s;
}
static unsigned char reverse(unsigned char b)
{
    unsigned char r = 0;
    for (unsigned i = 0; i < 8; i++) r = (r << 1) | ((b >> i) & 1);
    return r;
}
static uint32_t le32(const unsigned char *p)
{
    return (uint32_t)p[0] | (uint32_t)p[1]<<8 | (uint32_t)p[2]<<16 | (uint32_t)p[3]<<24;
}
int main(int argc, char **argv)
{
    if (argc != 5) {
        fprintf(stderr, "Usage: decoder RAW OUTPUT VERIFIED_BOOT0 ROWS_LE32\n");
        return 2;
    }
    FILE *raw = fopen(argv[1], "rb"), *out = fopen(argv[2], "wb");
    FILE *boot = fopen(argv[3], "rb"), *rows = fopen(argv[4], "rb");
    if (!raw || !out || !boot || !rows) return 2;
    unsigned char boot0[24576], page[17664], rowbuf[4], buf[1098];
    if (fread(boot0, 1, sizeof(boot0), boot) != sizeof(boot0) || fgetc(boot) != EOF) return 2;
    if (boot0[0x4dac] != 0x75 || boot0[0x4dad] != 0x2b) return 2;
    struct bch_control *bch = init_bch(14, 40, 0x5803);
    if (!bch || bch->ecc_bytes != 70) return 2;
    unsigned record = 0, failed = 0, errors[40];
    size_t n;
    while ((n = fread(rowbuf, 1, 4, rows))) {
        if (n != 4 || record >= 512 || fread(page, 1, sizeof(page), raw) != sizeof(page)) return 2;
        uint32_t row = le32(rowbuf);
        if (row < 512 || row >= 1792) return 2;
        unsigned seedpos = 0x4dac + (row & 127) * 2;
        uint16_t seed = boot0[seedpos] | boot0[seedpos+1] << 8;
        for (unsigned chunk = 0; chunk < 16; chunk++) {
            uint16_t state = step(seed, 15);
            for (unsigned i = 0; i < sizeof(buf); i++) {
                unsigned offset = i < 1024 ? chunk * 1024 + i : 16384 + chunk * 74 + i - 1024;
                buf[i] = reverse(page[offset] ^ (state & 255));
                state = step(state, 8);
            }
            int count = decode_bch(bch, buf, 1028, buf+1028, NULL, NULL, errors);
            if (count >= 0) {
                for (int i = 0; i < count; i++) {
                    if (errors[i] >= sizeof(buf) * 8) return 2;
                    buf[errors[i]/8] ^= 1u << (errors[i]%8);
                }
                if (decode_bch(bch, buf, 1028, buf+1028, NULL, NULL, errors)) return 2;
            } else failed++;
            printf("RECORD=%u ROW=%u CHUNK=%u BCH_CORRECTED_BITS=%d\n", record, row, chunk, count);
            for (unsigned i = 0; i < 1024; i++) buf[i] = reverse(buf[i]);
            if (fwrite(buf, 1, 1024, out) != 1024) return 2;
        }
        record++;
    }
    if (!record || fgetc(raw) != EOF || ferror(raw) || ferror(rows) || ferror(out)) return 2;
    int bad = fclose(out);
    fclose(raw); fclose(rows); fclose(boot); free_bch(bch);
    printf("RECORDS=%u CODEWORDS=%u FAILED=%u\n", record, record*16, failed);
    return bad || failed ? 1 : 0;
}
