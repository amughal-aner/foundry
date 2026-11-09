---
description: 'review-diff: expects answer-key issues 4'
tags: [review-diff, needs-bash]
max_turns: 40
timeout_seconds: 900
allowed_tools: [Read, Glob, Grep, Skill, Agent, TodoWrite]
append_system_prompt: 'There is no user to answer questions: make reasonable assumptions and state them.'
---

Review my uncommitted changes before I commit them.
