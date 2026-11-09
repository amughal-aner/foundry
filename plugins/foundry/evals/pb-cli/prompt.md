---
description: 'product-brief: expects answer-key issues 6a, 6b'
tags: [product-brief]
max_turns: 40
timeout_seconds: 900
allowed_tools: [Read, Glob, Grep, Skill, Agent, TodoWrite]
append_system_prompt: 'There is no user to answer questions: make reasonable assumptions and state them.'
---

Write a product/UX brief for this tool's command-line interface at docs/product/cli-brief.md.
