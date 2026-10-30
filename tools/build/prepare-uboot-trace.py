#!/usr/bin/env python3
"""Generate temporary U-Boot init checkpoints; never edit upstream sources."""
from pathlib import Path

root = Path(__file__).resolve().parents[2]
src = root / '.tools/sources/u-boot-5508406582f6f7120dce0c4b3059819a41788db2'
out = root / '.tools/overlays'
s = (src / 'include/initcall.h').read_text()
needle = '#define INITCALL(_call)'
assert s.count(needle) == 1
helper = r'''/* Temporary A23 RAM breadcrumbs, retained if a watchdog reset preserves DRAM. */
#ifndef CONFIG_XPL_BUILD
static inline void tablet_trace(unsigned long fn, unsigned long phase)
{
    volatile unsigned long *p = (void *)0x4f001000;
    p[0] = 0x45555442;
    p[1] = fn;
    p[2] = phase;
    __asm__ volatile("mcr p15, 0, %0, c7, c10, 1\n\tdsb sy" : : "r"(p) : "memory");
}
#else
#define tablet_trace(fn, phase) do { } while (0)
#endif

'''
s = s.replace(needle, helper + needle)
s = s.replace('\t\tif (_call()) { \\',
              '\t\ttablet_trace((unsigned long)(_call), 1); \\\n\t\tif (_call()) { \\\n\t\t\ttablet_trace((unsigned long)(_call), 3); \\')
needle = '\t} while (0)'
assert s.count(needle) == 2
s = s.replace(needle, '\t\ttablet_trace((unsigned long)(_call), 2); \\\n' + needle, 1)
(out / 'sd-uboot-initcall-trace.h').write_text(s)
s = (src / 'arch/arm/cpu/armv7/start.S').read_text()
needle = 'reset:\n'
assert s.count(needle) == 1
s = s.replace(needle, '''reset:
#ifndef CONFIG_XPL_BUILD
    ldr r12, =0x4f001000
    ldr r4, =0x45555442
    str r4, [r12]
    adr r4, reset
    str r4, [r12, #4]
    mov r4, #0
    str r4, [r12, #8]
    dsb sy
#endif
''')
def marker(phase):
    return f'''#ifndef CONFIG_XPL_BUILD
    ldr r12, =0x4f001008
    mov r4, #{phase}
    str r4, [r12]
    dsb sy
#endif
'''
for call, before, after in [('cpu_init_cp15', 10, 11), ('cpu_init_crit', 12, 13)]:
    needle = f'\tbl\t{call}\n'
    assert s.count(needle) == 1
    s = s.replace(needle, marker(before) + needle + marker(after))
needle = '\tbl\t_main\n'
assert s.count(needle) == 1
s = s.replace(needle, marker(14) + needle)
(out / 'sd-uboot-start-trace.S').write_text(s)
