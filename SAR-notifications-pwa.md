# SAR-notifications-pwa.md
# Scrape-and-Review (SAR) Notifications Module — Standard Specification
# Version: 1.0
# Platform: Windows
# Last updated: See repository commit history

---

## PURPOSE

This file is a mandatory reference specification for all Scrape-and-Review (SAR)
projects. It defines a standard notifications and scheduling layer that must be
integrated into every SAR project during the build. When a `claude-*.md` file
instructs Claude Code to read this document, every requirement below has the same
authority as requirements written directly into that file.

---

## HOW TO REFERENCE THIS FILE FROM A `claude-*.md` FILE

Place the following block as the FIRST PROMPT in every SAR project's
`claude-*.md` file, before any scaffold or build steps:

```
## PROMPT 0 — Load Notifications Specification

Before writing any code, read the file `SAR-notifications-pwa.md` from
the project context. Confirm you have read it by listing the six component
names described in the COMPONENTS section. These requirements are mandatory
and must be woven into the build steps that follow — do not treat them as
an optional add-on to be handled at the end.
```

---

## COMPONENTS

This module adds six components to any SAR project:

1. APScheduler with misfire grace period (scheduling)
2. Windows Task Scheduler auto-start entry (startup)
3. PWA manifest and service worker (phone installability)
4. Web Push subscription endpoint (notification registration)
5. Push notification on scrape completion (trigger)
6. Mobile-first "Open Selected" button behavior (interaction)

---

## COMPONENT 1 — APScheduler with Misfire Grace Period

### Dependency
```
apscheduler>=3.10.0
```
Add to `requirements.txt`.

### Scheduler Initialization
In the main application file (typically `run.py` or `app.py`), initialize the
scheduler as follows. Add a comment to each significant line as shown:

```python
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore

# Store job state in SQLite so missed jobs survive process restarts
jobstores = {
    'default': SQLAlchemyJobStore(url='sqlite:///jobs.sqlite')
}

# misfire_grace_time: if a job was missed (computer was off/asleep),
# run it immediately on wakeup as long as fewer than 6 hours have passed
scheduler = BackgroundScheduler(
    jobstores=jobstores,
    job_defaults={'misfire_grace_time': 21600}  # 21600 seconds = 6 hours
)
```

### Job Registration
Register the scrape function with a cron trigger. The schedule should be
configurable via `config.json` so the user can adjust it without editing code.
The default schedule is Tuesday and Friday at 08:00 local time:

```python
# Read schedule from config; fall back to Tue/Fri 08:00 if not set
schedule_cfg = config.get('schedule', {'days': 'tue,fri', 'hour': 8, 'minute': 0})

scheduler.add_job(
    run_scrape,                          # the function to call
    trigger='cron',
    day_of_week=schedule_cfg['days'],    # e.g. 'tue,fri'
    hour=schedule_cfg['hour'],           # local time hour
    minute=schedule_cfg['minute'],
    id='scrape_job',
    replace_existing=True                # prevents duplicate jobs on restart
)

scheduler.start()  # starts the scheduler thread alongside Flask
```

### config.json Schedule Block
Add the following key to `config.json.example`:
```json
"schedule": {
  "days": "tue,fri",
  "hour": 8,
  "minute": 0,
  "timezone": "America/New_York"
}
```

Include a comment in `config.json.example` (as a sibling `_comment` key):
```json
"_schedule_comment": "Set 'days' to any combination of mon,tue,wed,thu,fri,sat,sun. Hour uses 24-hour format in the timezone specified."
```

---

## COMPONENT 2 — Windows Auto-Start via Task Scheduler XML

### What this does
Creates a Windows Task Scheduler entry so that `run.py` starts automatically
when the user logs in to Windows. This ensures APScheduler is always running
and can fire scheduled scrapes.

### Deliverable
Generate a file named `windows-task-scheduler.xml` in the repository root.
This file should be importable directly into Windows Task Scheduler via
Task Scheduler → Action → Import Task.

The XML template is:

```xml
<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <Triggers>
    <!-- Trigger: run at logon for any user -->
    <LogonTrigger>
      <Enabled>true</Enabled>
    </LogonTrigger>
  </Triggers>
  <Actions Context="LocalService">
    <Exec>
      <!-- MANUAL STEP: Replace the path below with the actual path to pythonw.exe
           and the actual path to run.py on the user's machine.
           Use pythonw.exe (not python.exe) to run without a visible terminal window.
           Example: C:\Users\YourName\AppData\Local\Programs\Python\Python312\pythonw.exe -->
      <Command>pythonw.exe</Command>
      <!-- MANUAL STEP: Replace with the full path to run.py -->
      <Arguments>C:\path\to\your\project\run.py</Arguments>
      <WorkingDirectory>C:\path\to\your\project</WorkingDirectory>
    </Exec>
  </Actions>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <!-- Do not start the task if the computer is on battery power -->
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <ExecutionTimeLimit>PT0S</ExecutionTimeLimit>
    <!-- Restart the task if it fails, up to 3 times, waiting 1 minute between attempts -->
    <RestartOnFailure>
      <Interval>PT1M</Interval>
      <Count>3</Count>
    </RestartOnFailure>
  </Settings>
</Task>
```

