"""Certificate renewal tests; disposable relay directories and loopback TLS only."""

from contextlib import redirect_stderr, redirect_stdout
import hashlib
import importlib.util
import io
import os
from pathlib import Path
import shutil
import socket
import ssl
import stat
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest import mock


RELAY_DIR = Path(__file__).resolve().parents[1] / "relay"
SETUP = RELAY_DIR / "setup_relay.py"
RENEW = RELAY_DIR / "renew_cert.py"
SPEC = importlib.util.spec_from_file_location("hardwareone_relay_renew", RENEW)
renew_cert = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = renew_cert
sys.path.insert(0, str(RELAY_DIR))
try:
    SPEC.loader.exec_module(renew_cert)
finally:
    sys.path.pop(0)

# Clearly fake fixture credential, never a real OpenClaw gateway token.
GATEWAY_TOKEN = "renew-test-only-gateway-" + "g" * 40
UNCHANGED = ("config.json", "ca-cert.pem", "ca-key.pem", "device-token.txt", "gateway-token.txt")


def digests(root, names):
    return {name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in names}


def handshake(runtime, hostname):
    """Return whether a client trusting only the relay CA accepts hostname."""
    server_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    server_context.load_cert_chain(str(runtime / "relay-cert.pem"), str(runtime / "relay-key.pem"))
    client_context = ssl.create_default_context(cafile=str(runtime / "ca-cert.pem"))
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        listener.listen(1)
        listener.settimeout(3)

        def serve():
            raw, _address = listener.accept()
            raw.settimeout(2)
            try:
                with server_context.wrap_socket(raw, server_side=True) as secure:
                    secure.sendall(b"ok")
            except (ssl.SSLError, OSError):
                raw.close()

        worker = threading.Thread(target=serve, daemon=True)
        worker.start()
        try:
            with socket.create_connection(listener.getsockname(), timeout=2) as raw:
                with client_context.wrap_socket(raw, server_hostname=hostname) as secure:
                    return secure.recv(8) == b"ok"
        except ssl.SSLCertVerificationError:
            return False
        finally:
            worker.join(timeout=3)


