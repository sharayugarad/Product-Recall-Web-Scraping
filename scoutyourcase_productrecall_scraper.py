#!/usr/bin/env python3
import os
import re
import json
import time
import logging
import subprocess
from typing import Dict, Any, List, Set, Optional
from urllib.parse import urljoin, urlparse

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

RECALL_KEYWORDS = [
    "product recall",
    "product recalls",
    "recall notice",
    "recall alert",
    "safety recall",
    "recall",
    "recalled",
]

RECALL_REGEX = re.compile(
    r"\b(" + "|".join(re.escape(k) for k in RECALL_KEYWORDS) + r")\b",
    re.IGNORECASE,
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

SEEN_DIR = os.path.join(BASE_DIR, "data", "seen")
os.makedirs(SEEN_DIR, exist_ok=True)

SEEN_FILE = os.path.join(SEEN_DIR, "scoutyourcase_seen_urls.json")



def _norm(u: str) -> str:
    return (u or "").strip()


def _is_http_url(u: str) -> bool:
    try:
        p = urlparse(u)
        return p.scheme in ("http", "https")
    except Exception:
        return False


def _same_host(a: str, b: str) -> bool:
    try:
        return urlparse(a).netloc == urlparse(b).netloc
    except Exception:
        return False


class ScoutYourCaseProductRecallScraper:
    """
    Scrapes ScoutYourCase "More Cases" listing and keeps only cases whose card text
    contains "product recall" (case-insensitive).

    - Opens: https://ld.scoutyourcase.com/index
    - Clicks "More Cases" repeatedly (dynamic loading)
    - Collects case card URLs + filters by "product recall" text
    - Deduplicates vs seen file
    - Saves seen
    """

    def __init__(
        self,
        start_url: str = "https://ld.scoutyourcase.com/index",
        max_clicks: int = 30,
        click_pause: float = 1.0,
        headless: bool = True,
        debug: bool = True,
        timeout: int = 15,
    ):
        self.start_url = start_url
        self.max_clicks = max_clicks
        self.click_pause = click_pause
        self.headless = headless
        self.debug = debug
        self.timeout = timeout

        self.logger = logging.getLogger("ScoutYourCase")
        if not self.logger.handlers:
            self.logger.setLevel(logging.INFO)
            h = logging.StreamHandler()
            h.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
            self.logger.addHandler(h)

        self.driver = None
        self.existing: Set[str] = set()
        self.new_urls: List[str] = []

        self._setup_driver()
        self._load_seen()

    def _setup_driver(self):
        import undetected_chromedriver as uc

        profile_dir = os.path.join(BASE_DIR, "data", "chrome_profiles", "scout")
        os.makedirs(profile_dir, exist_ok=True)

        opts = uc.ChromeOptions()

        # IMPORTANT: try headless=False first on VPS (still uses Xvfb display)
        if self.headless:
            # If you still get blocked in headless, run with headless=False
            opts.add_argument("--headless=new")

        opts.add_argument("--no-sandbox")
        opts.add_argument("--disable-dev-shm-usage")
        opts.add_argument("--window-size=1920,1080")

        # Persist cookies/local storage (helps once it works)
        opts.add_argument(f"--user-data-dir={profile_dir}")
        opts.add_argument("--profile-directory=Default")

        # Reduce automation fingerprints
        opts.add_argument("--disable-blink-features=AutomationControlled")

        version_main = self._detect_chrome_major_version()
        if self.debug:
            self.logger.info(f"SCOUT: launching Chrome with version_main={version_main}")

        # Pin driver major version to the local browser to avoid
        # "ChromeDriver only supports Chrome version X" session errors.
        if version_main:
            self.driver = uc.Chrome(options=opts, version_main=version_main)
        else:
            self.driver = uc.Chrome(options=opts)

    def _detect_chrome_major_version(self) -> Optional[int]:
        """Best-effort detection of the locally installed Chrome major version."""
        commands = [
            ["google-chrome", "--version"],
            ["google-chrome-stable", "--version"],
            ["chromium", "--version"],
            ["chromium-browser", "--version"],
        ]

        for cmd in commands:
            try:
                out = subprocess.check_output(cmd, stderr=subprocess.STDOUT, text=True).strip()
                m = re.search(r"(\d+)\.\d+\.\d+\.\d+", out)
                if m:
                    return int(m.group(1))
            except Exception:
                continue

        return None


    def close(self):
        try:
            if self.driver:
                self.driver.quit()
        except Exception:
            pass

    def _load_seen(self):
        if os.path.exists(SEEN_FILE):
            try:
                data = json.load(open(SEEN_FILE, "r", encoding="utf-8"))
                if isinstance(data, list):
                    self.existing = set(data)
                elif isinstance(data, dict):
                    self.existing = set(data.get("urls", []))
                else:
                    self.existing = set()
                self.logger.info(f"SCOUT: Loaded {len(self.existing)} seen URLs from {SEEN_FILE}")
            except Exception as e:
                self.logger.warning(f"SCOUT: Could not load seen file: {e}")
                self.existing = set()
        else:
            self.logger.info("SCOUT: No seen file found, starting fresh")
            self.existing = set()

    def _save_seen(self, all_urls: Set[str]):
        try:
            json.dump(sorted(all_urls), open(SEEN_FILE, "w", encoding="utf-8"), indent=2)
            self.logger.info(f"SCOUT: Saved {len(all_urls)} total URLs to {SEEN_FILE}")
        except Exception as e:
            self.logger.warning(f"SCOUT: Could not save seen file: {e}")

    def _wait_body(self):
        WebDriverWait(self.driver, self.timeout).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )

    def _click_more_cases_until_done(self) -> int:
        """
        Clicks the "More Cases" button repeatedly until:
        - max_clicks reached OR
        - button not found/clickable OR
        - clicking does not increase page content / card count
        Returns number of successful clicks.
        """
        clicks = 0

        # We'll use anchor count as a cheap "did content increase" signal.
        last_a_count = -1

        for _ in range(self.max_clicks):
            # count anchors before click
            a_before = len(self.driver.find_elements(By.CSS_SELECTOR, "a[href]"))

            # Find "More Cases" button/link (text-based, robust)
            candidates = self.driver.find_elements(
                By.XPATH,
                "//*[self::button or self::a or self::div]"
                "[contains(translate(normalize-space(.),"
                " 'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'), 'more cases')]"
            )

            if not candidates:
                if self.debug:
                    self.logger.info("SCOUT: 'More Cases' control not found; stopping.")
                break

            btn = candidates[0]

            # scroll into view + click
            try:
                self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", btn)
                time.sleep(0.3)
                self.driver.execute_script("arguments[0].click();", btn)
            except Exception as e:
                if self.debug:
                    self.logger.info(f"SCOUT: Click failed/intercepted; stopping. err={e}")
                break

            time.sleep(self.click_pause)

            a_after = len(self.driver.find_elements(By.CSS_SELECTOR, "a[href]"))
            if self.debug:
                self.logger.info(f"SCOUT: click {clicks+1}: anchors before={a_before} after={a_after}")

            # if no growth, assume no more content
            if a_after <= a_before and a_after == last_a_count:
                if self.debug:
                    self.logger.info("SCOUT: No new content after click; stopping.")
                break

            last_a_count = a_after
            clicks += 1

        return clicks
    
    def _matches_recall_keywords(self, text: str) -> bool:
        if not text:
            return False
        return bool(RECALL_REGEX.search(text))
  

    def _is_candidate_case_url(self, href: str) -> bool:
        """Allow only same-site case-like URLs; skip generic/nav endpoints."""
        href = (href or "").strip()
        if not href:
            return False
        if not _is_http_url(href):
            return False

        parsed = urlparse(href)
        base_host = urlparse(self.start_url).netloc
        if parsed.netloc != base_host:
            return False

        path = (parsed.path or "").strip("/").lower()
        if not path:
            return False

        blocked_exact = {
            "index", "", "about", "contact", "privacy-policy", "terms", "faq", "login", "signup"
        }
        if path in blocked_exact:
            return False

        blocked_prefixes = ("assets/", "static/", "images/", "css/", "js/")
        if path.startswith(blocked_prefixes):
            return False

        return True

    def _extract_recall_case_urls(self) -> List[str]:
        found = set()
        anchors = self.driver.find_elements(By.CSS_SELECTOR, "a[href]")

        if self.debug:
            self.logger.info(f"SCOUT: total anchors found={len(anchors)}")

        for a in anchors:
            try:
                href = (a.get_attribute("href") or "").strip()
                if not self._is_candidate_case_url(href):
                    continue

                # Some cards use generic link text (e.g., "View case").
                # Pull text from the anchor + nearby container before filtering.
                text_parts = []
                anchor_text = ((a.text or "").strip() or (a.get_attribute("innerText") or "").strip())
                if anchor_text:
                    text_parts.append(anchor_text)

                parent = a
                for _ in range(3):
                    parent = parent.find_element(By.XPATH, "./..")
                    parent_text = (parent.text or "").strip()
                    if parent_text:
                        text_parts.append(parent_text)

                context_text = "\n".join(text_parts)

                if not self._matches_recall_keywords(context_text):
                    continue

                found.add(href)

                if self.debug:
                    snippet = " ".join(context_text.split())[:160]
                    self.logger.info(f"SCOUT: MATCH → href={href} context='{snippet}'")

            except Exception:
                continue

        return sorted(found)

    def scrape(self) -> Dict[str, Any]:
        start = time.time()
        pages_loaded = 0

        try:
            self.logger.info(f"SCOUT: OPEN {self.start_url}")
            self.driver.get(self.start_url)
            self._wait_body()
            html = (self.driver.page_source or "").lower()
            title = (self.driver.title or "").lower()

            if "just a moment" in title or "cloudflare" in html:
                return {
                    "success": False,
                    "error": "Blocked by Cloudflare (Just a moment / challenge page).",
                    "pages_loaded": pages_loaded,
                    "new_urls": [],
                    "duration": time.time() - start,
                }
            pages_loaded = 1

            if self.debug:
                self.logger.info(
                    f"SCOUT: title={self.driver.title!r} html_len={len(self.driver.page_source or '')} "
                    f"final={self.driver.current_url}"
                )

            clicks = self._click_more_cases_until_done()

            urls = self._extract_recall_case_urls()

            # Dedup vs seen
            new = [u for u in urls if u not in self.existing]
            self.new_urls = new

            # Update seen file with ALL matched URLs (not just new)
            all_seen = set(self.existing).union(urls)
            self._save_seen(all_seen)

            dur = time.time() - start
            self.logger.info(
                f"SCOUT: Done. pages_loaded={pages_loaded}, clicks={clicks}, "
                f"matches={len(urls)}, new_matches={len(new)}, duration={dur:.2f}s"
            )

            return {
                "success": True,
                "pages_loaded": pages_loaded,
                "clicks": clicks,
                "matched_urls": urls,
                "new_urls": new,
                "duration": dur,
            }

        except Exception as e:
            dur = time.time() - start
            self.logger.warning(f"SCOUT: Failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "pages_loaded": pages_loaded,
                "new_urls": [],
                "duration": dur,
            }
