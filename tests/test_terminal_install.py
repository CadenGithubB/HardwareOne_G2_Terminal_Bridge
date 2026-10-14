"""Offline first-party installer checks; never start an installed runtime."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

TERMINAL = Path(__file__).resolve().parents[1] / 'terminal'
sys.path.insert(0, str(TERMINAL))
spec = importlib.util.spec_from_file_location('hw1_install', TERMINAL / 'install.py')
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)
FILES = ('start.mjs', 'server.mjs', 'gateway.mjs', 'provider.mjs', 'device-api.mjs')


class InstallTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.source = self.root / 'source'
        self.source.mkdir()
        self.target = self.root / 'private' / 'host'
        for name in FILES:
            (self.source / name).write_text('export const fixture = ' + repr(name) + ';\n')

    def install(self):
        with patch('shutil.which', return_value='/fixture/node'), patch('subprocess.run', return_value=subprocess.CompletedProcess([], 0, 'v22.18.0\n', '')) as run:
            installer.install(self.target, self.source)
            self.assertEqual(run.call_count, 1)
            self.assertEqual(run.call_args.args[0], ['/fixture/node', '--version'])

    def test_offline_flat_install_records_every_source_and_creates_no_configuration(self):
        self.install()
        self.assertEqual({p.name for p in self.target.iterdir()}, set(FILES) | {'provenance.json'})
        self.assertEqual(self.target.stat().st_mode & 0o777, 0o700)
        provenance = json.loads((self.target / 'provenance.json').read_text())
        self.assertEqual(provenance['schema'], 1)
        self.assertEqual(provenance['runtime'], 'hardwareone-g2-terminal-bridge')
        self.assertEqual(set(provenance['filesSha256']), set(FILES))
        import hashlib
        for name in FILES:
            self.assertEqual((self.target / name).read_bytes(), (self.source / name).read_bytes())
            self.assertEqual(provenance['filesSha256'][name], hashlib.sha256((self.source / name).read_bytes()).hexdigest())
            self.assertEqual((self.target / name).stat().st_mode & 0o777, 0o600)

    def test_every_new_parent_is_private_even_with_permissive_process_umask(self):
        import os
        self.target = self.root / 'first' / 'second' / 'host'
        previous = os.umask(0)
        try:
            self.install()
        finally:
            os.umask(previous)
        for path in (self.root / 'first', self.target.parent, self.target):
            self.assertEqual(path.stat().st_mode & 0o777, 0o700)

    def test_existing_directory_is_never_overwritten(self):
        self.target.mkdir(parents=True)
        sentinel = self.target / 'keep'
        sentinel.write_text('unique local data')
        with self.assertRaises(ValueError):
            self.install()
        self.assertEqual(sentinel.read_text(), 'unique local data')

    def test_source_symlink_and_missing_file_fail_before_parent_creation(self):
        saved = self.source / FILES[-1]
        saved.unlink()
        with self.assertRaises((ValueError, OSError)):
            self.install()
        self.assertFalse(self.target.parent.exists())
        saved.symlink_to(self.source / FILES[0])
        with self.assertRaises((ValueError, OSError)):
            self.install()
        self.assertFalse(self.target.parent.exists())

    def test_symlinked_destination_parent_is_rejected(self):
        other = self.root / 'elsewhere'
        other.mkdir()
        self.target.parent.symlink_to(other, target_is_directory=True)
        with self.assertRaises(ValueError):
            self.install()
        self.assertEqual(list(other.iterdir()), [])

    def test_special_source_file_is_rejected_without_blocking(self):
        import os
        source = self.source / FILES[0]
        source.unlink()
        os.mkfifo(source)
        with self.assertRaises(ValueError):
            self.install()
        self.assertFalse(self.target.parent.exists())

    def test_oversized_and_non_source_inputs_leave_no_install(self):
        for value in (b'', b'x' * (256 * 1024 + 1), b'bad\x00source', b'\xff'):
            with self.subTest(length=len(value)):
                (self.source / FILES[0]).write_bytes(value)
                with self.assertRaises(ValueError):
                    self.install()
                self.assertFalse(self.target.parent.exists())

    def test_old_missing_or_unverifiable_node_leaves_no_install(self):
        for version in ('v20.19.0\n', 'not a version\n'):
            with self.subTest(version=version), patch('shutil.which', return_value='/fixture/node'), patch('subprocess.run', return_value=subprocess.CompletedProcess([], 0, version, '')):
                with self.assertRaises(ValueError):
                    installer.install(self.target, self.source)
                self.assertFalse(self.target.parent.exists())
        with patch('shutil.which', return_value=None):
            with self.assertRaises(ValueError):
                installer.install(self.target, self.source)

    def test_explicit_node_executable_is_resolved_without_runtime_import(self):
        with patch('shutil.which', return_value='/fixture/custom-node') as which, patch('subprocess.run', return_value=subprocess.CompletedProcess([], 0, 'v24.1.0\n', '')) as run:
            installer.install(self.target, self.source, node='custom-node')
        which.assert_called_once_with('custom-node')
        self.assertEqual(run.call_args.args[0], ['/fixture/custom-node', '--version'])


if __name__ == '__main__':
    unittest.main()
