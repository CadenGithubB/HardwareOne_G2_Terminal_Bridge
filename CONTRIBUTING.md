# Contributing

Keep each decision with its owner: `relay/` owns authenticated HTTPS transport;
`terminal/` owns the OpenClaw protocol adapter and bounded device presentation;
`skills/` owns agent guidance; `launcher/macos/` owns optional local process
controls. The firmware remains in the separate HardwareOne project.

Preserve pairing, credentials, runtime paths, pinned upstream integrity and
protocol identities unless an explicit migration is part of the change. Do not
replace the Gateway's history, permissions or tools with parallel implementations.

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
