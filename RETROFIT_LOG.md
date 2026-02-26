# RETROFIT LOG — ThinkPad Seeker
# SAR Notifications Infrastructure Retrofit
# Tracking all changes made during the notifications retrofit.

---

## STEP 1 — Audit Results (pre-retrofit baseline)

**Date audited:** 2026-02-26

### Entry point
| Item | Finding |
|------|---------|
| Main entry point file | `tracker.py` (CLI tool — **no Flask app exists yet**) |
| Scrape orchestration function | `run_cycle(config, email_enabled, push_enabled)` in `tracker.py` |
| Flask app variable | **NONE** — no Flask application exists in the project |
| Main HTML template | **NONE** — no `templates/` directory exists |
| Main JS file / `<script>` block | **NONE** — no JavaScript files exist |

### Configuration and dependencies
| Item | Finding |
|------|---------|
| `requirements.txt` | EXISTS at repo root — contains 3 packages: `requests`, `PyYAML`, `beautifulsoup4` |
| `config.yaml` | EXISTS at repo root — project's runtime config (YAML format, not JSON) |
| `config.json` | **DOES NOT EXIST** |
| `config.json.example` | **DOES NOT EXIST** |
| APScheduler | **NOT present** in requirements.txt or any source file |
| `.gitignore` | **DOES NOT EXIST** |

### Existing Python files
- `tracker.py` — main CLI: load_config, fetch_govdeals_listings, filter_listings,
  upsert_listings, send_email, send_push, run_cycle, main
- `browser_opener.py` — opens Municibid/HiBid tabs in default browser, no scraping

### Retrofit implications
Because no Flask app, HTML template, or JavaScript exists, the retrofit will:
1. Create `run.py` as the new Flask application entry point.
2. Import existing functions from `tracker.py` unchanged.
3. Create `templates/index.html` with the listing review UI.
4. Create `static/` directory for PWA assets.
5. The existing `tracker.py` CLI remains fully functional.
6. Project uses `config.yaml` (not JSON); `config.json.example` will be created
   per spec, and runtime config reads will use `config.yaml` via PyYAML.

---

## STEP 2 — APScheduler (Component 1)
*(to be filled after Step 2 commit)*

## STEP 3 — Windows Task Scheduler XML (Component 2)
*(to be filled after Step 3 commit)*

## STEP 4 — PWA Manifest and Service Worker (Component 3)
*(to be filled after Step 4 commit)*

## STEP 5 — Web Push Subscription Endpoint (Component 4)
*(to be filled after Step 5 commit)*

## STEP 6 — Push Notification on Scrape Completion (Component 5)
*(to be filled after Step 6 commit)*

## STEP 7 — Open Selected Button (Component 6)
*(to be filled after Step 7 commit)*

## STEP 8 — Notifications Manual Steps
*(to be filled after Step 8 commit)*

## STEP 9 — Final Verification
*(to be filled after Step 9 commit)*
