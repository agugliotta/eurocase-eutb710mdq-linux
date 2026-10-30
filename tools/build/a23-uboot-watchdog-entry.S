.syntax unified
.arch armv7-a
.arm
.global _start
_start:
    /* A23 sun6i watchdog: base 0x01c20ca0, offsets from sunxi_wdt.c. */
    ldr r3, =0x01c20ca0
    ldr r4, [r3, #0x14]
    bic r4, r4, #3
    orr r4, r4, #1
    str r4, [r3, #0x14]
    mov r4, #0xb1
    str r4, [r3, #0x18]
    ldr r4, =0x14af
    str r4, [r3, #0x10]
    dsb sy
    ldr pc, =0x4a000000