### MANUAL STEPS Entry (add to MANUAL STEPS document)
```
TASK SCHEDULER SETUP (Windows):
1. Open Windows Task Scheduler (search "Task Scheduler" in Start menu).
2. Click Action → Import Task.
3. Select windows-task-scheduler.xml from the project folder.
4. Edit the task: replace the placeholder paths in the Actions tab with:
   - The actual path to pythonw.exe on your machine
     (find it by running: where pythonw in a command prompt)
   - The actual path to run.py in your project folder
5. Click OK. The app will now start automatically at login.
6. To test: right-click the task → Run.
```

---

## COMPONENT 3 — PWA Manifest and Service Worker

### Purpose
Makes the web app installable as a Progressive Web App (PWA) on Android Chrome,
which is required for Web Push notifications. The phone must visit and accept
the push permission prompt once before notifications will work.

### Files to generate

**`static/manifest.json`**
```json
{
  "name": "PROJECT_NAME",
  "short_name": "PROJECT_SHORT",
  "start_url": "/",
  "display": "standalone",
  "background_color": "#ffffff",
  "theme_color": "#333333",
  "icons": [
    {
      "src": "/static/icons/icon-192.png",
      "sizes": "192x192",
      "type": "image/png"
    },
    {
      "src": "/static/icons/icon-512.png",
      "sizes": "512x512",
      "type": "image/png"
    }
  ]
}
```
Replace `PROJECT_NAME` and `PROJECT_SHORT` with the project's actual name.
Generate simple placeholder PNG icons (solid color with initials) using Pillow
if no icons are provided.

**`static/sw.js`** (service worker)
```javascript
// Service worker for SAR PWA notifications
// Handles push events delivered by the server and shows them in the system tray

self.addEventListener('install', event => {
    // Activate the new service worker immediately without waiting
    self.skipWaiting();
});

self.addEventListener('activate', event => {
    // Take control of all open pages immediately
    event.waitUntil(self.clients.claim());
});

// Listen for push events sent by the Flask backend
self.addEventListener('push', event => {
    // Parse the JSON payload sent by the server
    const data = event.data ? event.data.json() : {};

    const title = data.title || 'Scrape Complete';
    const options = {
        body: data.body || 'New listings are ready to review.',
        icon: '/static/icons/icon-192.png',
        badge: '/static/icons/icon-192.png',
        // tag prevents duplicate notifications if the push fires more than once
        tag: 'sar-scrape-result',
        // renotify: true causes the notification sound/vibration even if tag matches
        renotify: true,
        // data payload carries the URL to open when the notification is tapped
        data: { url: data.url || '/' }
    };

    event.waitUntil(self.registration.showNotification(title, options));
});

// When the user taps the notification, open the app URL in the mobile browser
self.addEventListener('notificationclick', event => {
    event.notification.close();
    const targetUrl = event.notification.data.url;

    event.waitUntil(
        clients.matchAll({ type: 'window', includeUncontrolled: true }).then(clientList => {
            // If the app is already open, focus it instead of opening a new tab
            for (const client of clientList) {
                if (client.url === targetUrl && 'focus' in client) {
                    return client.focus();
                }
            }
            // Otherwise open a new browser tab
            if (clients.openWindow) {
                return clients.openWindow(targetUrl);
            }
        })
    );
});
```

### HTML `<head>` additions
Add the following to the main `index.html` template `<head>` block:
```html
<!-- PWA manifest link -->
<link rel="manifest" href="/static/manifest.json">
<!-- Theme color for Android Chrome address bar -->
<meta name="theme-color" content="#333333">
```

### Service worker registration (add to main JS file)
```javascript
// Register the service worker for push notification support
// Only runs in browsers that support service workers (Chrome, Firefox, Edge)
if ('serviceWorker' in navigator) {
    window.addEventListener('load', async () => {
        try {
            const registration = await navigator.serviceWorker.register('/static/sw.js');
            console.log('Service worker registered:', registration.scope);
            // After registration, request push permission from the user
            await requestPushPermission(registration);
        } catch (err) {
            console.error('Service worker registration failed:', err);
        }
    });
}
```

---

## COMPONENT 4 — Web Push Subscription Endpoint

