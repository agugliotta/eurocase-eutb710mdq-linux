#!/usr/bin/env python3
"""Exercise the actual C power UI and request code, without USB or real actions."""
from pathlib import Path
import subprocess
import tempfile

source = Path(__file__).with_name('tablet-poc.c').read_text()
# Build the platform-independent slice of the app on the development machine.
code = source[source.index('// Both ends'):source.index('static int ui(void)')]
checks = source[source.index('        for (int which=4;'):source.index('        snd_config_t *cfg=NULL;')]
headers = '''
#include <assert.h>
#include <errno.h>
#include <stdio.h>
#include <string.h>
#include <sys/wait.h>
#include <unistd.h>
'''
mock = '''
static int expected_action, fail_exec;
static int mock_execl(const char *path, const char *arg, char *end)
{
    assert(!strcmp(path, expected_action == 5 ? "/sbin/poweroff" : "/sbin/reboot"));
    assert(!strcmp(arg, expected_action == 5 ? "poweroff" : "reboot"));
    assert(end == NULL);
    if (fail_exec) return -1;
    _exit(0);
}
#define execl mock_execl
'''
main = '''
int main(void)
{
CHECKS
    screen=tmpfile();assert(screen);
    page(4);page(5);page(6);
    rewind(screen);
    char rendered[8192]={0};
    assert(fread(rendered,1,sizeof(rendered)-1,screen)>0);
    assert(strstr(rendered,"APAGAR"));assert(strstr(rendered,"REINICIAR"));
    assert(strstr(rendered,"HOME cancela"));assert(strstr(rendered,"CONFIRMAR"));
    fclose(screen);
    screen=tmpfile();assert(screen);page(7);rewind(screen);
    memset(rendered,0,sizeof(rendered));
    assert(fread(rendered,1,sizeof(rendered)-1,screen)>0);
    assert(strstr(rendered,"Accion enviada"));
    assert(!strstr(rendered,"CONFIRMAR"));assert(!strstr(rendered,"HOME cancela"));
    fclose(screen);
#ifdef PANEL_POWER_ACTIONS
    for (expected_action=5;expected_action<=6;expected_action++) {
        fail_exec=0;assert(request_power(expected_action)==0);
        fail_exec=1;assert(request_power(expected_action)==-EIO);
    }
#endif
    puts("POWER_UI_SELF_CHECK_OK");
}
'''.replace('CHECKS', checks)
with tempfile.TemporaryDirectory(prefix='tablet-power-') as directory:
    root = Path(directory)
    for active in (False, True):
        path = root / 'power-test.c'
        path.write_text(headers + (mock if active else '') + code + main)
        binary = root / 'power-test'
        command = ['cc', '-std=c11', '-Wall', '-Wextra', '-Werror', '-DPANEL_SD_BOOT']
        if active:
            command += ['-DPANEL_POWER_ACTIONS']
        subprocess.run(command + [str(path), '-o', str(binary)], check=True)
        subprocess.run([str(binary)], check=True)
print('Preview and mocked init requests passed; no USB or power commands executed.')
