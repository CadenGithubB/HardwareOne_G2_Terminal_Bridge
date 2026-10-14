import contextlib
import io
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import setup_help as h

class HelpTests(unittest.TestCase):
    def test_summary_never_reads_device_secret(self):
        with patch.object(h,'settings',return_value=({'device_token_file':'/private/key'},'https://192.0.2.10:18790/v1')), patch.object(h,'private_bytes') as read, contextlib.redirect_stdout(io.StringIO()) as out:
            h.main('summary');read.assert_not_called();self.assertIn('relay device key',out.getvalue())
    def test_copy_goes_only_to_pbcopy_not_stdout(self):
        token=b'a'*40
        with patch.object(h,'settings',return_value=({'device_token_file':'/private/key'},'https://example/v1')), patch.object(h,'private_bytes',return_value=token), patch.object(h.subprocess,'run') as run, contextlib.redirect_stdout(io.StringIO()) as out:
            h.main('copy-key');run.assert_called_once_with(['/usr/bin/pbcopy'],input=token,check=True);self.assertNotIn(token.decode(),out.getvalue())
    def test_private_files_and_symlinks(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'key';p.write_bytes(b'private');p.chmod(0o600);self.assertEqual(h.private_bytes(p),b'private')
            p.chmod(0o644)
            with self.assertRaises(ValueError):h.private_bytes(p)
            p.chmod(0o600);s=Path(d)/'symlink';s.symlink_to(p)
            with self.assertRaises(OSError):h.private_bytes(s)
    def test_unknown_action_never_copies(self):
        with patch.object(h,'settings',return_value=({},'https://example/v1')),patch.object(h.subprocess,'run') as run:
            with self.assertRaises(ValueError):h.main('other')
            run.assert_not_called()
if __name__=='__main__':unittest.main()
