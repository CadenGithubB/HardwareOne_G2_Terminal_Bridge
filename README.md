# HardwareOne G2 Terminal Bridge

A HardwareOne project that connects G2 glasses, through compatible HardwareOne
firmware, to an OpenClaw agent. It brings the HTTPS relay, first-party Terminal
server, conversation skill and optional macOS launcher into one repository.

This is an independent project, not an Even Realities product. Its Terminal
server uses Node.js built-ins and does not depend on the Even Terminal package.

```text
G2 glasses ↔ HardwareOne device ↔ HTTPS relay ↔ Terminal host ↔ local OpenClaw
                                  └────────────→ legacy HTTP chat
```

| Component | Purpose |
| --- | --- |
| [relay/](relay/README.md) | Authenticated HTTPS access to bounded Terminal operations and the existing HTTP chat path. |
| [terminal/](terminal/README.md) | Session browsing, live responses, tool status, question cards, accepted-answer display and run controls. |
| [skills/terminal-conversation/](skills/terminal-conversation/SKILL.md) | Agent guidance for correctly formed questions and useful conversation after an answer. |
| [launcher/macos/](launcher/macos/README.md) | Optional start/stop app and local setup help. |

The host suppresses raw question-tool JSON, displays accepted answers and
replays recent answer receipts within bounded view capacity. OpenClaw remains
the owner of conversation history, tools, permissions and execution.

## Requirements and setup

Use Python 3.9+, OpenSSL and Node.js 22+. The supported Gateway is
**OpenClaw 2026.9.4**, protocol 4; the adapter checks that version rather than
guessing a different API. This pin describes compatibility, not the latest release.
Terminal installation and updates copy first-party source offline, with no npm
dependencies or package downloads. npm is only a convenience for the test scripts.

For a new installation:

1. Prepare the [relay](relay/README.md) with your host address and private
   credentials. Documentation addresses such as `192.0.2.10` are examples.
2. Install, initialize and pair the [Terminal host](terminal/README.md), then
   connect it to the existing relay using the supplied helper.
3. Run the host and relay in the foreground, or configure the optional
   [macOS launcher](launcher/macos/README.md).
4. Use compatible [HardwareOne firmware](https://github.com/CadenGithubB/HardwareOne)
   to open Terminal on the glasses. Firmware and device setup remain in that
   separate repository.

The Terminal host defaults to `~/.local/share/hardwareone-g2-terminal-bridge`;
the relay uses `~/.openclaw/hardwareone-relay`. Existing first-party installations
use the [update procedure](terminal/README.md#update-an-existing-first-party-host).
An older package-based host requires [explicit migration](docs/migration.md)
to preserve its paired identity, tokens and configuration. Do not initialize a
replacement identity over an existing setup.

The conversation skill is packaged source. Cloning, installing or updating this
bridge does not activate it in an agent. See the optional
[skill installation instructions](docs/conversation-skill.md) when you choose
to use it.

## Development

No npm dependency installation is needed:

```sh
npm test
```

The tests use synthetic credentials, temporary files, loopback fake servers and
mocked launcher actions. They do not send questions or prompts to a real agent.
Live device behavior and model compliance with the skill require separate
verification. See [CONTRIBUTING.md](CONTRIBUTING.md).

Only source, generic examples and synthetic tests belong here. Keep credentials,
private keys, deployment configuration, transcripts and diagnostics out of Git.

## Origin and license

The relay and protocol adapter originate in the HardwareOne host integration;
the standalone HTTP server replaces its former package-based host. Historical
extraction provenance is recorded in [docs/ORIGIN.md](docs/ORIGIN.md). Firmware
stays in HardwareOne. Source changes alone do not migrate running services.

Project source retains the [PolyForm Noncommercial 1.0.0 license](LICENSE.md).
See [third-party notices](docs/THIRD_PARTY.md) for external components.
