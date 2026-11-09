---
name: threat-model
description: "STRIDE threat model of a scope via the security-auditor subagent, written to docs/security/. Use when asked for a threat model or security review of a feature, service or directory."
argument-hint: "[scope: path or feature]"
allowed-tools: Read Grep Glob Edit(docs/security/**)
---

# Threat model

Scope: $ARGUMENTS (if empty, the whole repository).

## 1. Scope it (main thread)
- Resolve the scope to concrete paths with Glob. Name it with a short kebab-case slug
  (e.g. `api`, `payments`, `repo`).
- From CLAUDE.md and the README: what the system does, who its users are, how it's deployed, and
  whether it handles PII, payments, auth or secrets (see "Security notes").
- Draft a first list of **entry points** (CLI commands, HTTP routes, file or env input, outbound
  calls) and **assets** (data, credentials, money, availability) from a quick Grep.

## 2. Delegate to the security auditor
Call the Agent tool with `subagent_type: "foundry:security-auditor"`. It must be that named
specialist, **not a fork**. The prompt is this self-contained brief:

```
Mode: STRIDE mode.
Goal: threat model of <scope>.
Context: <what it does, users, deployment, sensitivity (from CLAUDE.md)>
Scope paths: <list>
Candidate entry points: <list>   Candidate assets: <list>
Constraints: read-only; cite file:line for every finding.
```

If the report isn't back yet, say in one line that the auditor is running. **When the report
arrives, continue with step 3.**

## 3. Write `docs/security/threat-model-<slug>.md`

```
# Threat model: <scope>
Date: <YYYY-MM-DD> · Scope: <paths> · Method: STRIDE (foundry:security-auditor)

## System summary
## Assets
## Entry points
## Trust boundaries
<where untrusted data or identity crosses into trusted code: user → CLI/API, app → DB,
app → external service, ...>

## STRIDE
| Category | Threat | Where (file:line) | Severity | Status |
|---|---|---|---|---|
<one or more rows per category from the tagged findings. For categories listed as
"none found in scope", one row with "none found">

## Findings
<the auditor's findings, verbatim, ordered by severity>

## Mitigations
1. <ordered by risk reduction per effort; each maps to findings>

## Open questions / Not checked
```

Correct the assets, entry points and boundaries using what the report found. Keep the document
under 150 lines.

## 4. Reply
In at most 12 lines: the path, counts per severity, the Critical findings in one line each. For
each Critical, offer `/foundry:plan-feature <fix>` for the user to run.
