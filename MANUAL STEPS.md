# MANUAL STEPS — ThinkPad Seeker

This document collects every one-time setup action that cannot be automated.
Follow these steps in order the first time you deploy the project.

---

## TASK SCHEDULER SETUP (Windows)

1. Open Windows Task Scheduler (search "Task Scheduler" in Start menu).
2. Click Action → Import Task.
3. Select `windows-task-scheduler.xml` from the project folder.
4. Edit the task: replace the placeholder paths in the Actions tab with:
   - The actual path to `pythonw.exe` on your machine
     (find it by running: `where pythonw` in a command prompt)
   - The actual path to `run.py` in your project folder
5. Click OK. The app will now start automatically at login.
6. To test: right-click the task → Run.

---

*(Additional sections will be appended as the project grows.)*
