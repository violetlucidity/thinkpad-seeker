"""
run.py — ThinkPad Seeker web application entry point.

Starts a Flask web server that:
  - Shows all tracked listings from the SQLite database.
  - Provides a "Run Scrape Now" button for on-demand scraping.
  - Runs APScheduler in a background thread for automatic scheduled scrapes.
  - Serves push-notification subscription endpoints (added in Component 4).

Usage:
    python run.py
Then open http://localhost:5000 in your browser (or phone via Tailscale).
"""

import json                          # Standard JSON parsing for config and push payloads
import sqlite3                       # Standard SQLite library for reading listings
import sys                           # For inserting the ntfy-monitor path (Component 5)
from datetime import datetime        # For timestamping scrape runs

import yaml                          # PyYAML — reads the project's config.yaml
from flask import Flask, jsonify, render_template, request  # Flask web framework
from pywebpush import webpush, WebPushException  # Web Push delivery (Component 4)

# APScheduler — runs the scrape on a background thread, on a cron schedule
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore

# ntfy-monitor integration (Component 5) — path to the ntfy-monitor repo
# The notify module provides success(), error(), and manual_step() helpers
sys.path.insert(0, '../ntfy-monitor')   # adjust this path if the repo lives elsewhere
try:
    import notify                        # ntfy-monitor notify module
    _NOTIFY_AVAILABLE = True             # flag used to guard notify calls below
except ImportError:
    _NOTIFY_AVAILABLE = False            # ntfy-monitor not installed — calls are skipped
    print("[WARN] ntfy-monitor not found at ../ntfy-monitor; ntfy notifications disabled.")

# Import existing scraper functions from tracker.py (unchanged)
from tracker import load_config, run_cycle, CaptchaDetectedError

# ── Flask application ─────────────────────────────────────────────────────────

app = Flask(__name__)                # Create the Flask app; templates/ and static/ are auto-discovered

# ── Configuration ─────────────────────────────────────────────────────────────

# Load the project's existing YAML config (tracker settings, email, push, etc.)
config = load_config("config.yaml")

# ── APScheduler setup (Component 1) ──────────────────────────────────────────

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


def run_scrape():
    """
    Zero-argument wrapper called by APScheduler on the cron schedule.
    Delegates to run_cycle() from tracker.py with notifications enabled.
    """
    try:
        # Reload config on each run so schedule changes take effect without restart
        cfg = load_config("config.yaml")
        new_count, _ = run_cycle(cfg, email_enabled=True, push_enabled=True)
        # Notify subscribed phones how many new listings were found (Component 5)
        send_push_notifications(new_count)
        # Send ntfy success notification so the operator knows the scrape completed
        if _NOTIFY_AVAILABLE:
            notify.success(
                f"{new_count} new listing(s) found.",   # result summary
                project="ThinkPad Seeker"               # project label shown in ntfy message
            )
    except CaptchaDetectedError:
        # GovDeals returned a CAPTCHA or login wall — human intervention required
        print("[WARN] CAPTCHA or login wall detected on GovDeals.")
        if _NOTIFY_AVAILABLE:
            notify.manual_step(
                "Manual action required — check the scraper.",  # action description
                project="ThinkPad Seeker"                       # project label
            )
    except Exception as e:
        # Unexpected scrape failure — send an error notification so we know it broke
        print(f"[ERROR] Scrape failed: {e}")
        if _NOTIFY_AVAILABLE:
            notify.error(
                f"Scrape failed: {str(e)}",  # include the exception message
                project="ThinkPad Seeker"    # project label shown in ntfy message
            )


# Read schedule from config; fall back to Tue/Fri 08:00 if not set
schedule_cfg = config.get(
    'schedule', {'days': 'tue,fri', 'hour': 8, 'minute': 0}
)

scheduler.add_job(
    run_scrape,                              # the function to call
    trigger='cron',
    day_of_week=schedule_cfg['days'],        # e.g. 'tue,fri'
    hour=schedule_cfg['hour'],               # local time hour (24-hour)
    minute=schedule_cfg['minute'],           # local time minute
    id='scrape_job',
    replace_existing=True                    # prevents duplicate jobs on restart
)

scheduler.start()                            # starts the scheduler thread alongside Flask

# ── Database helper ───────────────────────────────────────────────────────────

DB_PATH = "thinkpads.db"                     # same path used by tracker.py


