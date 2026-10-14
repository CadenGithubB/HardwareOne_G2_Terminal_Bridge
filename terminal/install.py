#!/usr/bin/env python3
"""Install the offline first-party Terminal runtime without starting or pairing it."""
import argparse
import os
from pathlib import Path
import tempfile

import runtime_files as runtime


def install(target, source, node=None):
    target = runtime.checked_path(target)
    if target.exists():
        raise ValueError('Install directory already exists; choose a new directory and preserve the existing installation')
    contents = runtime.source_files(source)
    runtime.node_executable(node)  # Version only: never import or execute runtime modules.
    contents['provenance.json'] = runtime.provenance_bytes(contents)
    # All source, destination and executable checks precede filesystem changes.
    runtime.make_private_parents(target.parent)
    with tempfile.TemporaryDirectory(prefix='.' + target.name + '-install-', dir=target.parent) as temporary:
        staged = Path(temporary) / 'runtime'
        staged.mkdir(mode=0o700)
        for name, data in contents.items():
            runtime.write_private(staged / name, data)
        runtime.checked_path(target)
        target.mkdir(mode=0o700)  # Reserve an unused destination without overwriting it.
        try:
            os.replace(staged, target)
        except BaseException:
            target.rmdir()  # Our empty reservation only; never recursive cleanup.
            raise
    return target


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', type=Path, default=runtime.DEFAULT_DIRECTORY)
    parser.add_argument('--node', help='Node.js 22+ executable; defaults to node on PATH')
    args = parser.parse_args()
    os.umask(0o077)
    try:
        target = install(args.directory, Path(__file__).parent, args.node)
    except (OSError, ValueError) as error:
        parser.exit(1, 'Host installation failed: ' + str(error) + '\n')
    print('Installed first-party HardwareOne Terminal runtime in ' + str(target) + '.')
    print('No packages were downloaded and no service was started. Run node start.mjs --init from that directory for first-time configuration.')


if __name__ == '__main__':
    main()
