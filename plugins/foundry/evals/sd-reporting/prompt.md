---
description: 'system-design: expects answer-key issues 5a, 5b'
tags: [system-design]
max_turns: 40
timeout_seconds: 900
allowed_tools: [Read, Glob, Grep, Skill, Agent, TodoWrite]
append_system_prompt: 'There is no user to answer questions: make reasonable assumptions and state them.'
---

The reporting code in this repo has become hard to change. Analyze the design and write an architecture decision record at docs/adr/0001-reporting-structure.md recommending how to restructure it.
