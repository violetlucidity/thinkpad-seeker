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

### Files created
- `run.py` — new Flask application entry point; contains the `app` Flask variable,
  APScheduler initialization, `run_scrape()` wrapper, database helper, and stub
  push-notification helpers. Imports `load_config` and `run_cycle` from `tracker.py`
  without modifying that file.
- `templates/index.html` — main Jinja2 template; listing checklist UI with
  "Run Scrape Now", "Select All", and "Open Selected" buttons. All Component 6
  markup and JavaScript included here for completeness.
- `config.json.example` — standardized SAR config template with `schedule` block,
  `vapid` block, and `tailscale_ip` placeholder, per spec.
- `.gitignore` — created with entries for `jobs.sqlite`, `thinkpads.db`,
  `config.json`, and `subscriptions.json`.

### Files modified
- `requirements.txt` — added `flask>=3.0.0`, `apscheduler>=3.10.0`,
  `sqlalchemy>=2.0.0` (SQLAlchemy is required by APScheduler's SQLAlchemyJobStore).
- `config.yaml` — added `schedule:` block (days: tue,fri, hour: 8, minute: 0,
  timezone: America/New_York) per spec default values.

### Adaptation note
The project uses `config.yaml` (YAML) rather than `config.json` as its runtime
config. `run.py` reads `config.yaml` via PyYAML. `config.json.example` is
provided as required by the spec for documentation and portability purposes.

## STEP 3 — Windows Task Scheduler XML (Component 2)

### Files created
- `windows-task-scheduler.xml` — importable Task Scheduler entry that launches
  `run.py` via `pythonw.exe` at Windows logon. Contains inline XML comments
  marking the two paths that need manual substitution.
- `MANUAL STEPS.md` — new documentation file; initial content is the
  TASK SCHEDULER SETUP section from the spec (6 numbered steps).

## STEP 4 — PWA Manifest and Service Worker (Component 3)

### Files created
- `static/manifest.json` — PWA manifest; name: "ThinkPad Seeker",
  short_name: "TP Seeker", theme/background colors, two icon entries.
- `static/sw.js` — service worker handling `install`, `activate`, `push`, and
  `notificationclick` events, verbatim from spec with project-name comment.
- `static/icons/icon-192.png` — 192×192 placeholder icon (dark-blue background,
  white "TS" initials), generated via Pillow.
- `static/icons/icon-512.png` — 512×512 placeholder icon (same design).

### Files modified
- `templates/index.html` — added `<link rel="manifest">` and
  `<meta name="theme-color">` to `<head>`; replaced SW placeholder comment
  with the full `navigator.serviceWorker.register()` block from spec.
- `requirements.txt` — added `Pillow>=10.0.0` (used to generate icons).

## STEP 5 — Web Push Subscription Endpoint (Component 4)

### Files created
- `generate_vapid_keys.py` — one-time script that generates EC VAPID key pair
  and prints hex values for pasting into config.yaml.

### Files modified
- `run.py` — added `from pywebpush import webpush, WebPushException` import;
  added `/subscribe` POST route (stores subscription, deduplicates);
  added `/vapid-public-key` GET route (returns public key for browser).
  `load_subscriptions()` and `save_subscriptions()` were already present as
  stubs from Step 2 and are now wired to the routes.
- `templates/index.html` — added `requestPushPermission(registration)` and
  `hexStringToUint8Array(hexString)` functions to the `<script>` block,
  placed before the SW registration code that calls `requestPushPermission`.
- `requirements.txt` — added `pywebpush>=2.0.0`.
- `config.yaml` — added `vapid:` block with placeholder public/private key
  values and claims sub email.

### Already completed in earlier steps
- `config.json` in `.gitignore` — done in Step 2
- `subscriptions.json` in `.gitignore` — done in Step 2
- `vapid` block in `config.json.example` — done in Step 2

## STEP 6 — Push Notification on Scrape Completion (Component 5)
*(to be filled after Step 6 commit)*

## STEP 7 — Open Selected Button (Component 6)
*(to be filled after Step 7 commit)*

## STEP 8 — Notifications Manual Steps
*(to be filled after Step 8 commit)*

## STEP 9 — Final Verification
*(to be filled after Step 9 commit)*
