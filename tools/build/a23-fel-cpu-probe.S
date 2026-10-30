.syntax unified
.arch armv7-a
.arm
.global _start
_start:
    /* Same return-to-FEL convention as sunxi-tools CP15 helpers. */
    ldr r0, =0x41001000
    mrs r1, cpsr
    str r1, [r0]
    mrc p15, 0, r1, c1, c0, 0
    str r1, [r0, #4]
    mrc p15, 0, r1, c2, c0, 0
    str r1, [r0, #8]
    str sp, [r0, #12]
    str lr, [r0, #16]
    dsb sy
    bx lr
