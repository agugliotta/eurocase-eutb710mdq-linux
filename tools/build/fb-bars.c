#include <fcntl.h>
#include <linux/fb.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/mman.h>
#include <unistd.h>

int main(void)
{
    int fd = open("/dev/fb0", O_RDWR);
    if (fd < 0) { perror("fb0"); return 1; }
    struct fb_var_screeninfo v;
    struct fb_fix_screeninfo f;
    if (ioctl(fd, FBIOGET_VSCREENINFO, &v) || ioctl(fd, FBIOGET_FSCREENINFO, &f)) {
        perror("fb info"); close(fd); return 1;
    }
    printf("FB=%ux%u bpp=%u stride=%u bytes=%u\n", v.xres, v.yres, v.bits_per_pixel, f.line_length, f.smem_len);
    if (v.bits_per_pixel != 32 || !v.xres || !v.yres || f.smem_len > 64*1024*1024 ||
        (uint64_t)(v.yoffset+v.yres)*f.line_length > f.smem_len ||
        (uint64_t)(v.xoffset+v.xres)*4 > f.line_length ||
        v.red.length > 8 || v.green.length > 8 || v.blue.length > 8 || v.transp.length > 8 ||
        v.red.offset >= 32 || v.green.offset >= 32 || v.blue.offset >= 32 ||
        (v.transp.length && v.transp.offset >= 32))
        { close(fd); return 2; }
    unsigned char *fb = mmap(NULL, f.smem_len, PROT_READ|PROT_WRITE, MAP_SHARED, fd, 0);
    if (fb == MAP_FAILED) { perror("fb map"); close(fd); return 1; }
    void *backup = malloc(f.smem_len);
    if (!backup) { munmap(fb, f.smem_len); close(fd); return 1; }
    memcpy(backup, fb, f.smem_len);
    const unsigned rgb[8][3] = {{255,255,255},{255,255,0},{0,255,255},{0,255,0},{255,0,255},{255,0,0},{0,0,255},{0,0,0}};
    for (unsigned y=0; y<v.yres; y++) {
        uint32_t *row = (uint32_t *)(fb + (y+v.yoffset)*f.line_length) + v.xoffset;
        for (unsigned x=0; x<v.xres; x++) {
            const unsigned *c = rgb[(uint64_t)x*8/v.xres];
            row[x] = ((c[0] >> (8-v.red.length)) << v.red.offset) |
                     ((c[1] >> (8-v.green.length)) << v.green.offset) |
                     ((c[2] >> (8-v.blue.length)) << v.blue.offset) |
                     (v.transp.length ? ((1u << v.transp.length)-1) << v.transp.offset : 0);
        }
    }
    puts("COLOR_BARS_VISIBLE_15_SECONDS"); fflush(stdout);
    sleep(15);
    memcpy(fb, backup, f.smem_len);
    int matched = memcmp(fb, backup, f.smem_len) == 0;
    printf("FRAMEBUFFER_RESTORED=%d\n", matched);
    free(backup); munmap(fb, f.smem_len); close(fd);
    return matched ? 0 : 1;
}
