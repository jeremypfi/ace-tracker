---
name: pre-commit
description: Quality checklist before committing code to ace-tracker
disable-model-invocation: false
---

# Pre-Commit Quality Checklist

## 1. Run Verification

```bash
python3 verify_pr.py
```

Runs the unit tests, a syntax check, and a full tracker run in one pass —
prints `OK: ...` on success, or the full diagnostic output for whichever
check failed. All unit tests must pass; the tracker run must generate
every page in `data/` (`ACE_Dashboard.html`, `history.html`, `records.html`,
`what-is-ace.html`) with no errors or NaN values. Use `python3 verify_pr.py --fast` to skip the live tracker run
during quick iteration.

## 2. Security Check

```bash
git status
git diff
```

Verify: no API keys, credentials, personal file paths, or `.env` files staged.

## 3. Commit Message

```
Brief summary (50 chars or less)

Detailed explanation if needed:
- What changed and why
- Breaking changes or migration notes
```

The attribution trailer is added per session; don't hardcode one here.

Good: "Fix duration calculation for subtropical storms"
Bad: "Fixed bug", "Updates"