### Dependencies
```
pywebpush>=2.0.0
```
Add to `requirements.txt`.

### VAPID Key Generation
VAPID keys authenticate the server's right to send push notifications.
Generate them once at project setup time using the following script, saved as
`generate_vapid_keys.py` in the project root:

```python
# generate_vapid_keys.py
# Run this script ONCE to create VAPID keys for Web Push authentication.
# Output will be printed to the console. Paste the values into config.json.
# Do NOT commit config.json (it contains your private key).

from py_vapid import Vapid

vapid = Vapid()
vapid.generate_keys()

print("Add these values to config.json under the 'vapid' key:\n")
print(f"  public_key:  {vapid.public_key.serialize().hex()}")
print(f"  private_key: {vapid.private_key.serialize().hex()}")
```

Add to `config.json.example`:
```json
"vapid": {
  "public_key": "REPLACE_WITH_OUTPUT_OF_generate_vapid_keys.py",
  "private_key": "REPLACE_WITH_OUTPUT_OF_generate_vapid_keys.py",
  "claims": {"sub": "mailto:your@email.com"}
}
```

Add `config.json` to `.gitignore` — it contains the private key.

### Flask Subscription Endpoint
Add the following routes to the Flask application:

```python
from pywebpush import webpush, WebPushException
import json

# In-memory store for push subscriptions (persisted to subscriptions.json)
SUBSCRIPTIONS_FILE = 'subscriptions.json'

def load_subscriptions():
    """Load push subscriptions from disk. Returns empty list if file missing."""
    try:
        with open(SUBSCRIPTIONS_FILE) as f:
            return json.load(f)
    except FileNotFoundError:
        return []

def save_subscriptions(subs):
    """Persist push subscriptions to disk."""
    with open(SUBSCRIPTIONS_FILE, 'w') as f:
        json.dump(subs, f, indent=2)

@app.route('/subscribe', methods=['POST'])
def subscribe():
    """
    Receives a Web Push subscription object from the browser.
    Stores it so the server can send push notifications to this device.
    """
    subscription = request.get_json()
    subs = load_subscriptions()

    # Avoid storing duplicate subscriptions from the same device
    if subscription not in subs:
        subs.append(subscription)
        save_subscriptions(subs)

    return jsonify({'status': 'subscribed'}), 201

@app.route('/vapid-public-key', methods=['GET'])
def vapid_public_key():
    """Returns the VAPID public key to the browser for push subscription setup."""
    return jsonify({'publicKey': config['vapid']['public_key']})
```

### Client-Side Push Subscription (add to main JS file)
```javascript
// Request push notification permission and subscribe to the server
async function requestPushPermission(registration) {
    // Ask the user for notification permission
    const permission = await Notification.requestPermission();
    if (permission !== 'granted') {
        console.warn('Push notification permission denied.');
        return;
    }

    // Fetch the server's VAPID public key
    const resp = await fetch('/vapid-public-key');
    const { publicKey } = await resp.json();

    // Convert the VAPID public key from hex to the Uint8Array format required by the browser
    const convertedKey = hexStringToUint8Array(publicKey);

    // Subscribe to push notifications using the server's public key
    const subscription = await registration.pushManager.subscribe({
        userVisibleOnly: true,     // Android requires this to be true
        applicationServerKey: convertedKey
    });

    // Send the subscription object to the Flask backend for storage
    await fetch('/subscribe', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(subscription)
    });
}

// Helper: convert hex string to Uint8Array for VAPID key handling
function hexStringToUint8Array(hexString) {
    const bytes = new Uint8Array(hexString.length / 2);
    for (let i = 0; i < bytes.length; i++) {
        bytes[i] = parseInt(hexString.substr(i * 2, 2), 16);
    }
    return bytes;
}
```

---

## COMPONENT 5 — Push Notification on Scrape Completion

Add the following helper function to the Flask application and call it at
the end of the `run_scrape()` function:

```python
def send_push_notifications(new_count):
    """
    Sends a Web Push notification to all subscribed devices.
    Called automatically when a scrape run finishes.
    
    Args:
        new_count (int): Number of new listings found in this scrape run.
    """
    if new_count == 0:
        # Do not send a notification if no new listings were found
        return

    subs = load_subscriptions()
    if not subs:
        print("No push subscriptions registered. Open the app on your phone first.")
        return

    # Build the notification payload
    payload = json.dumps({
        "title": "New listings ready",
        "body": f"{new_count} new item{'s' if new_count != 1 else ''} found. Tap to review.",
        "url": "/"   # opens the checklist when the notification is tapped
    })

    vapid_cfg = config['vapid']

    for subscription in subs:
        try:
            webpush(
                subscription_info=subscription,
                data=payload,
                vapid_private_key=vapid_cfg['private_key'],
                vapid_claims=vapid_cfg['claims']
            )
        except WebPushException as e:
            # If a subscription is expired or invalid, remove it from the store
            if e.response and e.response.status_code == 410:
                print(f"Subscription expired, removing: {subscription['endpoint'][:40]}...")
                subs.remove(subscription)
                save_subscriptions(subs)
            else:
                print(f"Push failed: {e}")
```

