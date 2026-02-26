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

## NOTIFICATIONS SETUP — ThinkPad Seeker

Step 1: Install Tailscale (one-time, required for phone access)
  a. Download Tailscale from https://tailscale.com/download
     - Install on your Windows computer
     - Install the Tailscale app on your Android phone
  b. Log in to the same Tailscale account on both devices.
  c. In the Tailscale admin panel (https://login.tailscale.com/admin/machines),
     find your computer's Tailscale IP address (format: 100.x.x.x).
  d. Add this IP to config.yaml under the key "tailscale_ip".
  e. From your phone's browser, navigate to http://[tailscale-ip]:5000
     to confirm connectivity before proceeding.

Step 2: Generate VAPID Keys (one-time)
  a. With the virtual environment active, run:
       python generate_vapid_keys.py
  b. Copy the two output values into config.yaml under the "vapid" key.
  c. Ensure config.yaml is listed in .gitignore — it must NOT be committed
     after adding real VAPID keys (it contains your private key).

Step 3: Register Push Subscription (one-time per phone)
  a. On your Android phone, open Chrome and navigate to
       http://[tailscale-ip]:5000
  b. When the browser shows "Allow notifications?", tap Allow.
  c. The phone is now subscribed. Notifications will appear in the system
     tray after each scrape run that finds new listings.
  d. If you ever switch phones or clear Chrome's data, repeat this step.

Step 4: Set Up Windows Auto-Start (one-time)
  See TASK SCHEDULER SETUP section above.

Step 5: Confirm Everything Works
  a. With the app running, click "Run Scrape Now" in the web interface.
  b. Within 30 seconds, a notification should appear in your Android tray.
  c. Tap the notification — it should open the ThinkPad Seeker checklist
     in Chrome on your phone.
  d. Check two or three items and tap "Open Selected" — the listing URLs
     should open as new tabs.
