
**What this does:**
- ✅ Runs tests automatically on every push
- ✅ Tests on Python 3.8, 3.9, 3.10, 3.11
- ✅ Shows green ✓ or red ✗ badge
- ✅ Prevents merging broken code

**Enable:**
After pushing this file, go to:
**Settings** → **Actions** → **General**

```
Actions permissions:
○ Allow all actions and reusable workflows

Workflow permissions:
○ Read and write permissions
✅ Allow GitHub Actions to create and approve pull requests
```

---

## 🏅 **Step 10: Add Status Badges to README**

Add these to top of your README.md:

\`\`\`markdown
![Tests](https://github.com/jeremypfi/ace-tracker/workflows/Tests/badge.svg)
![Python Version](https://img.shields.io/badge/python-3.8+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Last Commit](https://img.shields.io/github/last-commit/jeremypfi/ace-tracker)
![Issues](https://img.shields.io/github/issues/jeremypfi/ace-tracker)
\`\`\`

**Shows:**
- ✅ Test status (passing/failing)
- Python version compatibility
- License type
- Activity level

---

## 📊 **Step 11: Create Issue Templates**

Create `.github/ISSUE_TEMPLATE/bug_report.md`:

\`\`\`markdown
---
name: Bug report
about: Create a report to help us improve
title: '[BUG] '
labels: bug
assignees: ''
---

**Describe the bug**
A clear description of what the bug is.

**To Reproduce**
Steps to reproduce:
1. Run '...'
2. See error

**Expected behavior**
What you expected to happen.

**Environment:**
 - OS: [e.g. macOS, Windows]
 - Python version: [e.g. 3.9]
 - ACE Tracker version: [e.g. v1.0.0]

**Additional context**
Any other relevant information.
\`\`\`

---

## 📜 **Step 12: Add Code Owners (Optional)**

Create `.github/CODEOWNERS`:

\`\`\`
# Code owners for ACE Tracker
# These users will be requested for review when someone opens a PR

* @jeremypfi

# Specific areas
ace_tracker.py @jeremypfi
test_*.py @jeremypfi
*.md @jeremypfi
\`\`\`

**Why:** Automatically requests your review on all PRs.

---

## 🎨 **Step 13: Social Preview Image (Optional)**

**Makes your repo look professional!**

1. Go to **Settings** → **General**
2. Scroll to "Social preview"
3. Upload an image (1200x630 px)
4. Suggestion: Screenshot of your dashboard or a hurricane graphic

**Free tools:**
- Canva (free templates)
- GitHub's auto-generated image
- Take screenshot of ACE_Dashboard.html

---

## ✅ **FINAL CHECKLIST Before Sharing**

### **Required:**
- [ ] Decide: Public or Private + Collaborators?
- [ ] Enable Issues ✓
- [ ] Enable Discussions ✓
- [ ] Add repository description
- [ ] Add topics (hurricane, weather, python)
- [ ] Review SECURITY.md (already added ✓)
- [ ] Review README.md (looks good ✓)
- [ ] Verify no secrets in code (checked ✓)

### **Recommended:**
- [ ] Set up branch protection (main branch)
- [ ] Enable Dependabot alerts
- [ ] Add GitHub Actions workflow
- [ ] Add status badges to README
- [ ] Create issue templates

### **Optional:**
- [ ] Add social preview image
- [ ] Create CODEOWNERS file
- [ ] Set up GitHub Pages (for documentation)
- [ ] Create project board

---

## 🚀 **Quick Setup Commands**

Run these to configure via CLI:

\`\`\`bash
# Enable features
gh repo edit jeremypfi/ace-tracker --enable-issues=true
gh repo edit jeremypfi/ace-tracker --enable-discussions=true
gh repo edit jeremypfi/ace-tracker --enable-projects=true
gh repo edit jeremypfi/ace-tracker --enable-wiki=false

# Add topics
gh repo edit jeremypfi/ace-tracker --add-topic hurricane,weather,python,noaa,ace,tropical-cyclones,meteorology

# Update description
gh repo edit jeremypfi/ace-tracker --description "Python tool tracking ACE for Atlantic & Pacific hurricane basins. Generates Excel spreadsheets and HTML dashboards using NOAA HURDAT2 data."

# Make public (if desired)
gh repo edit jeremypfi/ace-tracker --visibility public
\`\`\`

---

## 👥 **Sharing With Friends**

### **Option A: Public Repository**

\`\`\`bash
# 1. Make public
gh repo edit jeremypfi/ace-tracker --visibility public

# 2. Share the URL
Send them: https://github.com/jeremypfi/ace-tracker

# 3. They can:
- View the code
- Clone it: git clone https://github.com/jeremypfi/ace-tracker.git
- Fork it (make their own copy)
- Open issues
- Submit pull requests
\`\`\`

### **Option B: Private + Collaborators**

\`\`\`bash
# 1. Keep private (it already is)

# 2. Add friends as collaborators
gh repo edit jeremypfi/ace-tracker --add-collaborator friend-username --permission write

# 3. They get email invitation

# 4. They can:
- View the code
- Clone it
- Push changes
- Open issues
\`\`\`

---

## 🎓 **Best Practices for Collaborating**

### **Communication:**
- Use **Issues** for bugs and features
- Use **Discussions** for Q&A and ideas
- Use **Pull Requests** for code changes

### **Workflow:**
1. Friend forks or clones repo
2. Friend creates branch: `git checkout -b fix-bug`
3. Friend makes changes
4. Friend opens Pull Request
5. You review and merge

### **Protection:**
- Don't give Admin access to others
- Use **Write** access for trusted friends
- Review all pull requests before merging
- Enable branch protection on `main`

---

## 📞 **Need Help?**

### **GitHub Support:**
- https://support.github.com
- https://docs.github.com

### **For This Project:**
- Open an issue: https://github.com/jeremypfi/ace-tracker/issues
- Start a discussion: https://github.com/jeremypfi/ace-tracker/discussions

---

## ✨ **You're Ready!**

Your repository is now configured with:
- ✅ Security settings
- ✅ Collaboration features
- ✅ Quality controls
- ✅ Documentation
- ✅ Best practices

**Time to share it with your friends!** 🎉

---

**Last Updated:** April 24, 2026
