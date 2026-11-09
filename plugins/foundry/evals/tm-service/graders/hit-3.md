---
type: regex
target: { source: file, path: docs/security/threat-model-service.md }
flags: i
pattern: '(authori[sz]ation|permission|access.?control|can_edit|ownership|owner check).{0,120}delet|delete_project.{0,160}(authori[sz]|permission|check|owner|can_edit)'
---
