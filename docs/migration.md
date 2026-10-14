# Migrate a package-based Terminal host

An older HardwareOne Terminal installation may use
`~/.local/share/hardwareone-even-terminal`, with an `official/` tree and
`node_modules/`. It cannot be updated by the first-party updater. Migration
replaces that runtime while preserving its existing paired identity, credentials
and configuration. There is no automatic migration command.

Use the following sequence deliberately; record the relevant paths privately.
Do not paste credentials into commands, diagnostics or this repository.

1. Wait for the Terminal host to become idle, then stop that host. Keep the
   existing private state and old runtime available until the replacement is
   verified. The relay and OpenClaw Gateway can remain running.
2. From this repository's `terminal/` directory, run `python3 install.py`. It
   creates the new default `~/.local/share/hardwareone-g2-terminal-bridge`.
   Use `--directory NEW` for another unused absolute destination. Do not run
   `start.mjs --init` during migration.
3. Transfer the existing `hardwareone.json`, paired `gateway-identity.pem` and
   `bridge-token.txt` into the new private directory. Preserve the identity and
   token bytes exactly, with private directory/file permissions (`0700`/`0600`).
   If the configuration references custom credential locations, inspect those
   actual files rather than assuming the default filenames contain active keys.
   Do not copy the old `start.mjs`, package files, installed dependencies or
   installation provenance into the new runtime.
4. In the transferred `hardwareone.json`, set `identityFile` and `bridgeTokenFile`
   to the new absolute file paths. Preserve `gatewayTokenFile`, ports, approval
   settings and other configuration. The external Gateway token stays where it is.
5. Update the relay configuration's `terminal_token_file` to the new bridge-token
   path. Preserve the token, `terminal_port`, TLS files and other relay settings.
   A running relay already holds the same token, so this path-only change does
   not require its restart; it ensures its next start uses the new path. If you
   also change a port or token, restart it to load those separate changes.
6. If you use the optional macOS launcher, update its installed `control.py`
   `SPECS` to the new Terminal `start.mjs` path. Preserve local executable paths
   and unique controller changes. Check the [launcher instructions](../launcher/macos/README.md).
7. Run the new host's check, then start it:

   ```sh
   node "$HOME/.local/share/hardwareone-g2-terminal-bridge/start.mjs" --check
   node "$HOME/.local/share/hardwareone-g2-terminal-bridge/start.mjs"
   ```

   Substitute the chosen destination if different. The paired Gateway device ID
   must remain the same; an unexpected pairing request means the identity needs
   checking, not automatic approval. Verify authenticated Terminal requests,
   session browsing and the glasses connection through the existing relay. Do
   not run both old and new hosts on the same port.
8. After verification, review an exact inventory of the old runtime and its
   backups. Confirm every referenced configuration, token and key has been
   preserved or deliberately relocated. Remove the obsolete host, its
   `official/` tree, `node_modules/` and old-runtime backups only after that
   review. Keep unrelated files and unique local changes. Avoid a blanket delete
   based only on a directory name.

Migration changes the host implementation and runtime paths. It does not change
OpenClaw models, tool policies or agent settings, activate the packaged skill,
or require fresh device credentials. Reopen Terminal on the glasses after the
new host starts; the new server instance invalidates old views.
