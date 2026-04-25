# 📚 GitHub Best Practices Guide for Beginners

**For:** ACE Tracker project
**Audience:** New to GitHub and publishing code
**Last Updated:** April 24, 2026

---

## 🎯 Quick Start Checklist

Your repo already has these ✅:
- ✅ README.md (documentation)
- ✅ LICENSE (MIT License)
- ✅ .gitignore (protects sensitive files)
- ✅ requirements.txt (dependencies)
- ✅ Test suite (test_ace_tracker.py)

New additions just made ✅:
- ✅ SECURITY.md (security policy)
- ✅ CONTRIBUTING.md (contribution guidelines)
- ✅ Enhanced .gitignore (more protection)

---

## 🔒 SECURITY: What You MUST Know

### ❌ **NEVER Commit These:**

```bash
# 1. Credentials & API Keys
.env                    # Environment variables
API_KEY = "abc123"      # API keys in code
password = "secret"     # Passwords anywhere
*.pem, *.key           # Private keys
credentials.json        # Google/AWS credentials

# 2. Personal Data
emails.csv             # Email lists
users.db               # User databases
personal/              # Personal files

# 3. Large Files
*.mp4, *.mov           # Videos
*.zip, *.tar.gz        # Large archives
dataset.csv (>100MB)   # Huge datasets
```

**Your repo is safe ✅** - You don't have any of these!

### ✅ **How to Check Before Committing:**

```bash
# Review what you're about to commit
git status
git diff

# Check for secrets
grep -r "password" .
grep -r "api_key" .
grep -r "secret" .

# If you find any, add to .gitignore IMMEDIATELY
```

---

## 🚨 **If You Accidentally Commit a Secret**

### **EMERGENCY STEPS:**

1. **Don't panic!** It can be fixed.

2. **Immediate action:**
   ```bash
   # Change the password/key IMMEDIATELY
   # Even if you delete the commit, it's in Git history
   ```

3. **Remove from history:**
   ```bash
   # Contact GitHub support or use BFG Repo-Cleaner
   # This is advanced - ask for help if needed
   ```

4. **Prevention:**
   - Always use `.env` files for secrets (add to .gitignore)
   - Never hardcode credentials
   - Use environment variables

---

## 📂 **GitHub Features You Should Use**

### **1. Issues** (Bug tracking)
- Track bugs and feature requests
- Organize with labels (bug, enhancement, question)
- Close issues when fixed

**Example:** https://github.com/jeremypfi/ace-tracker/issues

### **2. Releases** (Version tags)
When you have a stable version:
```bash
git tag -a v1.0.0 -m "First stable release"
git push origin v1.0.0
```

Then create a Release on GitHub with:
- Version number (v1.0.0)
- Release notes
- Attached files (optional)

### **3. GitHub Actions** (Automation)
Auto-run tests when you push code:

Create `.github/workflows/tests.yml`:
```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.9'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
      - name: Run tests
        run: python3 test_ace_tracker.py
```

### **4. Branch Protection**
Settings → Branches → Add rule for `main`:
- ✅ Require pull request reviews
- ✅ Require status checks to pass
- ✅ Require branches to be up to date

---

## 📝 **Commit Message Best Practices**

### ❌ **Bad commit messages:**
```bash
git commit -m "fix"
git commit -m "update stuff"
git commit -m "asdfasdf"
```

### ✅ **Good commit messages:**
```bash
git commit -m "Fix duration calculation for current season storms"
git commit -m "Add unit tests for ACE calculation"
git commit -m "Update README with installation instructions"
```

**Format:**
```
<type>: <short description>

<optional longer description>

<optional footer>
```

**Types:**
- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation
- `test:` Tests
- `refactor:` Code restructuring
- `chore:` Maintenance

---

## 🌿 **Branching Strategy**

### **For Solo Projects (like yours):**

```bash
main              # Stable, working code
├── feature-x     # New feature branch
├── fix-bug-y     # Bug fix branch
└── experiment-z  # Experimental branch
```

**Workflow:**
```bash
# Create feature branch
git checkout -b add-new-basin

# Make changes
# ... edit files ...

# Commit
git add .
git commit -m "feat: Add support for Western Pacific basin"

# Push to GitHub
git push origin add-new-basin

# Create Pull Request on GitHub
# Merge when ready
# Delete branch after merging
```

### **When Working with Others:**

Use Pull Requests (PRs):
1. Fork the repo
2. Create a branch
3. Make changes
4. Submit PR
5. Code review
6. Merge

---

## 🔍 **Code Review Checklist**

Before pushing code, ask yourself:

- [ ] Does it work? (Test it!)
- [ ] Are tests passing?
- [ ] Is it documented?
- [ ] No secrets/credentials?
- [ ] No personal data?
- [ ] Good commit message?
- [ ] .gitignore updated if needed?

---

## 📈 **Growing Your Project**

### **1. Add a Badge to README:**
Show off your project status!

```markdown
![Tests](https://github.com/jeremypfi/ace-tracker/workflows/Tests/badge.svg)
![Python Version](https://img.shields.io/badge/python-3.7+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
```

### **2. Add Topics on GitHub:**
Settings → Topics → Add:
- `hurricane`
- `weather`
- `python`
- `noaa`
- `ace`
- `tropical-cyclones`

Helps people find your project!

### **3. Create a Project Board:**
Organize tasks visually:
- Projects → New Project
- Add columns: To Do, In Progress, Done
- Add issues/cards

### **4. Enable Discussions:**
Settings → Features → ✅ Discussions
- Better than Issues for Q&A
- Community engagement

---

## 🚀 **Publishing Best Practices**

