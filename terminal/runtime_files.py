"""Shared file contract for the offline, first-party Terminal runtime."""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess

RUNTIME = 'hardwareone-g2-terminal-bridge'
RUNTIME_FILES = ('start.mjs', 'server.mjs', 'gateway.mjs', 'provider.mjs', 'device-api.mjs')
MAX_SOURCE_BYTES = 256 * 1024
DEFAULT_DIRECTORY = Path.home() / '.local/share' / RUNTIME


def checked_path(value):
    """Do not resolve away links: refuse them in every existing path component."""
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = Path.cwd() / path
    if '..' in path.parts:
        raise ValueError('Parent traversal is not allowed in a runtime path')
    current = Path(path.anchor)
    for part in path.parts[1:]:
        current /= part
        try:
            info = current.lstat()
        except FileNotFoundError:
            break
        if stat.S_ISLNK(info.st_mode):
            raise ValueError('Runtime and source paths must not contain symbolic links')
        if current != path and not stat.S_ISDIR(info.st_mode):
            raise ValueError('A runtime path parent is not a directory')
    return path


def make_private_parents(directory):
    """Create every missing parent privately, without changing existing directories."""
    directory = checked_path(directory)
    missing = []
    current = directory
    while not current.exists():
        missing.append(current)
        current = current.parent
    for path in reversed(missing):
        checked_path(path)
        path.mkdir(mode=0o700)


def read_regular(path, limit=MAX_SOURCE_BYTES, private=False):
    path = checked_path(path)
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or not 0 < info.st_size <= limit:
            raise ValueError('Expected a bounded, nonempty regular file: ' + path.name)
        if private and (info.st_uid != os.getuid() or info.st_mode & 0o077):
            raise ValueError('Installed runtime files must be private and owned by this user')
        with os.fdopen(fd, 'rb', closefd=False) as stream:
            data = stream.read(limit + 1)
        if len(data) != info.st_size:
            raise ValueError('File changed while being read: ' + path.name)
        return data, stat.S_IMODE(info.st_mode)
    finally:
        os.close(fd)


def source_files(directory):
    directory = checked_path(directory)
    if not directory.is_dir():
        raise ValueError('Runtime source directory is missing')
    contents = {}
    for name in RUNTIME_FILES:
        data, unused_mode = read_regular(directory / name)
        try:
            data.decode('utf-8')
        except UnicodeDecodeError:
            raise ValueError('Runtime source is not UTF-8: ' + name) from None
        if b'\0' in data:
            raise ValueError('Runtime source contains a NUL byte: ' + name)
        contents[name] = data
    return contents


def digest(data):
    return hashlib.sha256(data).hexdigest()


def provenance_bytes(contents):
    return (json.dumps({'schema': 1, 'runtime': RUNTIME,
                        'filesSha256': {name: digest(contents[name]) for name in RUNTIME_FILES}},
                       indent=2) + '\n').encode()


def installed_files(directory):
    directory = checked_path(directory)
    info = directory.stat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise ValueError('Installed runtime directory must be private and owned by this user')
    raw, mode = read_regular(directory / 'provenance.json', limit=64 * 1024, private=True)
    try:
        metadata = json.loads(raw)
    except (ValueError, UnicodeDecodeError):
        raise ValueError('Invalid runtime provenance') from None
    if isinstance(metadata, dict) and 'officialVersion' in metadata:
        raise ValueError('Legacy installation requires explicit migration to a new first-party runtime directory; no files changed')
    if (not isinstance(metadata, dict) or set(metadata) != {'schema', 'runtime', 'filesSha256'}
            or type(metadata['schema']) is not int or metadata['schema'] != 1
            or metadata['runtime'] != RUNTIME):
        raise ValueError('Expected first-party HardwareOne runtime provenance')
    hashes = metadata['filesSha256']
    if (not isinstance(hashes, dict) or set(hashes) != set(RUNTIME_FILES)
            or any(not isinstance(value, str) or not re.fullmatch('[a-f0-9]{64}', value) for value in hashes.values())):
        raise ValueError('Invalid first-party runtime file manifest')
    contents = {'provenance.json': (raw, mode)}
    for name in RUNTIME_FILES:
        contents[name] = read_regular(directory / name, private=True)
        if digest(contents[name][0]) != hashes[name]:
            raise ValueError('Installed runtime differs from its recorded version: ' + name)
    return contents


def node_executable(requested=None):
    executable = shutil.which(str(requested) if requested is not None else 'node')
    if not executable:
        raise ValueError('Node.js 22 or newer is required; use --node or put node on PATH')
    try:
        result = subprocess.run([executable, '--version'], capture_output=True, text=True, timeout=10, check=False)
    except (OSError, subprocess.SubprocessError):
        raise ValueError('Unable to verify Node.js version') from None
    match = re.fullmatch(r'v?(\d+)\.\d+\.\d+(?:[-+][A-Za-z0-9.-]+)?', result.stdout.strip())
    if result.returncode or not match or int(match.group(1)) < 22:
        raise ValueError('Node.js 22 or newer is required')
    return executable


def write_private(path, data, mode=0o600):
    with path.open('xb') as stream:
        stream.write(data)
    path.chmod(mode)
