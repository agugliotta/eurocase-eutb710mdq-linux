# Only read from microSD. No environment save and no NAND fallback.
setenv bootargs 'console=tty0 console=ttyGS0,115200 maxcpus=2 clk_ignore_unused loglevel=3 panic=0 root=/dev/mmcblk0p2 rootfstype=squashfs rootwait ro init=/sbin/init consoleblank=0'
if fatload mmc 0:1 0x42000000 zImage; then
    if fatload mmc 0:1 0x43000000 board.dtb; then
        bootz 0x42000000 - 0x43000000
    fi
fi
