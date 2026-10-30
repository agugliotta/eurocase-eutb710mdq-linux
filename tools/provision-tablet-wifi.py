#!/usr/bin/env python3
"""Read a WPA2 password locally and place only its derived config in tablet RAM."""
import base64
import fcntl
import getpass
import hashlib
import json
import os
from pathlib import Path
import select
import struct
import sys
import termios
import time
import warnings


def config(ssid, password):
    name, key = ssid.encode('utf-8'), password.encode('utf-8')
    if not 1 <= len(name) <= 32 or not 8 <= len(key) <= 63:
        raise ValueError('Nombre de red o longitud de contraseña inválidos.')
    psk = hashlib.pbkdf2_hmac('sha1', key, name, 4096, 32).hex()
    return ('ctrl_interface=/run/wifi/control\nupdate_config=0\nnetwork={\n'
            f'    ssid={name.hex()}\n    proto=RSN\n    key_mgmt=WPA-PSK\n'
            f'    pairwise=CCMP\n    psk={psk}\n}}\n').encode()


def read_password(ssid):
    with warnings.catch_warnings():
        warnings.simplefilter('error', getpass.GetPassWarning)
        return getpass.getpass(f'Contraseña WPA2 para {ssid}: ')


def main():
    if sys.argv[1:] == ['--self-check']:
        assert b'f42c6fc52df0ebef9ebb4b90b38a5f902e83fe1b135a70e23aed762e9710a12e' in config('IEEE', 'password')
        assert b'ssid=726564220a' in config('red"\n', 'test-only-password')
        for name, password in [('', 'password'), ('x'*33, 'password'), ('red', 'short'), ('red', 'x'*64)]:
            try:
                config(name, password)
            except ValueError:
                pass
            else:
                raise AssertionError('Invalid config accepted')
        from unittest.mock import patch
        def echo_fallback(_):
            warnings.warn('No echo control', getpass.GetPassWarning)
            return 'must-not-be-read'
        with patch.object(getpass, 'getpass', side_effect=echo_fallback):
            try:
                read_password('test')
            except getpass.GetPassWarning:
                pass
            else:
                raise AssertionError('Echoed password input accepted')
        print('WIFI_SECRET_CONFIG_SELF_CHECK_OK; no USB accessed')
        return
    if len(sys.argv) != 4 or not sys.stdin.isatty():
        raise SystemExit('Uso desde Terminal: provision-tablet-wifi.py PUERTO SSID RESULTADO_JSON')
    port, ssid, result_path = sys.argv[1:]
    fd = os.open(port, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
    original = termios.tcgetattr(fd)
    identified = False
    secret_started = False
    received = bytearray()

    def send(data):
        pending = memoryview(data)
        deadline = time.monotonic() + 30
        while pending:
            if time.monotonic() >= deadline:
                raise TimeoutError('USB no responde')
            if select.select([], [fd], [], 0.2)[1]:
                pending = pending[os.write(fd, pending[:4096]):]

    def receive(marker):
        # Never write a serial transcript: it may contain credential material.
        deadline = time.monotonic() + 20
        while marker not in received:
            if time.monotonic() >= deadline:
                raise TimeoutError('Sin confirmación de la tablet')
            if select.select([fd], [], [], 0.2)[0]:
                block = os.read(fd, 65536)
                if not block:
                    raise RuntimeError('USB desconectado')
                received.extend(block)
        return received

    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        attrs = termios.tcgetattr(fd)
        attrs[0] = attrs[1] = attrs[3] = 0
        attrs[2] = termios.CS8 | termios.CREAD | termios.CLOCAL
        attrs[4] = attrs[5] = termios.B115200
        attrs[6][termios.VMIN] = attrs[6][termios.VTIME] = 0
        termios.tcsetattr(fd, termios.TCSANOW, attrs)
        fcntl.ioctl(fd, termios.TIOCMBIS, struct.pack('I', termios.TIOCM_DTR | termios.TIOCM_RTS))
        time.sleep(3)
        send(b'\runame -r; hostname; cat /proc/mounts; dmesg | grep "Eurocase stock calibration applied"; echo WIFI_ID_DONE\r')
        data = receive(b'\r\nWIFI_ID_DONE\r\n')
        required = [b'6.12.0-eutb710mdq-sd4wifi\r\n', b'\r\ntablet\r\n',
                    b'/dev/root / squashfs ro,', b'tmpfs /run tmpfs rw,',
                    b'Eurocase stock calibration applied in RAM']
        if not all(item in data for item in required):
            raise RuntimeError('No es la tablet candidata con calibración confirmada.')
        identified = True
        password = read_password(ssid)
        raw = config(ssid, password)
        del password
        send(b'\rif test ! -e /run/wifi/control/wlan0; then mkdir -p /run/wifi; chmod 700 /run/wifi; if stty -echo; then echo WIFI_SECRET_READY; uudecode; r=$?; stty echo; echo WIFI_SECRET_RC:$r; fi; fi\r')
        receive(b'\r\nWIFI_SECRET_READY\r\n')
        secret_started = True
        send(b'begin-base64 600 /run/wifi/wpa.conf\n' + base64.encodebytes(raw) + b'====\n')
        receive(b'\r\nWIFI_SECRET_RC:0\r\n')
        send(b'\rsha256sum /run/wifi/wpa.conf; echo WIFI_SECRET_HASH_DONE\r')
        data = receive(b'\r\nWIFI_SECRET_HASH_DONE\r\n')
        if (hashlib.sha256(raw).hexdigest() + '  /run/wifi/wpa.conf').encode() not in data:
            raise RuntimeError('La configuración no pasó la verificación.')
        Path(result_path).write_text(json.dumps({'ssid': ssid, 'credentials_in_tablet_ram': True,
                                                'password_logged': False})+'\n')
        print('Clave cargada y verificada únicamente en RAM; no se inició conexión.')
    except BaseException:
        if identified:
            try:
                send(b'\x03\rstty echo\r')
                if secret_started:
                    send(b'rm -f /run/wifi/wpa.conf\r')
            except (OSError, TimeoutError):
                pass
        raise
    finally:
        try:
            termios.tcsetattr(fd, termios.TCSANOW, original)
        finally:
            os.close(fd)


if __name__ == '__main__':
    main()
