# Third-party components

HardwareOne G2 Terminal Bridge is independent of Even Realities and OpenClaw.
Their names identify compatible products, not project ownership.

The Terminal server is first-party source using Node.js built-ins. Its installer
and updater work offline. They do not download, patch or import the Even Terminal
package, Express, cors, qrcode-terminal or other npm runtime dependencies. This
repository does not vendor APKs, decompiled application code or installed binaries.
An existing package-based installation is removed only through the explicit
[migration procedure](migration.md).

The adapter targets OpenClaw 2026.9.4, commit
`3a9d69db306cd7f081e06254cb89c4bcc14a7107`, protocol 4. OpenClaw runs separately
and owns agent tools, permissions, transcripts and execution.

Node.js, Python and OpenSSL/LibreSSL are external runtime or setup tools. They
and OpenClaw retain their own licenses and notices. This source repository does
not redistribute those components.

The root [LICENSE.md](../LICENSE.md) applies to first-party HardwareOne source;
it does not relicense external software.
