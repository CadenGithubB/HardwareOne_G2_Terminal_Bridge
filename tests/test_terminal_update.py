"""Verified first-party updates preserve settings and roll back partial replacement."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

TERMINAL = Path(__file__).resolve().parents[1] / 'terminal'
sys.path.insert(0, str(TERMINAL))
import runtime_files as runtime


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, TERMINAL / filename)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


installer = load('update_fixture_install', 'install.py')
updater = load('hw1_update', 'update.py')


class UpdateTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.source = self.root / 'source'
        self.source.mkdir()
        self.target = self.root / 'host'
        for name in runtime.RUNTIME_FILES:
            (self.source / name).write_text('export const fixture = ' + repr(name) + ';\n')
        self.node = patch.object(runtime, 'node_executable', return_value='/fixture/node')
        self.node.start()
        self.addCleanup(self.node.stop)
        installer.install(self.target, self.source)
        # Deliberately synthetic private state; the updater must never modify it.
        for name in ('hardwareone.json', 'gateway-identity.pem', 'bridge-token.txt', 'gateway-token.txt'):
            (self.target / name).write_text('synthetic private fixture ' + name)
            (self.target / name).chmod(0o600)
        self.original = self.snapshot()
        (self.source / 'gateway.mjs').write_text('export const fixture = "updated Gateway";\n')
        (self.source / 'device-api.mjs').write_text('export const fixture = "updated device API";\n')

    def snapshot(self):
        return {p.name: (p.read_bytes(), p.stat().st_mode & 0o777)
                for p in self.target.iterdir() if p.is_file() and not p.is_symlink()}

    def test_check_validates_without_writes(self):
        self.assertFalse(updater.update(self.target, self.source, check=True))
        self.assertEqual(self.snapshot(), self.original)
        self.assertEqual({p.name for p in self.target.iterdir()}, set(self.original))

    def test_update_backs_up_changed_files_and_preserves_private_state(self):
        self.assertTrue(updater.update(self.target, self.source))
        updated = self.snapshot()
        for name in self.original:
            if name not in ('gateway.mjs', 'device-api.mjs', 'provenance.json'):
                self.assertEqual(updated[name], self.original[name])
        runtime.installed_files(self.target)
        backups = list(self.target.glob('runtime-update-*'))
        self.assertEqual(len(backups), 1)
        self.assertEqual({p.name for p in backups[0].iterdir()}, {'gateway.mjs', 'device-api.mjs', 'provenance.json'})
        for p in backups[0].iterdir():
            self.assertEqual(p.read_bytes(), self.original[p.name][0])
        self.assertFalse((self.target / '.runtime-update.lock').exists())
        self.assertFalse(updater.update(self.target, self.source))
        self.assertEqual(len(list(self.target.glob('runtime-update-*'))), 1)

    def test_local_edit_is_refused_before_backup_or_any_change(self):
        (self.target / 'start.mjs').write_text('unique local start edit')
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError, 'differs from its recorded version'):
            updater.update(self.target, self.source)
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(list(self.target.glob('runtime-update-*')), [])

    def test_partial_replace_failure_restores_code_and_provenance(self):
        replace = os.replace
        def fail_second(source, destination):
            if Path(source).parent.name == 'new' and Path(destination).name == 'device-api.mjs':
                raise OSError('simulated replacement failure')
            return replace(source, destination)
        with patch.object(updater.os, 'replace', side_effect=fail_second):
            with self.assertRaisesRegex(OSError, 'simulated replacement failure'):
                updater.update(self.target, self.source)
        self.assertEqual(self.snapshot(), self.original)
        runtime.installed_files(self.target)
        self.assertEqual(len(list(self.target.glob('runtime-update-*'))), 1)
        self.assertEqual(list(self.target.glob('.runtime-update-*')), [])
        self.assertFalse((self.target / '.runtime-update.lock').exists())

    def test_missing_invalid_or_symlinked_source_is_refused_before_writes(self):
        source = self.source / 'provider.mjs'
        source.unlink()
        with self.assertRaises(OSError):
            updater.update(self.target, self.source)
        source.symlink_to(self.source / 'start.mjs')
        with self.assertRaises(ValueError):
            updater.update(self.target, self.source)
        source.unlink()
        source.write_bytes(b'\x00')
        with self.assertRaises(ValueError):
            updater.update(self.target, self.source)
        self.assertEqual(self.snapshot(), self.original)
        self.assertEqual(list(self.target.glob('runtime-update-*')), [])

    def test_symlinked_installed_code_and_provenance_are_refused(self):
        for name in ('device-api.mjs', 'provenance.json'):
            with self.subTest(name=name):
                file = self.target / name
                external = self.root / (name + '.external')
                external.write_bytes(file.read_bytes())
                file.unlink()
                file.symlink_to(external)
                with self.assertRaises(ValueError):
                    updater.update(self.target, self.source)
                self.assertEqual(external.read_bytes(), self.original[name][0])
                file.unlink()
                file.write_bytes(self.original[name][0])
                file.chmod(0o600)
        self.assertEqual(list(self.target.glob('runtime-update-*')), [])

    def test_symlinked_installation_root_is_refused(self):
        alias = self.root / 'alias'
        alias.symlink_to(self.target, target_is_directory=True)
        with self.assertRaises(ValueError):
            updater.update(alias, self.source)
        self.assertEqual(self.snapshot(), self.original)

    def test_legacy_provenance_requires_explicit_migration(self):
        (self.target / 'provenance.json').write_text(json.dumps({'officialVersion': '0.10.5', 'extensionSha256': {}}))
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError, 'explicit migration'):
            updater.update(self.target, self.source)
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(list(self.target.glob('runtime-update-*')), [])

    def test_wrong_or_incomplete_manifest_is_refused(self):
        original = json.loads(self.original['provenance.json'][0])
        for metadata in ({'schema': 1}, dict(original, schema=True), dict(original, runtime='other'), dict(original, filesSha256={})):
            (self.target / 'provenance.json').write_text(json.dumps(metadata))
            before = self.snapshot()
            with self.assertRaises(ValueError):
                updater.update(self.target, self.source)
            self.assertEqual(self.snapshot(), before)
        self.assertEqual(list(self.target.glob('runtime-update-*')), [])

    def test_existing_operation_lock_is_preserved(self):
        lock = self.target / '.runtime-update.lock'
        lock.write_text('another operation')
        with self.assertRaisesRegex(ValueError, 'update lock exists'):
            updater.update(self.target, self.source)
        self.assertEqual(lock.read_text(), 'another operation')
        self.assertEqual(list(self.target.glob('runtime-update-*')), [])

    def test_nonprivate_target_or_runtime_file_is_refused(self):
        for path in (self.target, self.target / 'start.mjs'):
            original_mode = path.stat().st_mode & 0o777
            path.chmod(0o755 if path.is_dir() else 0o644)
            with self.assertRaisesRegex(ValueError, 'private'):
                updater.update(self.target, self.source)
            path.chmod(original_mode)
        self.assertEqual(self.snapshot(), self.original)
        self.assertEqual(list(self.target.glob('runtime-update-*')), [])


if __name__ == '__main__':
    unittest.main()
