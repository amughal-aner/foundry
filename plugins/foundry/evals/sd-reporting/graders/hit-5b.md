---
type: regex
target: { source: file, path: docs/adr/0001-reporting-structure.md }
flags: i
pattern: 'bypass.{0,60}(api|service)|cli.{0,80}(imports?|calls?|uses?|reaches?).{0,40}\bdb\b|direct(ly)?.{0,40}(db|database|storage)'
---
