# Source origin

The initial repository extracted `integrations/openclaw/relay`,
`integrations/openclaw/terminal` and their relay tests from
[HardwareOne](https://github.com/CadenGithubB/HardwareOne), based on commit
`2834dd26b0e14a4d21c123bb66c67685af7669a5` plus working-tree host fixes.
Those fixes include deferred question-tool JSON suppression, accepted-answer
receipts, recent-answer replay and protection of the initial event window.
The optional launcher comes from first-party HardwareOne macOS source.

[source-manifest.json](source-manifest.json) is a historical extraction record:
its source paths and SHA-256 digests describe the files before public-example
sanitization, branding edits and replacement of the package-based Terminal host.
It is not a manifest of the current runtime or an instruction to restore the old
installer. Current installations record the hashes of their first-party runtime
files separately.

The standalone server and offline installer/updater replace the previous host's
Even Terminal package dependency. The runtime now has five first-party modules:
`start.mjs`, `server.mjs`, `gateway.mjs`, `provider.mjs` and `device-api.mjs`.
The bounded device API and pinned OpenClaw contract preserve protocol continuity;
existing private state requires the documented [migration](migration.md).

Public examples use generic names and synthetic data. The conversation skill
and repository documentation were authored here. The source license was copied
unchanged. This repository has its own Git history containing selected source,
not private deployment or investigation history.

HardwareOne remains the firmware owner. This repository is the standalone home
for subsequent host bridge work. Changing or checking out source does not itself
migrate or deploy a running service.
