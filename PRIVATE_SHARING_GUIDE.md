# 🔒 Private Repository - Controlled Sharing Guide

**Your Setup:** Private repo with full merge control

**Goal:** Only people you choose can access, and YOU approve all changes.

---

## ✅ **Your Configuration**

```
Repository: PRIVATE 🔒
Access: Invite-only
Merging: Only YOU can merge
Approval: YOU must review all PRs
Friends can: View, clone, create branches, open PRs
Friends cannot: Push to main, merge PRs, access settings
```

**Perfect for:** Selective sharing with full control

---

## 📋 **Setup Checklist**

### ✅ **Step 1: Keep Repo Private**
**Status:** Already done! Your repo is private.

**Verify:**
```bash
gh repo view jeremypfi/ace-tracker --json isPrivate
# Should show: "isPrivate": true
```

---

### ✅ **Step 2: Set Up Branch Protection**

**Go to:** https://github.com/jeremypfi/ace-tracker/settings/branches

**Click:** "Add branch protection rule"

**Settings:**

```
Branch name pattern: main

☑️ Require a pull request before merging
   ☑️ Require approvals: 1
   ☑️ Dismiss stale pull request approvals when new commits are pushed
   ☑️ Require review from Code Owners

☑️ Do not allow bypassing the above settings
   → Even you must follow these rules!

☑️ Restrict who can push to matching branches
   → Add: jeremypfi (ONLY YOU)
   → This prevents friends from pushing directly

☐ Require status checks to pass before merging
   → Enable later when GitHub Actions runs

☐ Require conversation resolution before merging
   → Optional but recommended

☐ Require signed commits
   → Optional (advanced security)

☐ Require linear history
   → Optional (keeps history clean)

☑️ Include administrators
   → Rules apply to you too (safety!)

☐ Allow force pushes
   → Keep OFF (dangerous)

☐ Allow deletions
   → Keep OFF (dangerous)
```

**Click:** "Create"

---

### ✅ **Step 3: Invite Friends**

**Method 1: GitHub Web**
1. Go to: https://github.com/jeremypfi/ace-tracker/settings/access
2. Click "Add people"
3. Enter GitHub username
4. **Select:** Write (NOT Maintain or Admin!)
5. Click "Add to repository"

**Method 2: GitHub CLI**
```bash
gh api repos/jeremypfi/ace-tracker/collaborators/FRIEND_USERNAME \
  -X PUT \
  -f permission=write
```

**They receive:**
- Email invitation
- Access once they accept

---

### ✅ **Step 4: Verify CODEOWNERS**

**Status:** Already created! ✅

**File:** `.github/CODEOWNERS`

**Contents:**
```
* @jeremypfi
```

**What it does:**
- Automatically requests YOUR review on all PRs
- PRs cannot merge without your approval

---

## 🔄 **How Friends Collaborate**

### **Friend's Workflow:**

1. **Clone your repo:**
   ```bash
   git clone https://github.com/jeremypfi/ace-tracker.git
   cd ace-tracker
   ```

2. **Create a branch:**
   ```bash
   git checkout -b friend-feature-name
   ```

3. **Make changes:**
   ```bash
   # Edit files
   git add .
   git commit -m "Add feature: description"
   ```

4. **Push to their branch:**
   ```bash
   git push origin friend-feature-name
   ```

5. **Open Pull Request:**
   - Go to GitHub
   - Click "Compare & pull request"
   - Fill out description
   - Submit PR

6. **Wait for YOUR approval:**
   - They CANNOT merge it
   - Only YOU can merge
   - They see: "Waiting for review"

---

### **Your Workflow (Reviewing PRs):**

1. **Get notification:**
   - Email: "Friend opened a pull request"
   - GitHub notification

2. **Review the PR:**
   ```bash
   # Go to: https://github.com/jeremypfi/ace-tracker/pulls
   # Click on the PR
   ```

3. **Check the changes:**
   - Click "Files changed" tab
   - Review code line-by-line
   - Add comments if needed

4. **Test locally (optional):**
   ```bash
   git fetch origin
   git checkout friend-feature-name
   python3 test_ace_tracker.py  # Run tests
   python3 ace_tracker.py       # Test it works
   ```

5. **Approve or Request Changes:**

   **To approve:**
   - Click "Review changes"
   - Select "Approve"
   - Click "Submit review"
   - Click "Merge pull request"
   - Click "Confirm merge"

   **To request changes:**
   - Click "Review changes"
   - Select "Request changes"
   - Add comments explaining what to fix
   - Click "Submit review"
   - Friend makes changes and pushes again

6. **Delete branch after merge:**
   - GitHub will prompt: "Delete branch"
   - Click it (keeps repo clean)

---

## 🚫 **What Friends CANNOT Do**

With your setup, friends are blocked from:

❌ Pushing directly to `main` branch
❌ Merging their own pull requests
❌ Merging anyone else's pull requests
❌ Bypassing branch protection
❌ Deleting branches on `main`
❌ Force pushing
❌ Accessing repository settings
❌ Adding/removing collaborators
❌ Making the repo public
❌ Deleting the repository