### Call site in `run_scrape()`
At the end of the `run_scrape()` function, add:
```python
    # Notify the user's phone how many new listings were found
    send_push_notifications(len(new_listings))
```

---

## COMPONENT 6 — Mobile-First "Open Selected" Button

The "Open Selected" button opens checked listing URLs in the **mobile browser**
(i.e., the same browser tab/window the user is already using on their phone).
Do not use `window.open()` with `_blank` as mobile browsers may block this.
Instead, open URLs sequentially using a small delay:

```javascript
// Opens all checked listing URLs in the mobile browser, one after another.
// A short delay between opens prevents the browser from treating them as a popup burst.
document.getElementById('open-selected-btn').addEventListener('click', async () => {
    // Gather all checked checkboxes
    const checked = document.querySelectorAll('.listing-checkbox:checked');
    if (checked.length === 0) {
        alert('Please check at least one listing first.');
        return;
    }

    // Confirm if more than 5 items are selected (prevents accidental tab floods)
    if (checked.length > 5) {
        const confirmed = confirm(`Open ${checked.length} listings? This will open ${checked.length} tabs.`);
        if (!confirmed) return;
    }

    for (const checkbox of checked) {
        const url = checkbox.dataset.url;
        // Open in the current browser context (mobile-safe)
        window.open(url, '_blank', 'noopener,noreferrer');
        // Wait 300ms between opens to avoid popup blocking
        await new Promise(resolve => setTimeout(resolve, 300));
    }
});
```

### UI Requirements
- The "Open Selected" button must have `id="open-selected-btn"`.
- Each listing checkbox must have `class="listing-checkbox"` and
  `data-url="[listing URL]"`.
- A "Select All / Deselect All" toggle must be present above the list.
- The layout must be responsive (mobile-first CSS) so the checklist is usable
  on a phone screen without zooming.

---

## MANUAL STEPS (add all of the following to the project's MANUAL STEPS document)

```
NOTIFICATIONS SETUP — MANUAL STEPS

Step 1: Install Tailscale (one-time, required for phone access)
  a. Download Tailscale from https://tailscale.com/download
     - Install on your Windows computer
     - Install the Tailscale app on your Android phone
  b. Log in to the same Tailscale account on both devices.
  c. In the Tailscale admin panel (https://login.tailscale.com/admin/machines),
     find your computer's Tailscale IP address (format: 100.x.x.x).
  d. Add this IP to config.json under the key "tailscale_ip".
  e. From your phone's browser, navigate to http://[tailscale-ip]:5000
     to confirm connectivity before proceeding.

Step 2: Generate VAPID Keys (one-time)
  a. With the virtual environment active, run:
       python generate_vapid_keys.py
  b. Copy the two output values into config.json under the "vapid" key.
  c. Ensure config.json is listed in .gitignore — it must NOT be committed.

Step 3: Register Push Subscription (one-time per phone)
  a. On your Android phone, open Chrome and navigate to
       http://[tailscale-ip]:5000
  b. When the browser shows "Allow notifications?", tap Allow.
  c. The phone is now subscribed. Notifications will appear in the system
     tray after each scrape run that finds new listings.
  d. If you ever switch phones or clear Chrome's data, repeat this step.

Step 4: Set Up Windows Auto-Start (one-time)
  See TASK SCHEDULER SETUP section in Component 2 above.

Step 5: Confirm Everything Works
  a. With the app running, click "Run Scrape Now" in the web interface.
  b. Within 30 seconds, a notification should appear in your Android tray.
  c. Tap the notification — it should open the checklist in Chrome on your phone.
  d. Check two or three items and tap "Open Selected" — the listing URLs
     should open as new tabs.
```

---

## NOTES FOR CLAUDE CODE

- All six components above are mandatory. Do not skip any component on the
  grounds that it adds complexity.
- All significant lines of code must have a comment explaining what the line does.
- The MANUAL STEPS items above must be appended to the project's MANUAL STEPS
  document verbatim, with the project name substituted where indicated.
- `config.json` must be added to `.gitignore` before the first commit that
  includes VAPID key instructions.
- `subscriptions.json` must also be added to `.gitignore`.
- `jobs.sqlite` must also be added to `.gitignore`.
