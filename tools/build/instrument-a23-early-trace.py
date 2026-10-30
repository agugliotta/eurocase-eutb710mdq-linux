#!/usr/bin/env python3
"""Patch a disposable U-Boot source copy with one RTC GP breadcrumb."""
import json
from pathlib import Path
import re

root = Path('/src')
mapping = {'1': 'reset entry', '2': 'after cpu_init_cp15',
           '3': 'after cpu_init_crit', '4': 'before _main'}
p = root / 'arch/arm/cpu/armv7/start.S'
s = p.read_text()
macro = '''
/* Eurocase diagnostic: GP2 checkpoint; GP0/GP1/GP3 untouched. */
.macro EU_TRACE number
    ldr r0, =0x01f00108
    ldr r1, =(0xe1000000 | \\number)
    str r1, [r0]
    dsb sy
.endm
'''
assert s.count('reset:\n') == 1
s = s.replace('reset:\n', macro + '\nreset:\n\tEU_TRACE 1\n')
for old, new in [('\tbl\tcpu_init_cp15', '\tbl\tcpu_init_cp15\n\tEU_TRACE 2'),
                 ('\tbl\tcpu_init_crit', '\tbl\tcpu_init_crit\n\tEU_TRACE 3'),
                 ('\tbl\t_main', '\tEU_TRACE 4\n\tbl\t_main')]:
    assert s.count(old) == 1, old
    s = s.replace(old, new)
p.write_text(s)

for filename, base in [('board_f.c', 0x10000), ('board_r.c', 0x20000)]:
    p = root / 'common' / filename
    s = p.read_text()
    header = f'#define EU_TRACE_BASE {base}\n'
    s = s.replace('#include <initcall.h>', header + '#include <initcall.h>')
    p.write_text(s)
    for line, text in enumerate(s.splitlines(), 1):
        match = re.search(r'\b(INITCALL|INITCALL_EVT)\((.+)\)', text)
        if match:
            mapping[str(base + line)] = f'{filename}:{line} {match.group(0)}'

p = root / 'include/initcall.h'
s = p.read_text()
point = '#define INITCALL(_call)'
assert point in s
trace = '''#ifdef EU_TRACE_BASE
static inline void eu_trace(unsigned int stage, unsigned int state)
{
    volatile unsigned int *gp2 = (void *)0x01f00108;
    *gp2 = 0xe0000000 | state | EU_TRACE_BASE | stage;
    __asm__ volatile("dsb sy" ::: "memory");
}
#define EU_POINT(state) eu_trace(__LINE__, state)
#else
#define EU_POINT(state) do { } while (0)
#endif

'''
s = s.replace(point, trace + point)
s = s.replace('do { \\\n\t\tif (_call())', 'do { \\\n\t\tEU_POINT(0x0b000000); \\\n\t\tif (_call())')
s = s.replace('do { \\\n\t\tif (event_notify_null(_evt))', 'do { \\\n\t\tEU_POINT(0x0b000000); \\\n\t\tif (event_notify_null(_evt))')
s = s.replace('\t\t\thang(); \\', '\t\t\tEU_POINT(0x0f000000); \\\n\t\t\thang(); \\')
s = s.replace('\t\t} \\\n\t} while (0)', '\t\t} \\\n\t\tEU_POINT(0x0a000000); \\\n\t} while (0)')
assert s.count('EU_POINT(0x0b000000)') == 2
assert s.count('EU_POINT(0x0a000000)') == 2
assert s.count('EU_POINT(0x0f000000)') == 2
p.write_text(s)
Path('/out/trace-map.json').write_text(json.dumps(mapping, indent=2) + '\n')
