---
name: terminal-conversation
description: Use for OpenClaw conversations through the HardwareOne G2 glasses Terminal when presenting structured choice cards or continuing a task or conversation after the wearer answers.
---

Preserve the purpose of the current request. Use a choice card when the user explicitly requests one or when the current tool instructions call for a decision that belongs to the user. Ordinary conversation does not need to become a sequence of structured questions.

Before calling deferred `ask_user`, inspect its full schema through the available tool discovery/describe mechanism unless that schema is already available in context. Follow the loaded schema; do not infer argument fields from the tool name or a shortened validation error.

The currently supported shape is:

- A `questions` array containing 1–3 questions. Prefer one question per call; combine questions only when their answers need to be submitted together.
- Each question has a unique lowercase snake_case `id`, a short `header`, a single-sentence `question`, and 2–4 `options`.
- Each option contains `label` and, optionally, `description`. Do not add `value`.
- Use `multiSelect` only when several choices may be selected.
- Do not add “Other”; free-text input is supplied automatically.
- Keep selectable choices in `options`. When recommending an option, put it first and mark its label as the tool instructions specify.

If validation fails, inspect the full schema if necessary and correct all incompatible fields and limits before retrying.

After an answer, use the returned selection or text as input to the existing task or conversation. The Terminal already displays accepted answers, so merely repeating the selection usually adds nothing.

Continue authorized work using the answer. In an ongoing conversation, respond substantively to what it means in context; ask a relevant follow-up only when useful. Do not force an interview, invent a purpose for the answer, or ask whether to proceed with work already requested.

If the request was only to demonstrate or test a choice card, brief confirmation can complete it. Treat cancellation or `no_answer` according to the tool result and current context; do not invent a selection.
