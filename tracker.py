"""
ThinkPad Auction Tracker
Tracks used Lenovo ThinkPad listings on GovDeals (Maine + Massachusetts).

Usage:
    python tracker.py [--once | --loop MINUTES] [--no-email] [--no-push]
"""

import argparse
import sqlite3
import smtplib
import time
import yaml
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


DB_PATH = "thinkpads.db"


class CaptchaDetectedError(Exception):
    """Raised when a GovDeals response looks like a CAPTCHA or login wall."""


def load_config(path="config.yaml"):
    """Load configuration from YAML file."""
    with open(path, "r") as f:
        return yaml.safe_load(f)


def fetch_govdeals_listings(config):
    """
    Fetch current ThinkPad listings from GovDeals for configured states.
    Returns a list of dicts with keys:
        id, source, title, url, location, end_time, price, description

    TODO: Verify the search URL structure against live GovDeals HTML.
    TODO: Update CSS selectors (item container, title, price, location, end_time, link)
          to match the actual rendered HTML returned by GovDeals search pages.
    """
    listings = []
    base_url = config["govdeals"]["base_url"]
    states = config["govdeals"].get("states", [])
    min_price = float(config["govdeals"].get("min_price", 0.0))
    max_price = float(config["govdeals"].get("max_price", 9999.0))

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
    }

    for state in states:
        # TODO: Adjust search URL params to match GovDeals actual search endpoint
        search_url = (
            f"{base_url}/index.cfm?fa=Main.AdvSearchResultsNew"
            f"&searchPg=1&kWord=thinkpad&state={state}"
            f"&category=&sortBy=ad&Agency=0&sType=1&aucType="
            f"&pricelow=&pricehigh=&pgSize=96"
        )

        try:
            response = requests.get(search_url, headers=headers, timeout=15)
            response.raise_for_status()
        except requests.RequestException as e:
            print(f"[WARN] Failed to fetch GovDeals for state {state}: {e}")
            continue

        # Detect CAPTCHA or login wall by checking for known marker strings in the page
        page_lower = response.text.lower()
        if "captcha" in page_lower or "please log in" in page_lower or "access denied" in page_lower:
            raise CaptchaDetectedError(
                f"GovDeals returned a CAPTCHA or login wall for state {state}"
            )

        soup = BeautifulSoup(response.text, "html.parser")

        # TODO: Replace selector with the actual container element for each listing card
        items = soup.select("div.listingContainer, div.item-card, li.listing-item")

        for item in items:
            try:
                # TODO: Replace each selector below with the correct one from live HTML
                title_el = item.select_one("a.item-title, h3.listing-title, .title a")
                price_el = item.select_one(".current-bid, .price, .bid-amount")
                location_el = item.select_one(".location, .agency-location, .city-state")
                end_time_el = item.select_one(".end-time, .auction-end, .closes")
                link_el = item.select_one("a[href]")

                title = title_el.get_text(strip=True) if title_el else ""
                price_text = price_el.get_text(strip=True) if price_el else "0"
                location = location_el.get_text(strip=True) if location_el else state
                end_time = end_time_el.get_text(strip=True) if end_time_el else ""
                href = link_el["href"] if link_el else ""

                # Build absolute URL
                if href and not href.startswith("http"):
                    href = base_url.rstrip("/") + "/" + href.lstrip("/")

                # Parse price: strip currency symbols and commas
                price_str = price_text.replace("$", "").replace(",", "").strip()
                try:
                    price = float(price_str.split()[0]) if price_str else 0.0
                except ValueError:
                    price = 0.0

                # Skip listings outside configured price range
                if price < min_price or (max_price > 0 and price > max_price):
                    continue

                # TODO: Extract a stable listing ID; GovDeals typically uses itemnum= in URL
                if "itemnum=" in href:
                    listing_id = href.split("itemnum=")[-1].split("&")[0]
                else:
                    # TODO: Fall back to a different stable identifier from the page
                    listing_id = href

                if not listing_id or not title:
                    continue

                listings.append({
                    "id": f"govdeals-{listing_id}",
                    "source": "govdeals",
                    "title": title,
                    "url": href,
                    "location": location,
                    "end_time": end_time,
                    "price": price,
                    # TODO: Optionally fetch detail page for full description
                    "description": title,
                })
            except Exception as e:
                print(f"[WARN] Error parsing listing item: {e}")
                continue

    return listings


