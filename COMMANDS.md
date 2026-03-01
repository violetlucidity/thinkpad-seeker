# ThinkPad Seeker — Commands Reference

A copy-paste command guide for setting up, running, and working on this project.
Each command block is ready to paste directly into your terminal.

> **Which terminal?**
> - **Windows:** open "Command Prompt" or "PowerShell" from the Start menu
> - **Mac/Linux:** open "Terminal"
>
> Lines starting with `#` are comments — you can include them when you paste,
> they won't run.

---

## 1. Get the Code (First Time Only)

### Clone the repository to your computer

```bash
# Download the repo into a new folder called thinkpad-seeker
git clone https://github.com/violetlucidity/thinkpad-seeker.git

# Move into that folder — you must be inside it for every other command to work
cd thinkpad-seeker
```

### Confirm you're in the right place

```bash
# Should list files like tracker.py, run.py, config.yaml, etc.
ls
```

---

## 2. Set Up Python (First Time Only)

### Create an isolated Python environment

A virtual environment keeps this project's packages separate from everything
else on your computer. You only do this once per machine.

**Mac / Linux:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

**Windows (PowerShell):**
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

**Windows (Command Prompt):**
```cmd
python -m venv .venv
.venv\Scripts\activate.bat
```

> Your prompt will change to show `(.venv)` at the start — that means it worked.
> You need to run the activate command every time you open a new terminal window.

### Install all dependencies

```bash
# Reads requirements.txt and installs every listed package
pip install -r requirements.txt
```

---

## 3. Configure the App (First Time Only)

The app reads its settings from `config.yaml`. Open it in any text editor and
fill in the sections you want to use.

```bash
# On Mac/Linux, open in the default text editor:
open config.yaml

# On Windows:
notepad config.yaml
```

At minimum, check that `govdeals.enabled` is `true`. Everything else
(email, push notifications, VAPID keys) can be filled in later.

---

## 4. Run the App

### Start the web interface

```bash
python run.py
```

Then open **http://localhost:5000** in your browser.

Press `Ctrl+C` in the terminal to stop the server.

### Run a one-off scrape from the command line (no web UI needed)

```bash
python tracker.py --once
```

### Run the scraper on a repeating timer (every 3 hours)

```bash
python tracker.py --loop 180
```

### Open Municibid and HiBid tabs in your browser

```bash
python browser_opener.py
```

### Run a scrape without sending any notifications (useful for testing)

```bash
python tracker.py --once --no-email --no-push
```

---

## 5. Everyday Git Commands

These are the commands you'll use most often when working on the project.

### See what has changed since your last commit

```bash
# Shows which files are modified, new, or deleted
git status
```

### Pull the latest changes from GitHub

Always do this before you start working to make sure you have the newest code.

```bash
git pull origin main
```

> If you're on the development branch instead:
> ```bash
> git pull origin claude/multi-phase-build-sequence-npEdN
> ```

### See exactly what changed inside the files

```bash
# Shows the actual lines that were added (+) or removed (-)
git diff
```

### Save your changes (add → commit → push)

This is the core three-step loop for saving your work to GitHub.

```bash
# Step 1: Stage the files you want to save
#   To stage everything at once:
git add .

#   To stage one specific file:
git add tracker.py

#   To stage several specific files:
git add run.py templates/index.html

# Step 2: Commit — create a labeled save point with a short description
git commit -m "describe what you changed here"

# Step 3: Push — upload your commit to GitHub
git push
```

### View your commit history

```bash
# Shows the last 10 commits, most recent first
git log --oneline -10
```

---

## 6. Branches

Branches let you try something out without touching the stable main code.

### See which branch you're on

```bash
git branch
```

> The branch with `*` in front is your current one.

### Create and switch to a new branch

```bash
# Replace "my-new-feature" with whatever name makes sense
git checkout -b my-new-feature
```

### Switch back to main

```bash
git checkout main
```

### Switch to the existing Claude Code dev branch

```bash
git checkout claude/multi-phase-build-sequence-npEdN
```

