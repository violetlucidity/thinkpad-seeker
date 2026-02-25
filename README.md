# ThinkPad Auction Tracker

A Python tool that monitors GovDeals government surplus auctions in Maine and
Massachusetts for used Lenovo ThinkPad laptops, stores new listings in a local
SQLite database, and optionally sends notifications via email and/or push
(Pushover or ntfy).

A companion script (`browser_opener.py`) opens Municibid and HiBid search pages
in your default browser for quick manual browsing — it does **not** scrape those
sites.

---

## Prerequisites

- Python 3.11 or later
- `pip` (bundled with Python)

---

## Setup

### 1. Clone or download the project

```bash
git clone https://github.com/youruser/thinkpad-seeker.git
cd thinkpad-seeker
```

### 2. Create and activate a virtual environment (Linux / macOS)

```bash
python -m venv .venv
source .venv/bin/activate
```

On Windows (PowerShell):

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Edit `config.yaml`

Open `config.yaml` and fill in the sections below.

#### `govdeals`

| Key | Description |
|-----|-------------|
| `enabled` | Set to `true` to enable GovDeals scraping. |
| `base_url` | Root URL for GovDeals (default: `https://www.govdeals.com`). |
| `states` | List of two-letter state codes to search (`ME`, `MA`, etc.). |
| `min_price` | Skip listings below this price (USD float). |
| `max_price` | Skip listings above this price (USD float, `0` = no limit). |

#### `models`

A list of ThinkPad model tokens (e.g., `X230`, `T440P`). Any listing whose
title or description contains one of these tokens (case-insensitive) *and* also
contains "lenovo" or "thinkpad" will be tracked.

#### `email`

| Key | Description |
|-----|-------------|
| `enabled` | `true` to send email on new listings. |
| `from_addr` | Sender address. |
| `to_addr` | Recipient address. |
| `smtp_host` | SMTP server hostname (e.g., `smtp.gmail.com`). |
| `smtp_port` | SMTP port (typically `587` for STARTTLS, `465` for SSL). |
| `username` | SMTP login username (usually your email address). |
| `password` | SMTP password or app-specific password. |
| `use_tls` | `true` for STARTTLS (port 587); `false` for SMTP_SSL (port 465). |

**Gmail tip:** Enable 2-factor authentication and generate an
[App Password](https://myaccount.google.com/apppasswords) to use as `password`.

#### `push`

| Key | Description |
|-----|-------------|
| `enabled` | `true` to send push notifications. |
| `method` | `"pushover"` or `"ntfy"`. |

**Pushover** (`push.pushover`):

- Register at [pushover.net](https://pushover.net/) and create an application.
- Copy the **API Token** into `api_token`.
- Copy your **User Key** into `user_key`.

**ntfy** (`push.ntfy`):

- Create a topic at [ntfy.sh](https://ntfy.sh/) (or self-host).
- Set `url` to `https://ntfy.sh/your_topic_name`.

---

## How to run

### Single poll (default)

```bash
python tracker.py --once
```

Fetches listings once, updates the database, sends notifications if new
listings are found, then exits.

### Continuous polling

```bash
python tracker.py --loop 180
```

Polls every 180 minutes (3 hours) indefinitely. Press Ctrl+C to stop.

### Disable notifications for one run

```bash
python tracker.py --once --no-email --no-push
```

### Open Municibid and HiBid browser tabs

```bash
python browser_opener.py
```

Opens the following pages in your default browser for manual browsing:

- **Municibid Maine** — Maine government surplus listings
- **HiBid New Hampshire** — NH laptops / consumer electronics

> **Note:** `browser_opener.py` does **not** scrape either site. It only calls
> `webbrowser.open_new_tab()` to open the URLs.

---

## Database

Listings are stored in `thinkpads.db` (SQLite) in the project directory.
Schema:

| Column | Type | Description |
|--------|------|-------------|
| `id` | TEXT PK | Stable listing ID (e.g., `govdeals-12345`) |
| `source` | TEXT | Data source (`govdeals`) |
| `title` | TEXT | Listing title |
| `url` | TEXT | Listing URL |
| `location` | TEXT | Seller location |
| `end_time` | TEXT | Auction end time (as scraped) |
| `first_seen` | TEXT | UTC ISO-8601 timestamp of first discovery |
| `last_seen` | TEXT | UTC ISO-8601 timestamp of last poll |
| `price` | REAL | Current bid/price in USD |
| `matched_models` | TEXT | Comma-separated matched model tokens |

---

## Terms of Service

GovDeals is a public government auction platform; please review their
[Terms of Use](https://www.govdeals.com/index.cfm?fa=Main.TOU) before running
the scraper at high frequency.

The Municibid and HiBid script (`browser_opener.py`) **does not scrape** either
website — it only opens URLs in your browser, the same as clicking a bookmark.