def _ensure_bookmark_column():
    """
    Adds a 'bookmarked' column to the listings table if it doesn't exist yet.
    Safe to call on every startup — the ALTER TABLE is silently ignored when
    the column is already present (SQLite raises OperationalError in that case).
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute(
            "ALTER TABLE listings ADD COLUMN bookmarked INTEGER DEFAULT 0"
        )
        conn.commit()
        conn.close()
    except sqlite3.OperationalError:
        pass   # column already exists — nothing to do


# Run the migration immediately at startup so the column is always present
_ensure_bookmark_column()


def get_all_listings():
    """
    Reads all tracked listings from the SQLite database.
    Returns (bookmarked, rest) — two separate lists so the template can
    display bookmarked entries in their own section at the top.
    Bookmarked list is ordered by title; the rest are newest-first.
    """
    try:
        conn = sqlite3.connect(DB_PATH)      # open (or create) the database file
        conn.row_factory = sqlite3.Row       # makes rows accessible by column name
        # Bookmarked listings — shown pinned at the top of the page
        bookmarked = [dict(r) for r in conn.execute(
            "SELECT * FROM listings WHERE bookmarked = 1 ORDER BY title"
        ).fetchall()]
        # All other listings — newest first
        rest = [dict(r) for r in conn.execute(
            "SELECT * FROM listings WHERE bookmarked = 0 ORDER BY first_seen DESC"
        ).fetchall()]
        conn.close()
        return bookmarked, rest
    except sqlite3.OperationalError:
        # Table doesn't exist yet — no scrapes have run
        return [], []

# ── Push notification helpers (Component 4 / 5 stubs — expanded later) ───────

SUBSCRIPTIONS_FILE = 'subscriptions.json'    # persisted push subscription store


def load_subscriptions():
    """Load push subscriptions from disk. Returns empty list if file missing."""
    try:
        with open(SUBSCRIPTIONS_FILE) as f:  # open subscriptions file for reading
            return json.load(f)
    except FileNotFoundError:
        return []                            # no subscriptions yet — that's fine


def save_subscriptions(subs):
    """Persist push subscriptions to disk."""
    with open(SUBSCRIPTIONS_FILE, 'w') as f:   # overwrite file with updated list
        json.dump(subs, f, indent=2)


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

    subs = load_subscriptions()            # load all registered phone subscriptions
    if not subs:
        print("No push subscriptions registered. Open the app on your phone first.")
        return

    # Build the notification payload as a JSON string
    payload = json.dumps({
        "title": "New listings ready",                                  # notification title
        "body": f"{new_count} new item{'s' if new_count != 1 else ''} found. Tap to review.",  # body text
        "url": "/"                                                      # opens the checklist when tapped
    })

    vapid_cfg = config.get('vapid', {})    # read VAPID credentials from config

    for subscription in list(subs):        # iterate over a copy so we can remove expired subs
        try:
            webpush(
                subscription_info=subscription,                         # the browser's subscription object
                data=payload,                                           # JSON payload string
                vapid_private_key=vapid_cfg.get('private_key', ''),    # server's VAPID private key
                vapid_claims=vapid_cfg.get('claims', {})               # claims dict including sub email
            )
        except WebPushException as e:
            # If a subscription is expired or invalid (HTTP 410 Gone), remove it from the store
            if e.response and e.response.status_code == 410:
                print(f"Subscription expired, removing: {subscription.get('endpoint','')[:40]}...")
                subs.remove(subscription)    # drop the dead subscription from the list
                save_subscriptions(subs)     # persist the updated list immediately
            else:
                print(f"Push failed: {e}")   # log other errors without removing the subscription

# ── Web Push subscription routes (Component 4) ───────────────────────────────

@app.route('/subscribe', methods=['POST'])
def subscribe():
    """
    Receives a Web Push subscription object from the browser.
    Stores it so the server can send push notifications to this device.
    """
    subscription = request.get_json()      # parse the JSON body sent by the browser
    subs = load_subscriptions()            # load existing subscriptions from disk

    # Avoid storing duplicate subscriptions from the same device
    if subscription not in subs:
        subs.append(subscription)          # add the new subscription to the list
        save_subscriptions(subs)           # persist the updated list to disk

    return jsonify({'status': 'subscribed'}), 201   # 201 Created


@app.route('/vapid-public-key', methods=['GET'])
def vapid_public_key():
    """Returns the VAPID public key to the browser for push subscription setup."""
    # The browser needs this key to identify our server as the authorised sender
    return jsonify({'publicKey': config.get('vapid', {}).get('public_key', '')})

# ── Flask routes ──────────────────────────────────────────────────────────────

@app.route('/')
def index():
    """
    Main page: renders the listing checklist for review.
    Passes bookmarked and regular listings separately so the template can
    display them in two distinct sections.
    """
    bookmarked, listings = get_all_listings()   # split into pinned and regular
    return render_template('index.html', bookmarked=bookmarked, listings=listings)


@app.route('/bookmark', methods=['POST'])
def toggle_bookmark():
    """
    Toggles the bookmarked state for a single listing.
    Expects JSON body: {"id": "<listing-id>", "bookmarked": true|false}
    Returns the new state so the client can update the UI without a reload.
    """
    data = request.get_json()                        # parse the JSON request body
    listing_id = data.get('id', '')                  # stable listing ID (e.g. govdeals-12345)
    new_state = 1 if data.get('bookmarked') else 0   # convert bool to SQLite integer

    try:
        conn = sqlite3.connect(DB_PATH)              # open the database
        conn.execute(
            "UPDATE listings SET bookmarked = ? WHERE id = ?",
            (new_state, listing_id)                  # parameterised query — no SQL injection
        )
        conn.commit()
        conn.close()
        return jsonify({'status': 'ok', 'id': listing_id, 'bookmarked': bool(new_state)})
    except sqlite3.Error as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/run-scrape', methods=['POST'])
def trigger_scrape():
    """
    On-demand scrape endpoint. Called by the "Run Scrape Now" button.
    Runs synchronously and returns a JSON result.
    """
    try:
        cfg = load_config("config.yaml")                 # fresh config each time
        new_count, updated_count = run_cycle(            # run one poll + notify cycle
            cfg, email_enabled=True, push_enabled=True
        )
        send_push_notifications(new_count)               # push to subscribed phones
        return jsonify({
            'status': 'ok',
            'new': new_count,
            'updated': updated_count,
            'timestamp': datetime.utcnow().isoformat()  # UTC ISO-8601 timestamp
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


# ── Application entry point ───────────────────────────────────────────────────

if __name__ == '__main__':
    # host='0.0.0.0' makes the app reachable from your phone over Tailscale
    app.run(host='0.0.0.0', port=5000, debug=False)
