.syntax unified
.arch armv7-a
.arm
.global _start
_start:
    mrs r3, cpsr
    and r3, r3, #0x1f
    cmp r3, #0x13
    bxne lr
    mrc p15, 0, r3, c1, c0, 0
    tst r3, #4
    bxne lr
    cpsid if
    /* FEL leaves DRAM uncached/write-combine; no dirty DRAM cache to clean. */
    mrc p15, 0, r3, c1, c0, 0
    bic r3, r3, #5
    bic r3, r3, #0x1800
    dsb sy
    mcr p15, 0, r3, c1, c0, 0
    isb sy
    mov r3, #0
    mcr p15, 0, r3, c8, c7, 0
    mcr p15, 0, r3, c7, c5, 0
    dsb sy
    isb sy
    mov r0, #0
    mvn r1, #0
    ldr r2, =0x43000000
    ldr pc, =0x42000000
