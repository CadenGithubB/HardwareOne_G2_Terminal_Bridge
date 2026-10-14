#!/usr/bin/env python3
"""Update verified first-party runtime files; preserve private configuration and identity."""
import argparse
from datetime import datetime, timezone
import os
from pathlib import Path
import tempfile

import runtime_files as runtime


def update(target, source, check=False, node=None):
    target = runtime.checked_path(target)
    installed = runtime.installed_files(target)
    contents = runtime.source_files(source)
    runtime.node_executable(node)
    contents['provenance.json'] = runtime.provenance_bytes(contents)
    changes = {name: (installed[name][0], data, installed[name][1])
               for name, data in contents.items() if data != installed[name][0]}
    if not changes:
        print('HardwareOne runtime files are already current; no files changed.')
        return False
    if check:
        print('Update validated for ' + ', '.join(name for name in changes if name != 'provenance.json') + '; no files changed.')
        return False
    # Exclude concurrent updater processes. Never unlink another operation's lock.
    lock = target / '.runtime-update.lock'
    try:
        descriptor = os.open(lock, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        raise ValueError('An update lock exists; inspect that operation before retrying') from None
    owned_lock = os.fstat(descriptor)
    backup = None
    try:
        # Recheck all installed inputs after acquiring the lock, before backups/writes.
        if runtime.installed_files(target) != installed:
            raise ValueError('Installed runtime changed during update validation; no files changed')
        backup = Path(tempfile.mkdtemp(prefix='runtime-update-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ-'), dir=target))
        for name, (old, unused_new, mode) in changes.items():
            runtime.write_private(backup / name, old, mode)
        with tempfile.TemporaryDirectory(prefix='.runtime-update-', dir=target) as temporary:
            staged = Path(temporary)
            (staged / 'new').mkdir(mode=0o700)
            (staged / 'old').mkdir(mode=0o700)
            for name, (old, new, mode) in changes.items():
                runtime.write_private(staged / 'new' / name, new, mode)
                runtime.write_private(staged / 'old' / name, old, mode)
            replaced = []
            try:
                for name, (old, unused_new, mode) in changes.items():
                    if runtime.read_regular(target / name, private=True) != (old, mode):
                        raise ValueError('Installed runtime changed before replacement: ' + name)
                    os.replace(staged / 'new' / name, target / name)
                    replaced.append(name)
            except BaseException:
                failures = []
                for name in reversed(replaced):
                    try:
                        os.replace(staged / 'old' / name, target / name)
                    except OSError:
                        failures.append(name)
                if failures:
                    raise RuntimeError('Update failed and automatic rollback was incomplete; restore from ' + str(backup)) from None
                raise
    finally:
        os.close(descriptor)
        try:
            info = lock.lstat()
            if (info.st_dev, info.st_ino) == (owned_lock.st_dev, owned_lock.st_ino):
                lock.unlink()
        except FileNotFoundError:
            pass
    print('Updated HardwareOne runtime files. Backup: ' + str(backup))
    print('Private configuration, credentials, identity and relay are unchanged. Restart only the Terminal host using its existing launch method.')
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', type=Path, default=runtime.DEFAULT_DIRECTORY)
    parser.add_argument('--node', help='Node.js 22+ executable; defaults to node on PATH')
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    os.umask(0o077)
    try:
        update(args.directory, Path(__file__).parent, args.check, args.node)
    except (OSError, ValueError, RuntimeError) as error:
        parser.exit(1, 'Host update failed: ' + str(error) + '\n')


if __name__ == '__main__':
    main()
