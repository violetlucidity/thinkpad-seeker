"""
browser_opener.py
Opens pre-configured auction search pages in the default web browser.
No scraping – only opens tabs.
"""

import webbrowser


URLS = [
    # Municibid – Maine government surplus auctions (active listings)
    "https://municibid.com/Browse/R3777816/Maine?ViewStyle=list&StatusFilter=active_only",
    # HiBid – New Hampshire laptops category
    "https://newhampshire.hibid.com/lots/computers---consumer-electronics---computers---laptops",
]


def open_tabs():
    for url in URLS:
        print(f"Opening: {url}")
        webbrowser.open_new_tab(url)


if __name__ == "__main__":
    open_tabs()
