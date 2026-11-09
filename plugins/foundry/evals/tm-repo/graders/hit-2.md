---
type: regex
target: { source: file, path: docs/security/threat-model-repo.md }
flags: i
pattern: 'hard.?coded.{0,40}(key|secret|credential|token)|(secret|credential|api.?key).{0,60}(in (the )?source|committed|in code)'
---
