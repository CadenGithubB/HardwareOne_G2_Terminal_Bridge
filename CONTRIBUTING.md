# Contributing

Keep each decision with its owner: `relay/` owns authenticated HTTPS transport;
`terminal/` owns the first-party HTTP server, OpenClaw protocol adapter and
bounded device presentation; `skills/` owns agent guidance; `launcher/macos/`
owns optional local process controls. Firmware remains in HardwareOne.

The Terminal runtime consists of `start.mjs`, `server.mjs`, `gateway.mjs`,
`provider.mjs` and `device-api.mjs`. Keep its installation and updates offline
and free of npm dependencies. Preserve the bounded `/api/hardwareone` contract
and the pinned OpenClaw Gateway contract; do not add a general Gateway proxy.
OpenClaw owns history, permissions and tools.

Preserve pairing, credentials, configuration and protocol identities. Changing
an existing runtime location requires an explicit migration that retains private
state and updates its references. Verify installed module hashes before updates;
do not overwrite unrecognized local changes or run fresh initialization as an
update. Keep legacy host removal separate from first-party source updates.

Run `npm test` after runtime or extraction changes. It uses Python standard
library tests, OpenSSL and Node built-ins; no dependency install or live service
is required. For a narrower change, use the relevant script in package.json.
Skill validation does not establish that a live model will follow the guidance;
record model behavior separately when actually tested. Firmware builds are not
required for host-only changes.

Keep generated apps, temporary fixtures, logs, local deployment configuration,
credentials and diagnostic evidence outside Git. Use `.local/` for private work
notes. Copy explicit source files, not installed service directories. Examples
use documentation addresses and synthetic credentials. Review `git diff --cached`
and the exact staged file list before publishing.

Own temporary-file cleanup. Retain compact source revisions, patches and useful
verification results privately; remove disposable downloads, builds and fixtures
once verified. Never remove another task's working files or runtime state.
