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
from datetime import datetime        # For timestamping scrape runs

import yaml                          # PyYAML — reads the project's config.yaml
from flask import Flask, jsonify, render_template, request  # Flask web framework

# APScheduler — runs the scrape on a background thread, on a cron schedule
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore

# Import existing scraper functions from tracker.py (unchanged)
from tracker import load_config, run_cycle

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
    # Reload config on each run so schedule changes take effect without restart
    cfg = load_config("config.yaml")
    new_count, _ = run_cycle(cfg, email_enabled=True, push_enabled=True)
    # Notify subscribed phones how many new listings were found (Component 5)
    send_push_notifications(new_count)


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


def get_all_listings():
    """
    Reads all tracked listings from the SQLite database, newest first.
    Returns a list of dicts matching the listings table schema.
    """
    try:
        conn = sqlite3.connect(DB_PATH)      # open (or create) the database file
        conn.row_factory = sqlite3.Row       # makes rows accessible by column name
        rows = conn.execute(
            "SELECT * FROM listings ORDER BY first_seen DESC"
        ).fetchall()
        conn.close()
        return [dict(row) for row in rows]   # convert Row objects to plain dicts
    except sqlite3.OperationalError:
        # Table doesn't exist yet — no scrapes have run
        return []

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
    Expanded with pywebpush in Component 5.

    Args:
        new_count (int): Number of new listings found in this scrape run.
    """
    if new_count == 0:
        # Do not send a notification if no new listings were found
        return
    # Full implementation added in Step 6 (Component 5)
    print(f"[PUSH] {new_count} new listing(s) — push notifications will be sent once Component 5 is wired.")

# ── Flask routes ──────────────────────────────────────────────────────────────

@app.route('/')
def index():
    """
    Main page: renders the listing checklist for review.
    Reads all rows from the database and passes them to the template.
    """
    listings = get_all_listings()            # fetch all rows from thinkpads.db
    return render_template('index.html', listings=listings)


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
