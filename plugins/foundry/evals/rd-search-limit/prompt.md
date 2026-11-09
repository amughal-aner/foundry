---
description: 'review-diff: expects answer-key issues 1'
tags: [review-diff, needs-bash]
max_turns: 40
timeout_seconds: 900
allowed_tools: [Read, Glob, Grep, Skill, Agent, TodoWrite]
append_system_prompt: 'There is no user to answer questions: make reasonable assumptions and state them.'
---

Code review my working-tree changes, please.
