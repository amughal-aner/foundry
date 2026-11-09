---
description: 'threat-model: expects answer-key issues 1, 2, 3'
tags: [threat-model]
max_turns: 40
timeout_seconds: 900
allowed_tools: [Read, Glob, Grep, Skill, Agent, TodoWrite]
append_system_prompt: 'There is no user to answer questions: make reasonable assumptions and state them.'
---

Do a threat model of this repository and write it to docs/security/threat-model-repo.md.
