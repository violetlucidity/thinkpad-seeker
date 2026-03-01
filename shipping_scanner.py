"""
shipping_scanner.py — GovDeals nationwide ThinkPad shipping scanner.

Searches GovDeals for "thinkpad" across all US states, fetches each listing's
detail page concurrently, and classifies whether the seller ships or requires
local pickup only.

Designed to be imported by run.py (web UI) or run directly from the CLI:
    python shipping_scanner.py
"""

import json                          # for saving/loading cached results
from concurrent.futures import ThreadPoolExecutor, as_completed  # parallel fetches
from datetime import datetime, timezone   # UTC timestamps on scan results

import requests                      # HTTP client
from bs4 import BeautifulSoup        # HTML parser

# ── Shipping keyword lists ────────────────────────────────────────────────────
# These phrases are matched case-insensitively against the full listing page text.
# Negative phrases are checked first and always win if both positive and negative appear.

# Phrases that strongly indicate the seller WILL ship the item.
SHIPS_PHRASES = [
    'will ship',
    'shipping available',
    'shipping is available',
    'can ship',
    'able to ship',
    'we ship',
    'buyer pays shipping',
    'buyer pays for shipping',
    'plus shipping',
    'shipping cost',
    'shipping fee',
    'shipping charges',
    'ships to',
    'shipped to',
    'fedex',
    'usps',
    'ups pickup',           # UPS as a carrier (not the verb "ups")
    'freight available',
    'delivery available',
    'remote bidder',        # GovDeals term sometimes used for shippable items
    'remote buyers',
    'ship at buyer',
    'shipping upon request',
]

# Phrases that indicate the seller will NOT ship — local pickup only.
# These take priority; a listing with both positive and negative is classified 'no_ship'.
NO_SHIP_PHRASES = [
    'no shipping',
    'no ship',
    'will not ship',
    'will not be shipped',
    'cannot ship',
    "can't ship",
    'not available for shipping',
    'does not ship',
    'pickup only',
    'pick up only',
    'pick-up only',
    'local pickup',
    'local pick up',
    'local pick-up',
    'must be picked up',
    'must pick up',
    'in-person pickup',
    'in person only',
    'on-site pickup',
    'onsite pickup',
    'no delivery',
    'buyer must remove',
    'buyer responsible for removal',
    'removal only',
    'no remote',
    'cash and carry',
]

# Default HTTP headers — mimic a real browser to avoid being blocked
_HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 '
        '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    )
}


# ── Core detection logic ──────────────────────────────────────────────────────

def detect_shipping(text):
    """
    Scans listing text for shipping-related keywords.

    Negative phrases are checked first and take priority — a listing that says
    "pickup only but will consider shipping" is still classified 'no_ship'.

    Args:
        text: Full plain-text content of the listing page.

    Returns:
        (status, evidence) where status is 'ships', 'no_ship', or 'unknown',
        and evidence is the matched phrase (empty string when unknown).
    """
    lower = text.lower()                      # case-insensitive matching throughout

    for phrase in NO_SHIP_PHRASES:            # check negative phrases first
        if phrase in lower:
            return 'no_ship', phrase          # explicit refusal found — stop here

    for phrase in SHIPS_PHRASES:             # then check positive phrases
        if phrase in lower:
            return 'ships', phrase            # explicit offer to ship found

    return 'unknown', ''                      # no shipping mention either way


# ── Network helpers ───────────────────────────────────────────────────────────

def fetch_listing_detail(url, timeout=10):
    """
    Fetches an individual GovDeals listing page and returns its plain text.

    Returns empty string on any network or parse error so the caller can
    classify the listing as 'unknown' rather than crashing the scan.

    TODO: Verify the CSS selector against live GovDeals listing HTML.
          Candidates: '#itemDescription', '.lot-description', '.item-desc'
    """
    try:
        resp = requests.get(url, headers=_HEADERS, timeout=timeout)
        resp.raise_for_status()                   # raise on 4xx / 5xx responses
        soup = BeautifulSoup(resp.text, 'html.parser')

        # TODO: Replace with the real description container selector from live HTML
        desc_el = soup.select_one(
            '#itemDescription, .lot-description, .item-desc, .description-body, '
            '.tab-content, #tabItemDesc'
        )
        if desc_el:
            return desc_el.get_text(' ', strip=True)   # extract text from description block

        # Fall back to the whole page if no description element matched
        return soup.get_text(' ', strip=True)
    except Exception:
        return ''                                  # swallow errors; caller treats '' as 'unknown'


