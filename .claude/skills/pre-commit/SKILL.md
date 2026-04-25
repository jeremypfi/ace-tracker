---
name: pre-commit
description: Quality checklist before committing code to ace-tracker
disable-model-invocation: false
---

# Pre-Commit Quality Checklist

Before committing any code changes to ace-tracker, follow this checklist to ensure quality and prevent breaking changes.

## 1. Run All Tests

```bash
python3 test_ace_tracker.py
```

**Verify:**
- All 25 tests pass
- No test failures or errors
- If tests fail: Fix the code before committing

## 2. Run the Full Tracker

```bash
python3 ace_tracker.py
```

**Verify:**
- Script runs without errors
- Both Excel files generate successfully:
  - `data/ACE_Tracker_Atlantic.xlsx`
  - `data/ACE_Tracker_Pacific.xlsx`
- HTML dashboard generates: `data/ACE_Dashboard.html`
- Console output shows valid data (no zeros or NaN values)

## 3. Security Check

**Verify no sensitive data added:**
- No API keys or tokens
- No passwords or credentials
- No personal file paths
- No `.env` files added to git

Run:
```bash
git status
git diff
```

Review all changes carefully.

## 4. Code Quality

**Check your changes:**
- Functions have docstrings
- Variable names are clear
- No commented-out debug code
- No hardcoded values that should be constants
- Logging messages are informative

## 5. Update Documentation (if needed)

**If you changed functionality, update:**
- README.md (if user-facing changes)
- CLAUDE.md (if architecture changed)
- Comments in code (if complex logic added)

## 6. Commit Message

Write a clear commit message:

**Format:**
```
Brief summary (50 chars or less)

Detailed explanation if needed:
- What changed
- Why it changed
- Any breaking changes or migration notes

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
```

**Good examples:**
- "Fix duration calculation for subtropical storms"
- "Add validation for wind speed data"
- "Update NOAA classification thresholds"

**Bad examples:**
- "Fixed bug" (too vague)
- "Updates" (says nothing)
- "asdf" (unprofessional)

## 7. Final Git Commands

```bash
git add <specific-files>  # Don't use "git add ."
git commit -m "Your message here"
git push origin main
```

## ✅ Checklist Summary

- [ ] All tests pass
- [ ] Tracker runs successfully
- [ ] No secrets or sensitive data
- [ ] Code quality is good
- [ ] Documentation updated (if needed)
- [ ] Clear commit message
- [ ] Pushed to GitHub

**Remember:** If branch protection is enabled, you'll need to create a PR even for your own changes!
