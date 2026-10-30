#!/usr/bin/env python3
"""Verify a RAM image, then optionally enter fresh FEL from stock Android and boot."""
import argparse
import glob
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SERIAL = 'REPLACE_WITH_YOUR_ADB_SERIAL'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(args, timeout=90):
    p = subprocess.run([str(x) for x in args], cwd=ROOT, capture_output=True, text=True, timeout=timeout)
    if p.returncode:
        raise RuntimeError(f'{args[0]} failed ({p.returncode}): {p.stderr[-2000:]} {p.stdout[-1000:]}')
    return p.stdout


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--image', type=Path, default=ROOT/'analysis/peripherals/revision3/image')
    parser.add_argument('--from-android', action='store_true', help='Execute: backup misc, stock reboot efex (writes BCB), one SPL, verified RAM boot')
    parser.add_argument('--skip-poc', action='store_true', help='For USB-rootfs image: leave the shell for ECM setup')
    args = parser.parse_args()
    image = args.image.resolve()
    manifest = json.loads((image/'manifest.json').read_text())
    for name, digest in manifest['files'].items():
        if Path(name).name != name or sha(image/name) != digest:
            raise RuntimeError(f'Invalid image file or hash: {name}')
    if not args.skip_poc:
        bundle = ROOT/'analysis/poc/bin/poc-bundle.tar.gz'
        poc = json.loads((ROOT/'analysis/poc/manifest.json').read_text())
        for name, digest in poc['files'].items():
            if sha(ROOT/name) != digest:
                raise RuntimeError(f'POC source/runtime changed: {name}')
        # The bundle must match the separately recorded current release hash.
        release = json.loads((ROOT/'analysis/poc/release.json').read_text())
        if sha(bundle) != release['bundle_sha256']:
            raise RuntimeError('POC bundle changed; rebuild release metadata before executing')
    plan = {'image': str(image), 'version': manifest['version'],
            'mode': 'EXECUTE FROM ANDROID' if args.from_android else 'CHECK ONLY; no USB accessed',
            'serial': SERIAL, 'misc_write': 'stock reboot efex writes BCB; backup first',
            'storage_flash': False, 'skip_poc': args.skip_poc}
    print(json.dumps(plan, indent=2), flush=True)
    if not args.from_android:
        return
    # Requiring a working stock Android channel prevents accidentally repeating SPL in existing FEL.
    adb = ['adb', '-s', SERIAL]
    model = run(adb+['shell', 'getprop ro.product.model']).strip()
    identity = run(adb+['shell', 'id']).strip()
    if model != 'EUTB_710MDQ' or not identity.startswith('uid=0('):
        raise RuntimeError(f'Expected stock rooted EUTB_710MDQ; got {model!r}, {identity!r}. No reboot sent.')
    out = Path(tempfile.mkdtemp(prefix='run-', dir=ROOT/'analysis/usb-root'))
    (out/'plan.json').write_text(json.dumps(plan, indent=2)+'\n')
    backup = out/'misc-before-efex.img'
    run(adb+['pull', '/dev/block/by-name/misc', backup])
    if backup.stat().st_size != 16777216:
        raise RuntimeError('Unexpected misc length; reboot withheld')
    (out/'misc-sha256.txt').write_text(sha(backup)+'  misc-before-efex.img\n')
    print(f'Misc backup verified; logs: {out}', flush=True)
    run(adb+['reboot', 'efex'])
    run([sys.executable, ROOT/'tools/build/load-a23-linux-fel.py', image, out], timeout=240)
    ready = json.loads((out/'ready-to-execute.json').read_text())
    if not ready['verified'] or ready['entry'] != '0x41000000':
        raise RuntimeError('No verified RAM entry')
    for name, digest in ready['files'].items():
        if sha(image/name) != digest:
            raise RuntimeError(f'Image changed after RAM verification: {name}')
    with (out/'capture-output.txt').open('w') as log:
        capture = subprocess.Popen([sys.executable, str(ROOT/'tools/build/capture-linux-usb.py'), str(out),
                                    *glob.glob('/dev/cu.usbmodem*')], cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
        try:
            run([ROOT/'.tools/bin/sunxi-fel', '--dev', ready['device'], 'exe', ready['entry']], timeout=20)
            capture.wait(timeout=85)
        finally:
            if capture.poll() is None:
                capture.terminate()
                capture.wait(timeout=5)
    observed = json.loads((out/'serial-result.json').read_text())
    if not observed.get('linux_shell_observed') or not observed.get('diagnostics_complete'):
        raise RuntimeError(f'Linux shell not confirmed; inspect {out}. Do not repeat SPL.')
    if not args.skip_poc:
        port = observed['port']
        run([sys.executable, ROOT/'tools/build/upload-poc-ram.py', port, bundle, out/'upload.txt'], timeout=180)
        commands = ['/bin/busybox test ! -e /poc && /bin/busybox gunzip -c /poc-bundle.tar.gz | /bin/busybox tar -xf - -C /',
                    '/bin/busybox sha256sum /poc/bin/tablet-poc /poc/lib/*']
        query = ROOT/'tools/build/query-linux-usb.py'
        (out/'extract.commands').write_text('\n'.join(commands)+'\n')
        run([sys.executable, query, port, out/'extract.commands', out/'extract.txt'])
        extracted = (out/'extract.txt').read_text()
        for file in (ROOT/'analysis/poc/bin/bundle/poc').rglob('*'):
            if file.is_file():
                remote = '/'+str(file.relative_to(ROOT/'analysis/poc/bin/bundle'))
                if sha(file)+'  '+remote not in extracted:
                    raise RuntimeError(f'RAM file hash mismatch: {remote}')
        (out/'ui.commands').write_text('/poc/lib/ld-linux-armhf.so.3 --library-path /poc/lib /poc/bin/tablet-poc --self-check\n'
            '/bin/busybox setsid /poc/lib/ld-linux-armhf.so.3 --library-path /poc/lib /poc/bin/tablet-poc --ui < /dev/null > /poc-ui.log 2>&1 &\n'
            '/bin/busybox sleep 1; /bin/busybox cat /poc-ui.log\n')
        run([sys.executable, query, port, out/'ui.commands', out/'ui.txt'])
        result = (out/'ui.txt').read_text()
        if 'POC_SELF_CHECK_OK' not in result or 'POC_UI_READY' not in result:
            raise RuntimeError('POC launch not confirmed')
    print(f'RAM Linux ready: {observed["port"]}; evidence {out}', flush=True)


if __name__ == '__main__':
    main()
