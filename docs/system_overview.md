# Product Recall Web Scraping System - Technical Documentation

## 1. Project Overview

This system is an automated web scraping pipeline that monitors multiple U.S. government and legal websites for product recall announcements. It collects new recall URLs, de-duplicates them against previously seen records, and sends consolidated email notifications to the team.

### Data Sources

| Source | Website | Description |
|--------|---------|-------------|
| **CPSC** | cpsc.gov/Recalls | U.S. Consumer Product Safety Commission |
| **FDA** | fda.gov/safety/recalls-market-withdrawals-safety-alerts | U.S. Food and Drug Administration |
| **FSIS** | fsis.usda.gov/recalls | USDA Food Safety and Inspection Service |
| **Scout** | ld.scoutyourcase.com/index | Legal case listings filtered for product recalls |

---

## 2. System Architecture

```
                        +------------------+
                        |    main.py       |
                        | (UnifiedScraper) |
                        +--------+---------+
                                 |
            +--------------------+--------------------+--------------------+
            |                    |                    |                    |
   +--------v-------+  +--------v-------+  +--------v-------+  +--------v---------+
   | CPSC Scraper   |  | FDA Scraper    |  | FSIS Scraper   |  | Scout Scraper    |
   | (Selenium)     |  | (Selenium +    |  | (Selenium)     |  | (Undetected      |
   |                |  |  DataTables)   |  |                |  |  ChromeDriver)   |
   +--------+-------+  +--------+-------+  +--------+-------+  +--------+---------+
            |                    |                    |                    |
            v                    v                    v                    v
   cpsc_seen_urls.json  fda_seen_urls.json  fsis_seen_urls.json  scoutyourcase_seen_urls.json
            |                    |                    |                    |
            +--------------------+--------------------+--------------------+
                                 |
                        +--------v---------+
                        | Merge New URLs   |
                        +--------+---------+
                                 |
                        +--------v---------+
                        | EmailNotifier    |
                        | (notifier.py)    |
                        +--------+---------+
                                 |
                                 v
                        Consolidated Digest Email
```

---

## 3. File Structure

```
Product-Recall-Web-Scraping/
|
+-- main.py                          # Main orchestrator - runs all scrapers and sends email
+-- cpsc_links_scraper.py            # CPSC recall scraper
+-- fda_selenium_scraper.py          # FDA recall scraper
+-- fsis_selenium_scraper.py         # FSIS recall scraper
+-- scoutyourcase_productrecall_scraper.py  # Scout case scraper
+-- notifier.py                      # Email notification module
+-- batch_notifier.py                # Batch email module (optional, currently disabled)
+-- scraper_config.json              # Primary configuration file (credentials + settings)
+-- requirements.txt                 # Python dependencies
+-- run_product_recall.sh            # Shell script for Linux cron scheduling
+-- scraper.log                      # Main application log
+-- cpsc_links_scraper.log           # CPSC scraper detailed log
|
+-- data/
|   +-- seen/                        # De-duplication state (previously seen URLs)
|   |   +-- cpsc_seen_urls.json
|   |   +-- fda_seen_urls.json
|   |   +-- fsis_seen_urls.json
|   |   +-- scoutyourcase_seen_urls.json
|   +-- progress/
|   |   +-- batch_progress.json      # Batch notification progress tracker
|   +-- chrome_profiles/scout/       # Persistent browser profile for Scout scraper
|
+-- docs/                            # Documentation
```

---

## 4. How Each Component Works

### 4.1 main.py - The Orchestrator

This is the entry point of the system. It contains the `UnifiedScraper` class which:

1. **Loads configuration** from `scraper_config.json` (credentials, scraper flags, page limits)
2. **Sets up logging** to both `scraper.log` and the console
3. **Sets up the Linux display server** (Xvfb) if running on a headless Linux VPS
4. **Runs each scraper sequentially**: CPSC, FDA, FSIS, Scout
5. **Aggregates results** from all scrapers into a combined URL list
6. **Sends a single digest email** with all new recall URLs

**Command-line options:**
- `python main.py` - Normal run (scrape all sources and send email)
- `python main.py --test-email` - Test email configuration only
- `python main.py --help` - Show usage

### 4.2 cpsc_links_scraper.py - CPSC Scraper

- **Target:** CPSC.gov recall listing pages
- **Method:** Uses Selenium WebDriver with Chrome in headless mode
- **Pagination:** Navigates through multiple listing pages (default: up to 10 pages)
- **Link extraction:** Uses multiple CSS selectors to find recall URLs on each page
- **De-duplication:** Loads `data/seen/cpsc_seen_urls.json` at startup, compares new links against it, and saves the updated set after scraping
- **Output:** Returns only the newly discovered URLs

### 4.3 fda_selenium_scraper.py - FDA Scraper

