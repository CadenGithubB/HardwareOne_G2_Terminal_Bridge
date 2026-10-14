# Third-party components

HardwareOne G2 Terminal Bridge is independent of Even Realities and OpenClaw.
Their names identify compatible products and dependencies, not project ownership.

`terminal/install.py` downloads `@evenrealities/even-terminal` version 0.10.5
from the npm registry, verifies its pinned SHA-512 archive integrity and exact
source-file hashes, then applies the HardwareOne extension patches. It retains
the upstream package and records installation provenance. This repository does
not vendor that package, APKs, decompiled application code or installed binaries.
Upstream software remains subject to its own distributed terms and notices.

The retained server uses express 5.2.1, cors 2.8.6 and qrcode-terminal 0.12.0.
The installer records the resolved npm lockfile in the private installation.
Those dependencies are not included in this source repository.

The adapter is verified against OpenClaw 2026.9.4, commit
`3a9d69db306cd7f081e06254cb89c4bcc14a7107`, protocol 4. OpenClaw runs separately
and retains ownership of agent tools, permissions, transcripts and execution.

The root LICENSE.md applies to the first-party HardwareOne project source; it
does not relicense any downloaded third-party packages.