### Push a new branch to GitHub for the first time

```bash
# The -u flag links your local branch to the remote so future pushes are just "git push"
git push -u origin my-new-feature
```

### Merge a branch into main when you're done

```bash
# Switch to main first
git checkout main

# Pull any changes that happened on GitHub while you were working
git pull origin main

# Merge your feature branch into main
git merge my-new-feature
```

---

## 7. Undoing Mistakes

> **Rule of thumb:** if you haven't committed yet, changes are easy to undo.
> Once you've committed, they're still recoverable but require a bit more care.

### Discard changes to a file you haven't committed yet

```bash
# WARNING: this permanently throws away your unsaved edits to that file
git checkout -- tracker.py
```

### Unstage a file (undo a "git add" before you commit)

```bash
git restore --staged tracker.py
```

### Undo your most recent commit but keep the file changes

Useful if you committed too soon or want to change the commit message.

```bash
# Removes the commit label but leaves your files exactly as they were
git reset --soft HEAD~1
```

### See what a file looked like in an older commit

```bash
# List recent commits to find the hash you want
git log --oneline -20

# View the old version of a file (replace abc1234 with the actual commit hash)
git show abc1234:tracker.py
```

### Stash work-in-progress so you can switch branches cleanly

```bash
# Save your uncommitted changes to a temporary shelf
git stash

# Do whatever you need on another branch, then bring them back
git stash pop
```

---

## 8. Working Alongside Claude Code

When you ask Claude Code (CCW) to make changes, this is the typical workflow:

```bash
# 1. Before asking Claude to work — make sure you're up to date
git pull origin main

# 2. After Claude makes changes — review what it did
git status
git diff

# 3. If everything looks good, save it
git add .
git commit -m "claude: short description of what changed"
git push

# 4. If something looks wrong and you want to revert ALL of Claude's changes
#    (only if you haven't committed yet!)
git checkout -- .
```

### Compare your branch to main to see everything Claude has changed

```bash
git diff main...HEAD
```

### View all commits Claude made on the dev branch

```bash
git log --oneline origin/main..HEAD
```

---

## 9. Staying Up to Date

### Check if GitHub has newer commits you don't have locally

```bash
# Fetches metadata from GitHub without changing your files
git fetch origin

# Then compare
git log HEAD..origin/main --oneline
```

> If this prints nothing, you're already up to date.

### Update your local branch to match GitHub exactly

```bash
git pull origin main
```

---

## 10. Quick Troubleshooting

### "command not found: python"

Try `python3` instead:
```bash
python3 run.py
python3 tracker.py --once
```

### "(.venv) disappeared from my prompt"

Your virtual environment deactivated. Re-activate it:

**Mac/Linux:**
```bash
source .venv/bin/activate
```

**Windows PowerShell:**
```powershell
.venv\Scripts\Activate.ps1
```

### "port 5000 already in use"

Another process is using port 5000. Either stop it, or run on a different port:
```bash
# Run the Flask app on port 5001 instead
python run.py --port 5001
```

Or find and stop whatever is using 5000:

**Mac/Linux:**
```bash
lsof -i :5000
kill -9 <PID>    # replace <PID> with the number shown by lsof
```

**Windows:**
```cmd
netstat -ano | findstr :5000
taskkill /PID <PID> /F
```

### "ModuleNotFoundError"

A package is missing. Install everything again:
```bash
pip install -r requirements.txt
```

### "git push" was rejected

Someone else (or Claude Code) pushed to the branch since your last pull.
Pull first, then push:
```bash
git pull origin main --rebase
git push
```

---

## 11. Full First-Time Setup Checklist

Copy and paste this whole block to get from zero to running in one go
(Mac/Linux):

```bash
git clone https://github.com/violetlucidity/thinkpad-seeker.git
cd thinkpad-seeker
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python run.py
```

Then open **http://localhost:5000** in your browser.

---

*Keep this file open in a second tab while you work.*
*Whenever you forget a command, it's probably in here.*
