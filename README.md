# HardwareOne G2 Terminal Bridge

A HardwareOne project that connects G2 glasses, through compatible HardwareOne
firmware, to an OpenClaw agent. It brings the HTTPS relay, computer-side Terminal
adapter, conversation skill and optional macOS launcher into one repository.

This is an independent project, not an Even Realities product. It integrates
with the official Even Terminal server and keeps the upstream name where it
identifies that dependency.

```text
G2 glasses ↔ HardwareOne device ↔ HTTPS relay ↔ Terminal host ↔ local OpenClaw
                                  └──────────→ legacy HTTP chat
```

| Component | Purpose |
| --- | --- |
| [relay/](relay/README.md) | Authenticated HTTPS access to bounded Terminal operations and the existing HTTP chat path. |
| [terminal/](terminal/README.md) | Session browsing, live responses, tool status, question cards, accepted-answer display and run controls. |
| [skills/terminal-conversation/](skills/terminal-conversation/SKILL.md) | Agent guidance for correctly formed questions and useful conversation after an answer. |
| [launcher/macos/](launcher/macos/README.md) | Optional start/stop app and local setup help. |

The host extensions include the latest question JSON suppression, accepted
answer receipts and bounded answer replay. The conversation skill is new source
in this repository; copying or cloning the repo does not install it into an
agent or change a running deployment.

## Requirements and setup

Use Python 3.9+, OpenSSL, Node.js 22+ and npm. The currently supported upstream
versions are **Even Terminal 0.10.5** and **OpenClaw 2026.9.4**, protocol 4.
The installer verifies the official package integrity; the adapter checks the
Gateway version. These pins describe supported versions, not the latest releases.

1. Prepare the [relay](relay/README.md) with your host address and private
   credentials. The documentation address `192.0.2.10` is an example; replace it
   with the host's reachable address.
2. Install, initialize and pair the [Terminal host](terminal/README.md), then
   connect it to the existing relay using the supplied helper.
3. Install the [conversation skill](docs/conversation-skill.md) into the agent's
   workspace and add the short routing instruction there.
4. Run the host and relay in the foreground, or use the optional
   [macOS launcher](launcher/macos/README.md).
5. Use compatible [HardwareOne firmware](https://github.com/CadenGithubB/HardwareOne)
   to open Terminal on the glasses. Firmware and device-specific setup remain
   in that separate repository.

Existing installations retain `~/.openclaw/hardwareone-relay` and
`~/.local/share/hardwareone-even-terminal`. These compatibility paths preserve
pairing and private settings; the new repository name does not rename them.
For an installed host update, follow [the update procedure](terminal/README.md#update-an-existing-hardware-one-host).
Do not rerun first-install initialization over an existing installation.

## Development

The source and tests need no npm dependency installation:

```sh
npm test
```

The tests use synthetic credentials, temporary files, loopback fake servers and
mocked launcher actions. They do not send questions or prompts to a real agent.
Live device behavior and model compliance with the skill require separate
verification. See [CONTRIBUTING.md](CONTRIBUTING.md).

Only source, generic examples and synthetic tests belong here. Keep credentials,
private keys, deployment configuration, transcripts and diagnostics out of Git.
The installer downloads the official server into a private runtime directory;
that server and its dependencies are not vendored in this repository.

## Origin and license

Extracted from the HardwareOne host integration, including pending fixes, with
source provenance recorded in [docs/ORIGIN.md](docs/ORIGIN.md). Existing hardware
firmware stays in HardwareOne. The original source checkout and running services
are not changed by this extraction.

Project source retains the [PolyForm Noncommercial 1.0.0 license](LICENSE.md).
See [third-party notices](docs/THIRD_PARTY.md) for upstream dependencies.
