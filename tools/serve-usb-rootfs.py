#!/usr/bin/env python3
"""Serve one verified rootfs only on the Mac's dedicated USB IPv6 link."""
import argparse
import hashlib
import http.client
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
from pathlib import Path
import re
import socket
import subprocess
import threading

ROOT = Path(__file__).resolve().parents[1]


def usb_address(text, interface=None):
    matches = []
    for block in re.split(r'(?=^[a-zA-Z0-9]+: flags=)', text, flags=re.M):
        m = re.match(r'([a-zA-Z0-9]+): flags=', block)
        if not m or (interface and m[1] != interface):
            continue
        if not re.search(r'ether\s+02:71:00:00:00:01\b', block, re.I):
            continue
        addr = re.search(r'inet6\s+(fe80:[0-9a-f:]+)(?:%\w+)?\s', block, re.I)
        if addr:
            matches.append((m[1], addr[1]))
    if len(matches) != 1:
        raise RuntimeError('Expected one USB ECM interface with MAC 02:71:00:00:00:01 and link-local IPv6; no network settings changed')
    return matches[0]


class IPv6Server(HTTPServer):
    address_family = socket.AF_INET6


def handler_for(archive):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path != '/rootfs.tar.gz':
                self.send_error(404)
                return
            with archive.open('rb') as f:
                self.send_response(200)
                self.send_header('Content-Length', str(archive.stat().st_size))
                self.send_header('Content-Type', 'application/gzip')
                self.end_headers()
                while chunk := f.read(65536):
                    self.wfile.write(chunk)

        def log_message(self, fmt, *args):
            pass
    return Handler


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--directory', type=Path, default=ROOT/'analysis/rootfs-usb')
    parser.add_argument('--interface')
    parser.add_argument('--self-test', action='store_true')
    args = parser.parse_args()
    archive = args.directory.resolve()/'rootfs.tar.gz'
    manifest = json.loads((archive.parent/'manifest.json').read_text())
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    if digest != manifest['files']['rootfs.tar.gz']:
        raise RuntimeError('Rootfs hash mismatch')
    if args.self_test:
        sample = 'en9: flags=8863\n\tether 02:71:00:00:00:01\n\tinet6 fe80::1234%en9 prefixlen 64\n'
        assert usb_address(sample) == ('en9', 'fe80::1234')
        try:
            usb_address(sample.replace('02:71:00:00:00:01', '02:00:00:00:00:01'))
        except RuntimeError:
            pass
        else:
            raise AssertionError('Accepted non-USB interface')
        server = IPv6Server(('::1', 0), handler_for(archive))
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            conn = http.client.HTTPConnection('::1', server.server_port, timeout=5)
            conn.request('GET', '/rootfs.tar.gz')
            response = conn.getresponse()
            assert response.status == 200 and hashlib.sha256(response.read()).hexdigest() == digest
            conn.request('GET', '/../../etc/passwd')
            response = conn.getresponse()
            assert response.status == 404
            response.read()
            conn.close()
        finally:
            server.shutdown()
            server.server_close()
            thread.join()
        print('USB_ROOTFS_SERVER_SELF_TEST_OK')
        return
    info = subprocess.run(['/sbin/ifconfig', '-a'], check=True, capture_output=True, text=True).stdout
    interface, address = usb_address(info, args.interface)
    scope = socket.if_nametoindex(interface)
    server = IPv6Server((address, 8080, 0, scope), handler_for(archive))
    plan = {'interface': interface, 'host_ipv6': address, 'port': 8080, 'rootfs_sha256': digest,
            'tablet_command': f'sh /fetch-rootfs {address} {digest}'}
    (archive.parent/'server.json').write_text(json.dumps(plan, indent=2)+'\n')
    print(json.dumps(plan, indent=2), flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
