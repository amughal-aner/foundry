---
description: 'system-design: expects answer-key issues 5a'
tags: [system-design]
max_turns: 40
timeout_seconds: 900
allowed_tools: [Read, Glob, Grep, Skill, Agent, TodoWrite]
append_system_prompt: 'There is no user to answer questions: make reasonable assumptions and state them.'
---

We want to add a second report format and a nightly job that pushes usage to billing. Write an ADR at docs/adr/0001-reporting-extensibility.md on how to structure the code for that.
