#!/usr/bin/env python3
"""Reissue the installed relay's server certificate from its existing CA; start nothing.

The CA, device token and relay configuration are unchanged, so the device keeps
its llmhttpca and llmhttptoken settings. Names on the current certificate are
kept unless --replace is given.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import os
from pathlib import Path
import secrets
import shutil
import ssl
import subprocess
import sys
import tempfile

from relay import ConfigError, _private_file, load_config
from setup_relay import certificate_names, issue_leaf, openssl


def current_names(path):
    """Return the IPv4 addresses and DNS names on an existing certificate."""
    try:
        decoded = ssl._ssl._test_decode_cert(str(path))
    except AttributeError:
        raise ConfigError("Cannot read the current certificate names; use --replace with every name") from None
    entries = decoded.get("subjectAltName", ())
    return ([value for kind, value in entries if kind == "IP Address"],
            [value for kind, value in entries if kind == "DNS"])


def atomic_write(path, data):
    fd, temporary = tempfile.mkstemp(prefix=".hw1-relay-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as output:
            output.write(data)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path,
                        default=Path.home() / ".openclaw" / "hardwareone-relay" / "config.json")
    parser.add_argument("--name", action="append", default=[],
                        help="Stable DNS name the device may use instead of the IP (repeatable)")
    parser.add_argument("--address", action="append", default=[],
                        help="Additional IPv4 address, such as a fixed public address (repeatable)")
    parser.add_argument("--replace", action="store_true",
                        help="Use only the bind address and the given names, dropping others")
    parser.add_argument("--check", action="store_true", help="Validate without changing any files")
    args = parser.parse_args(argv)
    config_path = args.config.expanduser().absolute()
    if config_path.parent.resolve() != config_path.parent:
        parser.error("Relay directory must not contain symlinks")
    program = shutil.which("openssl")
    if not program:
        parser.error("openssl is required to issue the server certificate")
    config = load_config(config_path)
    cert_path, key_path = Path(config.tls_cert_file), Path(config.tls_key_file)
    ca_cert, ca_key = config_path.with_name("ca-cert.pem"), config_path.with_name("ca-key.pem")
    _private_file(str(ca_key), 16384)
    if not ca_cert.is_file():
        raise ConfigError("The relay CA certificate is missing")
    old_addresses, old_names = ([], []) if args.replace else current_names(cert_path)
    try:
        addresses, names = certificate_names(config.bind_host, [*old_names, *args.name],
                                             [*old_addresses, *args.address])
    except ValueError as error:
        parser.error(str(error))
    covered = ", ".join([*addresses, *names])
    if args.check:
        print("Relay configuration validated. A new certificate would cover: " + covered)
        print("No files changed and no connections made.")
        return 0

    old_cert, old_key = cert_path.read_bytes(), _private_file(str(key_path), 16384)
    previous_mask = os.umask(0o077)
    try:
        with tempfile.TemporaryDirectory(prefix=".hw1-relay-renew-", dir=config_path.parent) as temporary:
            staging = Path(temporary)
            issue_leaf(program, staging, ca_cert, ca_key, addresses, names)
            # Prove the new leaf chains to the CA the device already trusts.
            openssl(program, "verify", "-CAfile", str(ca_cert), str(staging / "relay-cert.pem"))
            suffix = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + secrets.token_hex(3)
            for path, data in ((cert_path, old_cert), (key_path, old_key)):
                backup = path.with_name(path.name + ".before-renew-" + suffix)
                with open(backup, "xb") as output:
                    os.chmod(backup, 0o600)
                    output.write(data)
                print("Backup: " + str(backup))
            os.replace(staging / "relay-key.pem", key_path)
            try:
                os.replace(staging / "relay-cert.pem", cert_path)
                load_config(config_path)
            except BaseException:
                atomic_write(key_path, old_key)
                atomic_write(cert_path, old_cert)
                raise
    finally:
        os.umask(previous_mask)
    print("Reissued the relay certificate for: " + covered + " (expires in 365 days).")
    for host in (*names, *addresses):
        print("Valid device URL: https://%s:%d/v1" % (host, config.bind_port))
    print("CA, device token and relay configuration are unchanged; the device keeps llmhttpca and llmhttptoken.")
    print("Restart the relay to load the new certificate. No service has been started.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (ConfigError, ValueError, OSError, UnicodeError, subprocess.TimeoutExpired):
        print("Certificate renewal failed; the previous certificate remains in place. "
              "Check private-file permissions and the relay configuration.", file=sys.stderr)
        sys.exit(1)
