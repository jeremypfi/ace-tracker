---
name: pre-commit
description: Quality checklist before committing code to ace-tracker
disable-model-invocation: false
---

# Pre-Commit Quality Checklist

## 1. Run All Tests

```bash
python3 test_ace_tracker.py
```

All 59 tests must pass. If any fail: fix before committing.

## 2. Run the Full Tracker

```bash
python3 ace_tracker.py
```

Verify:
- Both Excel files generate: `data/ACE_Tracker_Atlantic.xlsx`, `data/ACE_Tracker_Pacific.xlsx`
- HTML dashboard generates: `data/ACE_Dashboard.html`
- Console output shows valid data — no zeros or NaN values

## 3. Security Check

```bash
git status
git diff
```

Verify: no API keys, credentials, personal file paths, or `.env` files staged.

## 4. Commit Message

```
Brief summary (50 chars or less)

Detailed explanation if needed:
- What changed and why
- Breaking changes or migration notes

Co-Authored-By: Claude Sonnet 4.6 (1M context) <noreply@anthropic.com>
```

Good: "Fix duration calculation for subtropical storms"
Bad: "Fixed bug", "Updates"
