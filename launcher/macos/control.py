#!/usr/bin/python3
"""On-demand HardwareOne service control. No login item or restart policy."""
import fcntl
import json
import os
from pathlib import Path
import shlex
import signal
import subprocess
import sys
import time

HOME_DIR = Path.home()
ROOT = HOME_DIR / 'Library/Application Support/HardwareOne Launcher'
SPECS = {
    'Terminal host': ['/usr/local/bin/node', str(HOME_DIR / '.local/share/hardwareone-g2-terminal-bridge/start.mjs')],
    'Relay': ['/usr/bin/python3', str(HOME_DIR / '.openclaw/hardwareone-relay/relay.py'), '--config', str(HOME_DIR / '.openclaw/hardwareone-relay/config.json')],
}


def matching(command, argv):
    try:
        words = shlex.split(command)
    except ValueError:
        return False
    if len(words) != len(argv) or words[1:] != argv[1:]:
        return False
    allowed = {'node'} if Path(argv[0]).name == 'node' else {'python3', 'Python', 'python3.9'}
    return Path(words[0]).name in allowed


def inventory():
    raw = subprocess.check_output(['/bin/ps', '-axo', 'pid=,uid=,command='], text=True)
    rows = []
    for line in raw.splitlines():
        fields = line.split(None, 2)
        if len(fields) == 3 and fields[0].isdigit() and fields[1].isdigit() and int(fields[1]) == os.getuid():
            rows.append((int(fields[0]), fields[2]))
    return rows


def matches(argv):
    return [(pid, command) for pid, command in inventory() if matching(command, argv)]


def listening(pid):
    r = subprocess.run(['/usr/sbin/lsof', '-nP', '-a', '-p', str(pid), '-iTCP', '-sTCP:LISTEN'], capture_output=True, text=True)
    return r.returncode == 0 and 'LISTEN' in r.stdout


def start_one(name, argv):
    found = matches(argv)
    if len(found) > 1:
        raise RuntimeError(name + ': multiple instances found; no additional process started.')
    if found:
        if not listening(found[0][0]):
            raise RuntimeError(name + ': existing process has no confirmed listener; no duplicate started.')
        return name + ': already running.'
    if not Path(argv[0]).is_file() or not Path(argv[1]).is_file():
        raise RuntimeError(name + ': installed executable or service script is missing.')
    log = ROOT / ('terminal.log' if name == 'Terminal host' else 'relay.log')
    if log.exists() and log.stat().st_size > 5 * 1024 * 1024:
        log.replace(log.with_suffix('.previous.log'))
    env = dict(os.environ, PATH='/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin')
    if name == 'Relay':
        env['PYTHONUNBUFFERED'] = '1'
    with log.open('ab') as output:
        process = subprocess.Popen(argv, cwd=str(Path(argv[1]).parent), env=env, stdin=subprocess.DEVNULL,
                                   stdout=output, stderr=subprocess.STDOUT, start_new_session=True, close_fds=True)
    # A failed or uncertain start is never automatically resent.
    for _ in range(80):
        if process.poll() is not None:
            raise RuntimeError(name + ': startup exited; see ' + str(log))
        if listening(process.pid):
            return name + ': started.'
        time.sleep(.1)
    raise RuntimeError(name + ': startup not confirmed; inspect ' + str(log) + ' before retrying.')


def stop_one(name, argv):
    found = matches(argv)
    if not found:
        return name + ': already stopped.'
    if len(found) != 1:
        raise RuntimeError(name + ': multiple instances found; no process stopped.')
    pid, command = found[0]
    # Recheck exact user and arguments immediately before signalling only this PID.
    if (pid, command) not in inventory():
        return name + ': process changed; no signal sent.'
    os.kill(pid, signal.SIGINT)
    for _ in range(80):
        if (pid, command) not in inventory():
            return name + ': stopped.'
        time.sleep(.1)
    raise RuntimeError(name + ': stop not confirmed; no force-kill was used.')


def main(action):
    if action not in ('start', 'stop', 'status'):
        raise ValueError('Use start, stop or status.')
    os.umask(0o077)
    ROOT.mkdir(parents=True, exist_ok=True)
    with (ROOT / 'control.lock').open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError('A launcher operation is already in progress. Wait before trying again.')
        messages = []
        for name, argv in SPECS.items():
            if action == 'status':
                found = matches(argv)
                label = 'stopped' if not found else 'running' if len(found) == 1 and listening(found[0][0]) else 'needs inspection'
                messages.append(name + ': ' + label)
            else:
                messages.append((start_one if action == 'start' else stop_one)(name, argv))
        print('\n'.join(messages))
        if action == 'start':
            print('They stay on until you choose Stop both or quit their processes. Nothing starts at login.')


if __name__ == '__main__':
    try:
        main(sys.argv[1] if len(sys.argv) == 2 else 'status')
    except (OSError, RuntimeError, ValueError, subprocess.SubprocessError) as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
