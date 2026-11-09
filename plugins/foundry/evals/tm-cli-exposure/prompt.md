---
description: 'threat-model: expects answer-key issues 1, 3'
tags: [threat-model]
max_turns: 40
timeout_seconds: 900
allowed_tools: [Read, Glob, Grep, Skill, Agent, TodoWrite]
append_system_prompt: 'There is no user to answer questions: make reasonable assumptions and state them.'
---

We're about to let other teams run this tool's search and delete commands. Assess the security risks first: write a STRIDE threat model to docs/security/threat-model-cli.md.