def filter_listings(listings, config):
    """
    Keep only listings that contain 'lenovo' or 'thinkpad' AND match a model token
    from the config.

    Fast path: brand check first (cheap string search).
    Then model token check.
    """
    models = [m.lower() for m in config.get("models", [])]
    filtered = []

    for listing in listings:
        combined = (
            listing.get("title", "") + " " + listing.get("description", "")
        ).lower()

        # Fast path: must include brand keyword
        if "lenovo" not in combined and "thinkpad" not in combined:
            continue

        # Require at least one model token match
        matched = [m for m in models if m in combined]
        if not matched:
            continue

        listing["matched_models"] = ",".join(matched)
        filtered.append(listing)

    return filtered


def _init_db(conn):
    """Create the listings table if it does not exist."""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS listings (
            id             TEXT PRIMARY KEY,
            source         TEXT,
            title          TEXT,
            url            TEXT,
            location       TEXT,
            end_time       TEXT,
            first_seen     TEXT,
            last_seen      TEXT,
            price          REAL,
            matched_models TEXT
        )
        """
    )
    conn.commit()


def upsert_listings(listings):
    """
    Insert new listings and update price/last_seen for existing ones in thinkpads.db.
    Returns (new_listings, updated_listings) and prints counts.
    """
    now = datetime.utcnow().isoformat()
    conn = sqlite3.connect(DB_PATH)
    _init_db(conn)

    new_listings = []
    updated_listings = []

    for listing in listings:
        existing = conn.execute(
            "SELECT id FROM listings WHERE id = ?", (listing["id"],)
        ).fetchone()

        if existing is None:
            conn.execute(
                """
                INSERT INTO listings
                    (id, source, title, url, location, end_time,
                     first_seen, last_seen, price, matched_models)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    listing["id"],
                    listing.get("source", ""),
                    listing.get("title", ""),
                    listing.get("url", ""),
                    listing.get("location", ""),
                    listing.get("end_time", ""),
                    now,
                    now,
                    listing.get("price", 0.0),
                    listing.get("matched_models", ""),
                ),
            )
            new_listings.append(listing)
        else:
            conn.execute(
                """
                UPDATE listings
                SET last_seen = ?, price = ?, matched_models = ?
                WHERE id = ?
                """,
                (
                    now,
                    listing.get("price", 0.0),
                    listing.get("matched_models", ""),
                    listing["id"],
                ),
            )
            updated_listings.append(listing)

    conn.commit()
    conn.close()

    print(f"[DB] New: {len(new_listings)}, Updated: {len(updated_listings)}")
    return new_listings, updated_listings


def send_email(new_listings, config, enabled=True):
    """
    Send a summary email for new listings.
    Does nothing when enabled=False, email disabled in config, or no new listings.
    """
    if not enabled:
        return
    if not config["email"].get("enabled", False):
        return
    if not new_listings:
        return

    lines = [f"New ThinkPad listings found ({len(new_listings)}):\n"]
    for listing in new_listings:
        lines.append(
            f"- **{listing['title']}** "
            f"(${listing['price']:.2f}, {listing['location']})\n"
            f"  {listing['url']}"
        )

    body = "\n".join(lines)
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"ThinkPad Tracker: {len(new_listings)} new listing(s)"
    msg["From"] = config["email"]["from_addr"]
    msg["To"] = config["email"]["to_addr"]
    msg.attach(MIMEText(body, "plain"))

    try:
        if config["email"].get("use_tls", True):
            smtp = smtplib.SMTP(config["email"]["smtp_host"], config["email"]["smtp_port"])
            smtp.starttls()
        else:
            smtp = smtplib.SMTP_SSL(
                config["email"]["smtp_host"], config["email"]["smtp_port"]
            )
        smtp.login(config["email"]["username"], config["email"]["password"])
        smtp.sendmail(
            config["email"]["from_addr"], config["email"]["to_addr"], msg.as_string()
        )
        smtp.quit()
        print(f"[EMAIL] Sent notification for {len(new_listings)} new listing(s).")
    except Exception as e:
        print(f"[EMAIL] Failed to send email: {e}")