@unittest.skipUnless(shutil.which("openssl"), "openssl is required for generated certificate tests")
class RelayRenewTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix="hw1-relay-renew-test-")
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name).resolve()
        token_file = self.root / "fake-existing-gateway-token"
        token_file.write_text(GATEWAY_TOKEN + "\n")
        token_file.chmod(0o600)
        self.runtime = self.root / "prepared"
        prepared = subprocess.run(
            [sys.executable, str(SETUP), "--bind", "127.0.0.1", "--output", str(self.runtime),
             "--gateway-token-file", str(token_file)],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, timeout=15)
        if prepared.returncode:
            raise AssertionError("Preparation failed: " + prepared.stderr.decode())
        self.config = self.runtime / "config.json"

    def renew(self, *arguments):
        return subprocess.run([sys.executable, str(RENEW), "--config", str(self.config), *arguments],
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, timeout=15)

    def test_hostname_added_while_ca_token_and_configuration_are_kept(self):
        before = digests(self.runtime, UNCHANGED)
        old_cert = (self.runtime / "relay-cert.pem").read_bytes()
        result = self.renew("--name", "Relay.Example.Test")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(digests(self.runtime, UNCHANGED), before)
        self.assertNotEqual((self.runtime / "relay-cert.pem").read_bytes(), old_cert)
        self.assertTrue(handshake(self.runtime, "relay.example.test"))
        self.assertTrue(handshake(self.runtime, "127.0.0.1"))
        self.assertFalse(handshake(self.runtime, "other.example.test"))
        self.assertIn(b"https://relay.example.test:18790/v1", result.stdout)
        check = subprocess.run([sys.executable, str(self.runtime / "relay.py"), "--config",
                                str(self.config), "--check-config"],
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, timeout=5)
        self.assertEqual(check.returncode, 0, check.stderr)

    def test_backups_are_private_and_output_has_no_secrets(self):
        old_cert = (self.runtime / "relay-cert.pem").read_bytes()
        old_key = (self.runtime / "relay-key.pem").read_bytes()
        result = self.renew("--name", "relay.example.test")
        self.assertEqual(result.returncode, 0, result.stderr)
        cert_backups = list(self.runtime.glob("relay-cert.pem.before-renew-*"))
        key_backups = list(self.runtime.glob("relay-key.pem.before-renew-*"))
        self.assertEqual([path.read_bytes() for path in cert_backups], [old_cert])
        self.assertEqual([path.read_bytes() for path in key_backups], [old_key])
        for path in (*cert_backups, *key_backups, self.runtime / "relay-key.pem"):
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
        device = (self.runtime / "device-token.txt").read_bytes().strip()
        output = result.stdout + result.stderr
        for private in (GATEWAY_TOKEN.encode(), device, b"PRIVATE KEY"):
            self.assertNotIn(private, output)
        self.assertEqual(list(self.runtime.glob(".hw1-relay-*")), [])

    def test_existing_names_are_kept_unless_replaced(self):
        self.assertEqual(self.renew("--name", "relay.example.test", "--address", "203.0.113.7").returncode, 0)
        self.assertEqual(self.renew().returncode, 0)
        self.assertTrue(handshake(self.runtime, "relay.example.test"))
        self.assertTrue(handshake(self.runtime, "203.0.113.7"))
        self.assertEqual(self.renew("--replace", "--name", "home.example.test").returncode, 0)
        self.assertTrue(handshake(self.runtime, "home.example.test"))
        self.assertTrue(handshake(self.runtime, "127.0.0.1"))
        self.assertFalse(handshake(self.runtime, "relay.example.test"))
        self.assertFalse(handshake(self.runtime, "203.0.113.7"))

    def test_check_and_invalid_names_change_nothing(self):
        names = ("relay-cert.pem", "relay-key.pem", *UNCHANGED)
        before = digests(self.runtime, names)
        result = self.renew("--check", "--name", "relay.example.test")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(b"127.0.0.1, relay.example.test", result.stdout)
        for arguments in (("--name", "192.0.2.10"), ("--name", "-bad.example.test"),
                          ("--name", "a..example.test"), ("--name", "under_score.example.test"),
                          ("--name", "x" * 64 + ".example.test"), ("--address", "0.0.0.0"),
                          ("--address", "relay.example.test")):
            with self.subTest(arguments=arguments):
                self.assertNotEqual(self.renew(*arguments).returncode, 0)
        self.assertEqual(digests(self.runtime, names), before)
        self.assertEqual(sorted(path.name for path in self.runtime.iterdir()),
                         sorted([*names, "relay.py", "launchagent.plist"]))

    def test_failed_issue_keeps_previous_certificate_and_cleans_staging(self):
        names = ("relay-cert.pem", "relay-key.pem", *UNCHANGED)
        before = digests(self.runtime, names)
        argv = ["--config", str(self.config), "--name", "relay.example.test"]
        with mock.patch.object(renew_cert, "openssl", side_effect=ValueError("fixture failure")):
            with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                with self.assertRaises(ValueError):
                    renew_cert.main(argv)
        self.assertEqual(digests(self.runtime, names), before)
        self.assertEqual(list(self.runtime.glob(".hw1-relay-*")), [])

    def test_failed_publish_restores_previous_certificate_and_key(self):
        names = ("relay-cert.pem", "relay-key.pem")
        before = digests(self.runtime, names)
        argv = ["--config", str(self.config), "--name", "relay.example.test"]
        with mock.patch.object(renew_cert, "load_config", side_effect=[renew_cert.load_config(self.config),
                                                                       renew_cert.ConfigError("fixture")]):
            with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                with self.assertRaises(renew_cert.ConfigError):
                    renew_cert.main(argv)
        self.assertEqual(digests(self.runtime, names), before)
        self.assertTrue(handshake(self.runtime, "127.0.0.1"))
        self.assertFalse(handshake(self.runtime, "relay.example.test"))


if __name__ == "__main__":
    unittest.main()