**Only YOU can do these things!** ✅

---

## 🎯 **Testing Your Setup**

### **Test 1: Can Friend Push to Main?**

Have a friend try:
```bash
git checkout main
echo "test" >> README.md
git add README.md
git commit -m "test"
git push origin main
```

**Expected Result:**
```
remote: error: GH006: Protected branch update failed for refs/heads/main.
remote: error: Changes must be made through a pull request.
```
✅ **BLOCKED!** Working correctly.

---

### **Test 2: Can Friend Merge Their Own PR?**

Have a friend:
1. Create branch
2. Make changes
3. Open PR

**Expected Result:**
- They see the PR page
- They see: "Review required"
- They do NOT see "Merge pull request" button
- Only YOU see the merge button

✅ **BLOCKED!** Working correctly.

---

### **Test 3: Can You Merge Without Approval?**

If you set "Include administrators":
1. You create a PR (for yourself)
2. You must still approve it
3. Only then can you merge

✅ **BLOCKED!** Prevents your own accidents.

---

## 👥 **Managing Collaborators**

### **View Current Collaborators:**
```bash
gh api repos/jeremypfi/ace-tracker/collaborators
```

### **Add New Friend:**
```bash
gh api repos/jeremypfi/ace-tracker/collaborators/NEW_FRIEND \
  -X PUT \
  -f permission=write
```

### **Remove Friend:**
```bash
gh api repos/jeremypfi/ace-tracker/collaborators/FRIEND_NAME \
  -X DELETE
```

**Or via web:**
- Settings → Access → Click X next to their name

---

## 📧 **Notification Settings**

**Make sure you get notified of PRs:**

1. Go to repo page
2. Click "Watch" → "All Activity"
3. Go to: https://github.com/settings/notifications
4. Enable: "Email" for participating and watching

**You'll receive emails for:**
- New pull requests
- New comments
- New issues
- Code review requests

---

## 🔒 **Security Best Practices**

### **Do:**
✅ Give friends "Write" access only
✅ Require PR reviews
✅ Enable branch protection
✅ Review all PRs before merging
✅ Delete branches after merging
✅ Keep repo private
✅ Revoke access when someone leaves

### **Don't:**
❌ Give "Admin" access to friends
❌ Allow bypassing branch protection
❌ Disable CODEOWNERS
❌ Merge without reviewing
❌ Share sensitive data in repo
❌ Add too many collaborators

---

## 🆘 **Troubleshooting**

### **Problem: Friend can't see the repo**

**Solution:**
1. Check they accepted the invitation
2. Verify: Settings → Access → They're listed
3. Confirm repo is private (not public)

---

### **Problem: Friend can push to main**

**Solution:**
1. Check branch protection: Settings → Branches
2. Verify "Restrict who can push" is enabled
3. Confirm only YOUR username is listed

---

### **Problem: Friend can merge their own PR**

**Solution:**
1. Check branch protection: Settings → Branches
2. Verify "Require a pull request before merging" is ON
3. Verify "Require approvals: 1" is set
4. Check CODEOWNERS file exists

---

### **Problem: You can't merge your own PR**

**Expected behavior!** If you enabled "Include administrators":
- Even you must get approval
- Create a second account or ask a friend to approve
- Or temporarily disable "Include administrators"

---

## 📚 **Quick Reference**

### **Your Permissions:**
✅ Everything (you're the owner)

### **Friend Permissions (Write):**
✅ View code
✅ Clone repository
✅ Create branches
✅ Push to their branches
✅ Open pull requests
✅ Comment on issues/PRs
✅ Create issues
❌ Push to main
❌ Merge PRs
❌ Delete branches
❌ Change settings

### **Key URLs:**
- **Settings:** https://github.com/jeremypfi/ace-tracker/settings
- **Access:** https://github.com/jeremypfi/ace-tracker/settings/access
- **Branches:** https://github.com/jeremypfi/ace-tracker/settings/branches
- **Pull Requests:** https://github.com/jeremypfi/ace-tracker/pulls

---

## ✅ **Final Checklist**

Before sharing with friends:

- [ ] Repo is private ✓ (already done)
- [ ] Branch protection on `main` (do this now)
- [ ] CODEOWNERS file added ✓ (already done)
- [ ] You're the only one who can merge
- [ ] Notifications enabled
- [ ] Friends added with "Write" permission

**Once set up, you have complete control!** 🎉

---

## 🎓 **Remember:**

1. **Private = Invite only** - Only people you add can see it
2. **Write permission = Can code** - But can't merge
3. **Branch protection = You control merging** - Must review all PRs
4. **CODEOWNERS = Auto-review** - Automatically requests your approval
5. **You're the boss** - Full control always

**Your friends can help, but YOU make all final decisions!** ✅

---

**Questions?** This setup gives you maximum control while allowing collaboration!