- **Target:** FDA safety recalls page which uses a DataTables-based listing
- **Method:** Selenium with explicit waits for the DataTables JavaScript library to fully render
- **Driver setup:** Uses a 3-method fallback for ChromeDriver initialization (system binary, `chromedriver_autoinstaller`, `webdriver_manager`)
- **Pagination:** Interacts with DataTables pagination controls (default: up to 115 pages)
- **Performance:** Disables image loading in Chrome for faster page loads
- **De-duplication:** Same pattern as CPSC using `data/seen/fda_seen_urls.json`

### 4.4 fsis_selenium_scraper.py - FSIS Scraper

- **Target:** USDA FSIS recall alerts
- **Method:** Selenium with XPath selectors
- **Pagination:** Looks for a "Next" pager link
- **Page limit:** Configurable via `FSIS_MAX_PAGES` in config (default: 3)
- **De-duplication:** Uses `data/seen/fsis_seen_urls.json`

### 4.5 scoutyourcase_productrecall_scraper.py - Scout Scraper

- **Target:** ScoutYourCase legal case listings
- **Method:** Uses `undetected_chromedriver` to handle anti-bot detection on the site
- **Dynamic loading:** Repeatedly clicks a "More Cases" button to load additional listings (up to `SCOUT_MAX_PAGES` clicks)
- **Keyword filtering:** Only collects URLs whose text matches recall-related keywords (e.g., "product recall", "recall notice", "safety recall")
- **Browser profile:** Stores a persistent Chrome profile in `data/chrome_profiles/scout/` to maintain cookies across runs
- **De-duplication:** Uses `data/seen/scoutyourcase_seen_urls.json`

### 4.6 notifier.py - Email Notification

The `EmailNotifier` class handles sending email notifications:

1. **Loads credentials** from the `scraper_config.json` secret file by reading its path defined in the code (`CONFIG_PATH = os.path.join(BASE_DIR, "scraper_config.json")`). The email username, app password, SMTP host, SMTP port, SSL preference, and recipient addresses are all fetched from this file at runtime.
2. **Validates** email format for sender and all recipients
3. **Constructs** a plain-text email body with a numbered list of URLs, batch info, and timestamps
4. **Sends** via SMTP using either SSL or TLS (STARTTLS) depending on the configuration
5. **Handles errors** with specific diagnostics for authentication failures, connection issues, and server disconnections

### 4.7 batch_notifier.py - Batch Email System (Currently Disabled)

An optional module that can split large URL sets into smaller batches:

- Sends emails in batches of a configurable size (default: 20 URLs per email)
- Waits between batches (configurable delay)
- Tracks progress in `data/progress/batch_progress.json` so it can resume after interruption
- Currently disabled in `main.py` (`USE_BATCH_NOTIFICATION = False`)

---

## 5. Configuration

### 5.1 scraper_config.json

This is the primary configuration file that stores all settings. The system reads credentials from this secret file by referencing its path directly in the code:

```python
# In main.py
CONFIG_PATH = os.path.join(BASE_DIR, "scraper_config.json")
config = load_scraper_config()  # Reads the secret file at CONFIG_PATH
```

Each module (main.py, notifier.py, batch_notifier.py, and individual scrapers) references this same path pattern to load credentials at runtime:

```python
# In notifier.py
EmailNotifier(config_file="scraper_config.json")

# In fda_selenium_scraper.py, cpsc_links_scraper.py, etc.
CONFIG_PATH = os.path.join(BASE_DIR, "scraper_config.json")
```

**Configuration fields:**

| Field | Description | Example |
|-------|-------------|---------|
| `EMAIL_USERNAME` | Sender email address | `marketing.landk@gmail.com` |
| `EMAIL_PASSWORD` | Email app password (fetched from the secret file) | *(stored in scraper_config.json)* |
| `EMAIL_SMTP_HOST` | SMTP server hostname | `smtp.gmail.com` |
| `EMAIL_SMTP_PORT` | SMTP server port | `587` |
| `EMAIL_USE_SSL` | Use SSL instead of TLS | `false` |
| `RECEIVER_EMAIL` | Comma-separated recipient emails | `team@example.com,user@example.com` |
| `FSIS_ENABLED` | Enable/disable FSIS scraper | `true` |
| `FSIS_MAX_PAGES` | Max pages to scrape for FSIS | `3` |
| `SCOUT_ENABLED` | Enable/disable Scout scraper | `true` |
| `SCOUT_MAX_PAGES` | Max "More Cases" clicks for Scout | `50` |

### 5.2 Hardcoded Settings (in main.py)

