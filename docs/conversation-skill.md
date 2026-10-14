# Install the Terminal conversation skill

This skill belongs to the OpenClaw agent, not the relay or device firmware.
It teaches the agent to inspect the question tool's full schema and to use an
answer to continue the requested task or conversation. It cannot guarantee a
model will never make an invalid call.

For the supported OpenClaw version, copy the complete
`skills/terminal-conversation/` folder into the relevant agent workspace's
`skills/` directory. Use that agent's configured workspace; do not assume the
repository is its workspace. If a skill with this name already exists, compare
and merge deliberately instead of overwriting it.

Add this routing sentence to that workspace's existing agent instructions:

> For HardwareOne G2 Terminal choice cards and conversation following an answer,
> read `skills/terminal-conversation/SKILL.md` before acting.

Keep this general tool-use reminder in the regular agent guidance:

> Before calling a deferred tool whose exact input schema is not in context,
> inspect its full definition instead of guessing arguments.

These are additions to the existing instructions, not replacements for them.
They do not grant tools, change models or modify approval policy. Ordinary
conversation should not turn into a compulsory sequence of choice cards.

OpenClaw exposes eligible skill names/descriptions for discovery and loads the
body when selected. Its file-backed skills watcher normally refreshes discovery
on the next turn after changes. Check visibility with `openclaw skills check`;
allowlists or a disabled watcher may require the host's normal refresh flow.
Explicitly referencing `$terminal-conversation` is useful for a first check.

Suggested behavior checks after installation:

- A choice-card test uses a valid schema on the first attempt; a short final
  confirmation is sufficient when demonstrating the card was the whole request.
- During an ongoing conversation, a selection leads to a meaningful response or
  useful follow-up, not only another copy of the selected label.
- An answer needed for an already requested task leads into that task.
- Multi-select, free text and cancellation preserve the returned meaning.

The skill was authored and structurally validated in this repository. Live
agent behavior must be checked after installation; repository tests do not
establish model compliance.
