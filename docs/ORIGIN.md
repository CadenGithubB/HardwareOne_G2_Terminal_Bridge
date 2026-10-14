# Source origin

The initial repository extracts `integrations/openclaw/relay`,
`integrations/openclaw/terminal` and their relay tests from
[HardwareOne](https://github.com/CadenGithubB/HardwareOne), based on commit
`2834dd26b0e14a4d21c123bb66c67685af7669a5` plus the working-tree host fixes.
Those fixes include deferred question-tool JSON suppression, accepted-answer
receipts, recent-answer replay and protection of the initial event window.
The optional launcher comes from existing first-party HardwareOne macOS source.

[source-manifest.json](source-manifest.json) records the original source paths
and SHA-256 digests at extraction, before public-example sanitization and
branding edits. The source license was copied unchanged. This is a new Git
history containing selected source only, not a copy of earlier deployment or
investigation history.

Public-source preparation replaced deployment-specific examples, agent nicknames
and test paths with generic equivalents. Runtime namespaces, installed service
paths, pairing identities and upstream integrity checks retain compatibility.
The new conversation skill and repository documentation were authored here.

The original HardwareOne files remain in their checkout for continuity; this
repository is the standalone home for subsequent bridge work. Firmware remains
owned by HardwareOne. No runtime migration or deployment was performed as part
of creating this source repository.