def send_push(new_listings, config, enabled=True):
    """
    Send push notification (Pushover or ntfy) for new listings.
    Pushover: one notification with count + preview titles.
    ntfy: one POST per run with text body summary.
    Does nothing when enabled=False, push disabled in config, or no new listings.
    """
    if not enabled:
        return
    if not config["push"].get("enabled", False):
        return
    if not new_listings:
        return

    method = config["push"].get("method", "pushover")
    count = len(new_listings)
    preview_titles = ", ".join(l["title"][:40] for l in new_listings[:3])
    summary = f"{count} new ThinkPad(s): {preview_titles}"

    if method == "pushover":
        pushover_cfg = config["push"].get("pushover", {})
        payload = {
            "token": pushover_cfg.get("api_token", ""),
            "user": pushover_cfg.get("user_key", ""),
            "title": "ThinkPad Tracker Alert",
            "message": summary,
        }
        try:
            resp = requests.post(
                "https://api.pushover.net/1/messages.json", data=payload, timeout=10
            )
            resp.raise_for_status()
            print("[PUSH/Pushover] Notification sent.")
        except Exception as e:
            print(f"[PUSH/Pushover] Failed: {e}")

    elif method == "ntfy":
        ntfy_cfg = config["push"].get("ntfy", {})
        url = ntfy_cfg.get("url", "")
        try:
            resp = requests.post(url, data=summary.encode("utf-8"), timeout=10)
            resp.raise_for_status()
            print("[PUSH/ntfy] Notification sent.")
        except Exception as e:
            print(f"[PUSH/ntfy] Failed: {e}")

    else:
        print(f"[PUSH] Unknown push method: {method}")


def run_cycle(config, email_enabled, push_enabled):
    """Execute one poll + notify cycle. Returns (new_count, updated_count)."""
    ts = datetime.utcnow().isoformat()
    print(f"[{ts}] Polling GovDeals...")

    raw_listings = fetch_govdeals_listings(config)
    print(f"[INFO] Fetched {len(raw_listings)} raw listing(s).")

    matched = filter_listings(raw_listings, config)
    print(f"[INFO] {len(matched)} listing(s) matched ThinkPad model filter.")

    new_listings, updated_listings = upsert_listings(matched)

    send_email(new_listings, config, enabled=email_enabled)
    send_push(new_listings, config, enabled=push_enabled)

    print(f"[DONE] {len(new_listings)} new, {len(updated_listings)} updated.")
    return len(new_listings), len(updated_listings)


def parse_args():
    parser = argparse.ArgumentParser(
        description="ThinkPad auction tracker for GovDeals (ME + MA)."
    )

    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--once",
        action="store_true",
        default=True,
        help="Run one poll + notify cycle and exit (default).",
    )
    mode.add_argument(
        "--loop",
        metavar="INTERVAL_MINUTES",
        type=float,
        default=None,
        help="Run forever, sleeping INTERVAL_MINUTES between cycles.",
    )

    parser.add_argument(
        "--no-email",
        action="store_true",
        help="Disable email notifications for this run (overrides config).",
    )
    parser.add_argument(
        "--no-push",
        action="store_true",
        help="Disable push notifications for this run (overrides config).",
    )

    return parser.parse_args()


def main():
    args = parse_args()
    config = load_config()

    email_enabled = not args.no_email
    push_enabled = not args.no_push

    if args.loop is not None:
        interval_seconds = args.loop * 60
        print(f"[LOOP] Running every {args.loop} minute(s). Ctrl+C to stop.")
        cycle = 0
        while True:
            cycle += 1
            ts = datetime.utcnow().isoformat()
            print(f"\n=== Cycle #{cycle} at {ts} ===")
            new_count, updated_count = run_cycle(config, email_enabled, push_enabled)
            print(
                f"[SUMMARY] Cycle #{cycle}: {new_count} new, {updated_count} updated. "
                f"Next poll in {args.loop} min."
            )
            time.sleep(interval_seconds)
    else:
        run_cycle(config, email_enabled, push_enabled)


if __name__ == "__main__":
    main()
