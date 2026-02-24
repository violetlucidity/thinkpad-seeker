# ThinkPad Auction Tracker

A Python tool that monitors [GovDeals](https://www.govdeals.com) government surplus auctions in Maine and Massachusetts for used Lenovo ThinkPad laptops. When new matching listings appear it can notify you by email and/or push notification (Pushover or ntfy).

A companion script (`browser_opener.py`) opens Municibid and HiBid search pages in your browser for manual review — no scraping involved there.

---

## Prerequisites

- Python 3.11 or newer
- `pip` (comes with Python)

---

## Setup

### 1. Clone or download the project

```bash
git clone <repo-url>
cd thinkpad-tracker
```

### 2. Create and activate a virtual environment (Linux / macOS)

```bash
python -m venv .venv
source .venv/bin/activate
```

On Windows use `.venv\Scripts\activate` instead.

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Edit `config.yaml`

Open `config.yaml` and fill in the relevant sections:

#### `govdeals`

| Key | Description |
|-----|-------------|
| `enabled` | Set to `true` to scrape GovDeals |
| `base_url` | GovDeals root URL (default is correct) |
| `states` | List of two-letter state codes to search (e.g. `[ME, MA]`) |
| `min_price` | Skip listings below this price (USD) |
| `max_price` | Skip listings above this price (USD) |

#### `models`

List of ThinkPad model tokens to match (e.g. `X230`, `T430S`). The tracker checks that each title/description contains one of these tokens **and** includes "lenovo" or "thinkpad".

#### `email`

| Key | Description |
|-----|-------------|
| `enabled` | Set to `true` to send emails |
| `from_addr` | Sender email address |
| `to_addr` | Recipient email address |
| `smtp_host` | SMTP server hostname |
| `smtp_port` | SMTP port (587 for STARTTLS, 465 for SSL) |
| `username` | SMTP login username |
| `password` | SMTP login password |
| `use_tls` | `true` for STARTTLS (port 587); `false` for SSL (port 465) |

Gmail users: create an [App Password](https://myaccount.google.com/apppasswords) and use it as `password`.

#### `push`

| Key | Description |
|-----|-------------|
| `enabled` | Set to `true` to send push notifications |
| `method` | `"pushover"` or `"ntfy"` |

**Pushover** — register at [pushover.net](https://pushover.net), create an application to get an API token, and copy your user key:

```yaml
push:
  method: pushover
  pushover:
    api_token: "aAbBcCdDeEfF..."
    user_key: "uUvVwWxXyYzZ..."
```

**ntfy** — create a topic at [ntfy.sh](https://ntfy.sh) (or self-host) and set the URL:

```yaml
push:
  method: ntfy
  ntfy:
    url: "https://ntfy.sh/my-secret-topic"
```

---

## How to run

### Single poll (run once and exit)

```bash
python tracker.py --once
```

### Continuous polling every 3 hours

```bash
python tracker.py --loop 180
```

### Suppress notifications for one run

```bash
python tracker.py --once --no-email --no-push
```

### Open Municibid and HiBid in your browser

```bash
python browser_opener.py
```

This opens two browser tabs:

- **Municibid Maine** — Maine government surplus auctions (active listings)
- **HiBid New Hampshire** — laptops and consumer electronics category

---

## Running as a background service

See [`thinkpad-tracker.service`](thinkpad-tracker.service) for a systemd unit file that runs the tracker continuously on a Linux server.

---

## Notes on Terms of Service

- The GovDeals scraper sends standard HTTP requests to public search pages.
  Review GovDeals' [Terms of Use](https://www.govdeals.com/index.cfm?fa=Main.Terms) before running in production and add reasonable poll intervals (60+ minutes recommended).
- `browser_opener.py` does **not** scrape Municibid or HiBid — it only opens their public search pages in your default browser, the same as clicking a bookmark.

---

## Project structure

```
thinkpad-tracker/
├── config.yaml          # All configuration (edit this)
├── requirements.txt     # Python dependencies
├── tracker.py           # Main tracker + CLI
├── browser_opener.py    # Opens Municibid/HiBid tabs
├── thinkpad-tracker.service  # systemd unit (optional)
└── thinkpads.db         # SQLite database (created on first run)
```
