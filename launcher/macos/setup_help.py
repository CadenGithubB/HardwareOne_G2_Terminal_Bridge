"""Local setup help. A device credential reaches the clipboard only on an explicit click."""
import ipaddress
import json
import os
from pathlib import Path
import stat
import subprocess
import sys

ROOT = Path.home() / 'Library/Application Support/HardwareOne Launcher'
CONFIG = Path.home() / '.openclaw/hardwareone-relay/config.json'


def private_bytes(path):
    fd = os.open(str(path), os.O_RDONLY | os.O_NOFOLLOW)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077 or info.st_size > 32768:
            raise ValueError('Private setup file has unexpected ownership, permissions or size.')
        return os.read(fd, 32769)
    finally:
        os.close(fd)


def settings():
    value = json.loads(private_bytes(CONFIG))
    host = str(ipaddress.IPv4Address(value['bind_host']))
    port = value['bind_port']
    if type(port) is not int or not 1 <= port <= 65535:
        raise ValueError('Invalid relay port.')
    return value, f'https://{host}:{port}/v1'


def main(action):
    if action == 'guide':
        subprocess.run(['/usr/bin/open', str(ROOT / 'Setup Help.html')], check=True)
        return
    config, url = settings()
    if action == 'summary':
        print('HardwareOne Connect controls the HardwareOne relay and Terminal host.\n\nEveryday use: Start both, wake the P4 and glasses, then open Terminal from the glasses side menu. The P4 needs Wi-Fi access to this host.\n\nOnce setup and pairing are complete, normal use needs no key entry.\n\nDevice endpoint: ' + url + '\nModel: openclaw/main\n\nIf setup asks for a key, use the relay device key. Copy device key places it on this Mac’s clipboard for private entry on the P4. It is not your OpenClaw Gateway token or device login password.\n\nAfter a host restart, close and reopen Terminal on the glasses.')
    elif action == 'copy-key':
        token = private_bytes(Path(config['device_token_file'])).strip()
        if not 32 <= len(token) <= 4096 or any(c < 33 or c > 126 for c in token):
            raise ValueError('Device credential has an unexpected format.')
        subprocess.run(['/usr/bin/pbcopy'], input=token, check=True)
        print('Device key copied to this Mac’s clipboard. Paste it only into the P4 relay/device-token setting. The launcher did not show or log it. Copy something else when finished.')
    else:
        raise ValueError('Unknown help action.')


if __name__ == '__main__':
    try:
        main(sys.argv[1])
    except Exception:
        # Configuration parser exceptions can contain secrets. Never echo them.
        print('Setup help could not read the private relay settings or complete the selected action.', file=sys.stderr)
        sys.exit(1)