| Setting | Value | Description |
|---------|-------|-------------|
| `CPSC_ENABLED` | `True` | CPSC scraper is always enabled |
| `CPSC_MAX_PAGES` | `10` | Max pages for CPSC |
| `FDA_ENABLED` | `True` | FDA scraper is always enabled |
| `FDA_MAX_PAGES` | `115` | Max pages for FDA |
| `HEADLESS_MODE` | `True` | Run Chrome in headless (no GUI) mode |
| `BATCH_SIZE` | `20` | URLs per batch email (when batch mode is on) |
| `USE_BATCH_NOTIFICATION` | `False` | Batch emailing is currently off |

---

## 6. De-Duplication Mechanism

Each scraper prevents sending duplicate recall URLs using this process:

1. **On startup**, loads previously seen URLs from its JSON file in `data/seen/`
2. **During scraping**, collects all URLs currently on the website
3. **Compares** the scraped set against the seen set: `new_urls = current - seen`
4. **Returns** only newly discovered URLs for notification
5. **After scraping**, saves the full combined set (old + new) back to the JSON file

This ensures that each recall URL is only reported once, even across multiple runs.

---

## 7. Email Notification Flow

```
All Scrapers Complete
        |
        v
Collect new URLs from each scraper
(CPSC: N urls, FDA: N urls, FSIS: N urls, Scout: N urls)
        |
        v
Merge into single combined list
        |
        v
EmailNotifier.send_notification()
  - Subject: "Daily Product Recall Links"
  - Scraper name: "CPSC + FDA + FSIS + SCOUT Digest"
  - Body includes numbered URL list + per-source counts
        |
        v
SMTP connection (Gmail via TLS on port 587)
  - Credentials fetched from scraper_config.json secret file
        |
        v
Email delivered to configured recipients
```

If no new URLs are found across all scrapers, a "No New Recalls Found" email is sent instead.

---

## 8. Scheduling and Automation

### Linux (Production)

The system is designed to run as a daily cron job using `run_product_recall.sh`:

```bash
#!/bin/bash
cd /home/deepak/CodeLab/GitHub/Product-Recall-Web-Scraping || exit 1
mkdir -p logs
source venv/bin/activate
python main.py >> logs/cron_run.log 2>&1
```

**Example cron entry** (runs daily at 2:00 AM):
```
0 2 * * * /path/to/run_product_recall.sh
```

### Linux Display Server

On headless Linux servers, `main.py` automatically starts an Xvfb virtual display (`DISPLAY=:99`, resolution 1920x1080) so that Chrome can run without a physical monitor. The Xvfb process is cleaned up on exit.

---

## 9. Logging

The system writes logs to multiple files:

| Log File | Source | Content |
|----------|--------|---------|
| `scraper.log` | `main.py` (UnifiedScraper) | High-level events: scraper start/stop, URL counts, email status, errors |
| `cpsc_links_scraper.log` | `cpsc_links_scraper.py` | Detailed CPSC link extraction and pagination logs |

**Log format:** `YYYY-MM-DD HH:MM:SS - LEVEL - Message`

Logs are written to both the log file and the console (stdout).

---

## 10. Dependencies

Key Python packages (from `requirements.txt`):

| Package | Purpose |
|---------|---------|
| `selenium` | Browser automation for all scrapers |
| `beautifulsoup4` | HTML parsing |
| `webdriver-manager` | Automatic ChromeDriver binary management |
| `chromedriver-autoinstaller` | Alternative ChromeDriver installer |
| `pyvirtualdisplay` | Virtual display for headless Linux |
| `requests` | HTTP requests |
| `pandas` | Data handling |
| `lxml` | XML/HTML processing |
| `psutil` | Process utilities |
| `python-dotenv` | Environment variable support |
| `tqdm` | Progress bars |

---

## 11. End-to-End Workflow Summary

1. **Trigger**: Cron job runs `run_product_recall.sh` daily, or `python main.py` is run manually
2. **Initialize**: `main.py` loads config from `scraper_config.json` secret file, sets up logging, starts Xvfb if on Linux
3. **Scrape CPSC**: Opens cpsc.gov, navigates up to 10 pages, extracts recall links, filters out previously seen URLs
4. **Scrape FDA**: Opens FDA recalls page, waits for DataTables to load, navigates up to 115 pages, extracts recall links, filters duplicates
5. **Scrape FSIS**: Opens FSIS recalls page, navigates up to 3 pages, extracts recall links, filters duplicates
6. **Scrape Scout**: Opens ScoutYourCase, clicks "More Cases" up to 50 times, extracts recall-related case URLs, filters duplicates
7. **Aggregate**: Combines all new URLs from all four scrapers
8. **Notify**: Sends a single consolidated digest email to configured recipients via Gmail SMTP (credentials fetched from secret file)
9. **Log**: Records summary (successful scrapers, failed scrapers, total URLs, total duration) to `scraper.log`
10. **Cleanup**: Terminates Xvfb process, closes all browser instances