### **What to Include:**

✅ **Must have:**
- README.md (what, why, how)
- LICENSE (legal terms)
- .gitignore (exclude files)
- requirements.txt (dependencies)

✅ **Should have:**
- CONTRIBUTING.md (how to contribute)
- SECURITY.md (security policy)
- Tests (prove it works)
- Examples (show usage)

✅ **Nice to have:**
- CHANGELOG.md (version history)
- Screenshots/GIFs
- Badges
- Documentation site

### **What to Exclude:**

❌ Generated files (data/*.xlsx)
❌ IDE settings (.vscode/)
❌ OS files (.DS_Store)
❌ Dependencies (node_modules/, venv/)
❌ Personal data
❌ Credentials

---

## 🛠️ **Useful Git Commands**

```bash
# Check status
git status

# See what changed
git diff

# Undo local changes (before commit)
git checkout -- filename.py

# Undo last commit (keep changes)
git reset --soft HEAD~1

# Undo last commit (discard changes) ⚠️
git reset --hard HEAD~1

# View commit history
git log --oneline

# See who changed what
git blame filename.py

# Search commits
git log --grep="bug fix"

# Create branch
git checkout -b new-branch

# Switch branches
git checkout main

# Delete branch
git branch -d old-branch

# Push with upstream
git push -u origin branch-name

# Pull latest changes
git pull origin main

# Merge branch
git checkout main
git merge feature-branch
```

---

## 📊 **GitHub Analytics**

Track your project:
- **Insights** tab: Traffic, commits, contributors
- **Pulse**: Recent activity summary
- **Community**: Health metrics

---

## 🤝 **Community Standards**

GitHub checks your repo health:
- Insights → Community → Community profile

**Complete checklist:**
- ✅ Description
- ✅ README
- ✅ License
- ✅ Contributing guide (NEW ✅)
- ✅ Code of conduct (optional for solo projects)
- ✅ Security policy (NEW ✅)

---

## 💡 **Pro Tips for Beginners**

### **1. Commit Often**
```bash
# Good: Small, focused commits
git commit -m "Add duration calculation"
git commit -m "Add unit test for duration"
git commit -m "Update README with duration info"

# Bad: Huge commit after 3 days of work
git commit -m "Added lots of stuff"
```

### **2. Write for Future You**
Your README should answer:
- What is this?
- Why does it exist?
- How do I use it?
- How do I contribute?

### **3. Use .gitignore Early**
Add files to .gitignore BEFORE committing:
```bash
echo "data/*.xlsx" >> .gitignore
git add .gitignore
git commit -m "Ignore generated Excel files"
```

### **4. Backup is Built-in**
GitHub IS your backup. Commit regularly!

### **5. Learn from Others**
Browse popular Python repos:
- https://github.com/psf/requests
- https://github.com/pallets/flask
- See how they structure projects

---

## 🆘 **Common Problems & Solutions**

### **Problem 1: Merge Conflicts**
```bash
# When pulling changes conflicts with your local work
git pull
# CONFLICT in filename.py

# Fix conflicts manually in the file
# Look for <<<<<<< and >>>>>>>
# Edit the file to keep what you want

git add filename.py
git commit -m "Resolve merge conflict"
```

### **Problem 2: Accidentally Committed Large File**
```bash
# GitHub rejects files > 100MB
# Remove from last commit
git rm --cached large-file.zip
echo "*.zip" >> .gitignore
git commit --amend
```

### **Problem 3: Forgot to Branch**
```bash
# Made changes on main, should be on branch
git stash                  # Save changes
git checkout -b new-branch # Create branch
git stash pop             # Restore changes
git add .
git commit -m "Feature on correct branch"
```

---

## 📚 **Learning Resources**

### **GitHub Learning Lab:**
https://lab.github.com/
- Interactive courses
- Free for everyone

### **Git Documentation:**
https://git-scm.com/doc
- Official reference
- Book: Pro Git (free online)

### **GitHub Docs:**
https://docs.github.com/
- Comprehensive guides
- Best practices

---

## ✅ **Your Next Steps**

### **Immediate (Do This Week):**
1. ✅ Review SECURITY.md and CONTRIBUTING.md (just added!)
2. ✅ Commit the new files
3. ✅ Add topics to your repo on GitHub
4. ✅ Write a better repo description on GitHub

### **Soon (Before Hurricane Season):**
1. Add screenshots to README
2. Create your first Release (v1.0.0)
3. Set up GitHub Actions for auto-testing
4. Add more examples to README

### **Optional (When You're Ready):**
1. Create a documentation site (GitHub Pages)
2. Add project board for task tracking
3. Enable Discussions for community
4. Write blog post about your project

---

## 🎓 **Key Takeaways**

1. **Security First:** Never commit credentials
2. **Commit Often:** Small, focused commits
3. **Document Everything:** README is your friend
4. **Test Before Pushing:** Always run tests
5. **Learn from Others:** Browse popular repos
6. **Ask for Help:** GitHub community is friendly
7. **Have Fun:** It's your project!

---

## 🌟 **Your Project Status**

**Current Grade: A- (Excellent!)**

What you're doing well:
- ✅ Clear README
- ✅ MIT License
- ✅ Working tests
- ✅ Good .gitignore
- ✅ Security policy (NEW!)
- ✅ Contributing guide (NEW!)
- ✅ No credentials committed

Minor improvements possible:
- 📸 Add screenshots (nice to have)
- 🏷️ Create releases (when stable)
- 🤖 Auto-testing (GitHub Actions)
- 📚 More examples (optional)

**You're doing great for a first project!** 🎉

---

**Questions?** Just ask or open an issue! 😊
