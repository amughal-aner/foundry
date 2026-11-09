---
description: 'threat-model: expects answer-key issues 1, 2, 3'
tags: [threat-model]
max_turns: 40
timeout_seconds: 900
allowed_tools: [Read, Glob, Grep, Skill, Agent, TodoWrite]
append_system_prompt: 'There is no user to answer questions: make reasonable assumptions and state them.'
---

Threat-model the service and storage layers (src/sample_app/api.py and db.py) and save the result to docs/security/threat-model-service.md.