def fetch_search_page(base_url, page, timeout=15):
    """
    Fetches one page of GovDeals search results for 'thinkpad' with no state filter.

    Returns a list of listing dicts: {id, title, url, price, location}.
    Returns empty list on network error or when no results are found.

    TODO: Verify the search URL query-string parameters against the live GovDeals site.
    TODO: Replace the CSS selectors below with the actual ones from live GovDeals HTML.
    """
    # state= left empty to search all US states (not just ME and MA like the main tracker)
    search_url = (
        f"{base_url}/index.cfm?fa=Main.AdvSearchResultsNew"
        f"&searchPg={page}&kWord=thinkpad&state="
        f"&category=&sortBy=ad&Agency=0&sType=1&aucType="
        f"&pricelow=&pricehigh=&pgSize=96"
    )

    try:
        resp = requests.get(search_url, headers=_HEADERS, timeout=timeout)
        resp.raise_for_status()
    except Exception as e:
        print(f"[SCAN] Search page {page} failed: {e}")
        return []

    soup = BeautifulSoup(resp.text, 'html.parser')

    # TODO: Replace with the actual listing card container selector from live GovDeals HTML
    items = soup.select('div.listingContainer, div.item-card, li.listing-item')

    listings = []
    for item in items:
        try:
            # TODO: Replace each selector below with the correct one from live HTML
            title_el = item.select_one('a.item-title, h3.listing-title, .title a')
            price_el = item.select_one('.current-bid, .price, .bid-amount')
            loc_el   = item.select_one('.location, .agency-location, .city-state')
            link_el  = item.select_one('a[href]')

            title    = title_el.get_text(strip=True) if title_el else ''
            price_raw = price_el.get_text(strip=True) if price_el else '0'
            location = loc_el.get_text(strip=True)   if loc_el   else ''
            href     = link_el['href']                if link_el  else ''

            # Make relative URLs absolute
            if href and not href.startswith('http'):
                href = base_url.rstrip('/') + '/' + href.lstrip('/')

            # Parse price: strip $ and commas, take first token
            price_str = price_raw.replace('$', '').replace(',', '').strip()
            try:
                price = float(price_str.split()[0]) if price_str else 0.0
            except ValueError:
                price = 0.0

            # Extract stable listing ID from the URL query string
            if 'itemnum=' in href:
                listing_id = href.split('itemnum=')[-1].split('&')[0]
            else:
                listing_id = href          # fall back to full URL as ID

            if not listing_id or not title or not href:
                continue                   # skip malformed / empty rows

            listings.append({
                'id':       f'scan-{listing_id}',   # prefix avoids collision with tracker IDs
                'title':    title,
                'url':      href,
                'price':    price,
                'location': location,
            })
        except Exception:
            continue                       # skip individual parse errors silently

    return listings


# ── Main scan function ────────────────────────────────────────────────────────

def run_scan(config, max_results=96, workers=10, progress_cb=None):
    """
    Full shipping scan: searches GovDeals nationally for ThinkPad listings,
    then fetches each listing detail page and classifies shipping status.

    Args:
        config:      Parsed config.yaml dict (needs govdeals.base_url).
        max_results: Maximum number of listings to classify (default: 96, one page).
        workers:     Concurrent HTTP workers for detail-page fetching (default: 10).
        progress_cb: Optional callable(done, total) called after each listing finishes.

    Returns:
        List of result dicts sorted ships-first, unknown-middle, no_ship-last.
        Each dict: {id, title, url, price, location, ships, evidence, scanned_at}
    """
    base_url = config['govdeals']['base_url']   # e.g. https://www.govdeals.com

    # Step 1 — collect listings from search results pages (fetch up to 2 pages)
    all_listings = []
    for page in range(1, 3):                    # pages 1 and 2 (up to 192 raw results)
        page_results = fetch_search_page(base_url, page)
        all_listings.extend(page_results)
        if not page_results:
            break                               # stop early if a page returned nothing
        if len(all_listings) >= max_results:
            break                               # stop once we have enough

    listings = all_listings[:max_results]       # cap at the requested limit
    total = len(listings)
    print(f"[SCAN] {total} listings to process.")

    # Shared counter — incremented inside worker threads.
    # Safe without a lock because the GIL serialises integer increments in CPython.
    done_count = [0]

    # Step 2 — fetch each listing detail page and classify shipping, in parallel
    def process_one(listing):
        """Worker: fetches one listing page and returns an annotated result dict."""
        text = fetch_listing_detail(listing['url'])       # get the page text
        status, evidence = detect_shipping(text)          # classify shipping status
        done_count[0] += 1                                # track progress
        if progress_cb:
            progress_cb(done_count[0], total)             # notify caller
        label = status.upper().ljust(8)
        print(f"[SCAN] {done_count[0]}/{total} {label} {listing['title'][:55]}")
        return {
            **listing,                                    # pass through all search fields
            'ships':      status,                         # 'ships', 'no_ship', 'unknown'
            'evidence':   evidence,                       # the keyword phrase that matched
            'scanned_at': datetime.now(timezone.utc).isoformat(),   # UTC scan timestamp
        }

    results = []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(process_one, lst): lst for lst in listings}
        for future in as_completed(futures):
            try:
                results.append(future.result())
            except Exception as e:
                print(f"[SCAN] Worker error: {e}")        # log but don't abort the scan

    # Sort: shippable first → unknown → no_ship
    order = {'ships': 0, 'unknown': 1, 'no_ship': 2}
    results.sort(key=lambda r: order.get(r['ships'], 1))

    return results


# ── CLI entry point ───────────────────────────────────────────────────────────

if __name__ == '__main__':
    import yaml                                           # only needed for CLI usage

    with open('config.yaml') as f:
        cfg = yaml.safe_load(f)                           # load the project config

    print("Starting shipping scan (this may take 30–60 seconds)…\n")
    results = run_scan(cfg)

    # Print a plain-text summary table to stdout
    print(f"\n{'STATUS':<10} {'PRICE':>7}  {'LOCATION':<25}  TITLE")
    print('-' * 90)
    for r in results:
        status_label = {'ships': 'SHIPS', 'no_ship': 'NO SHIP', 'unknown': 'UNKNOWN'}
        print(
            f"{status_label.get(r['ships'], '?'):<10}"
            f" ${r['price']:>6.0f}"
            f"  {r['location'][:24]:<24}"
            f"  {r['title'][:50]}"
        )
        if r['evidence']:
            print(f"{'':>10}   ↳ matched: \"{r['evidence']}\"")
        print(f"{'':>10}   {r['url']}")
