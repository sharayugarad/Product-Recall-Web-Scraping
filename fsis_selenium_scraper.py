# fsis_selenium_scraper.py

import os
import json
import time
import logging
from typing import List, Dict, Any, Set, Optional

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options

# Reuse same config path pattern
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "scraper_config.json")

DATA_DIR = os.path.join(BASE_DIR, "data", "seen")
os.makedirs(DATA_DIR, exist_ok=True)

FSIS_SEEN_FILE = os.path.join(DATA_DIR, "fsis_seen_urls.json")

logger = logging.getLogger(__name__)


class FSISSeleniumScraper:
    """
    Scraper for https://www.fsis.usda.gov/recalls

    Pattern:
      - Load existing URLs from fsis_seen_urls.json
      - Visit FSIS recall listing pages
      - Collect recall detail URLs
      - Deduplicate vs seen URLs
      - Save updated seen URLs
      - Return list of new URLs
    """

    def __init__(self, headless: bool = True, max_pages: Optional[int] = None):
        self.headless = headless
        self.max_pages = max_pages
        self.existing_urls: Set[str] = set()
        self.new_urls: List[str] = []

        self._setup_driver()
        self._load_existing_urls()

    # ---------- Setup / teardown ----------

    def _setup_driver(self):
        chrome_options = Options()
        if self.headless:
            chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--window-size=1920,1080")

        logger.info("Setting up Chrome WebDriver for FSIS...")
        self.driver = webdriver.Chrome(options=chrome_options)
        logger.info("Chrome WebDriver for FSIS initialized successfully")

    def close(self):
        if hasattr(self, "driver") and self.driver:
            self.driver.quit()
            logger.info("FSIS WebDriver closed successfully")

    # ---------- Seen URLs handling ----------

    def _load_existing_urls(self):
        if os.path.exists(FSIS_SEEN_FILE):
            try:
                with open(FSIS_SEEN_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.existing_urls = set(data if isinstance(data, list) else data.get("urls", []))
                logger.info(f"FSIS: Loaded {len(self.existing_urls)} existing URLs")
            except Exception as e:
                logger.warning(f"FSIS: Could not load existing URLs: {e}")
        else:
            logger.info("FSIS: No existing URLs file found, starting fresh")

    def _save_urls(self):
        try:
            all_urls = list(self.existing_urls.union(self.new_urls))
            with open(FSIS_SEEN_FILE, "w", encoding="utf-8") as f:
                json.dump(all_urls, f, indent=2)
            logger.info(f"FSIS: Saved {len(all_urls)} total URLs to {FSIS_SEEN_FILE}")
        except Exception as e:
            logger.error(f"FSIS: Error saving URLs: {e}")

    # ---------- Core scraping ----------

    def scrape_all_recalls(self, delay: float = 0.5) -> Dict[str, Any]:
        """
        Scrape recall URLs from FSIS listing.

        Returns:
          {
            "success": bool,
            "new_urls": [...],
            "error": optional_str
          }
        """
        start = time.time()
        base_url = "https://www.fsis.usda.gov/recalls"

        try:
            self.driver.get(base_url)
            time.sleep(delay)

            # TODO: Adjust selectors based on actual FSIS HTML structure.
            # Open FSIS in browser, inspect recall cards/rows,
            # then update these XPaths/CSS selectors accordingly.

            page = 1
            while True:
                logger.info(f"FSIS: Scraping page {page}")

                logger.info("FSIS: Looking for recall links with current XPath...")
                recall_links = self.driver.find_elements(
                    By.XPATH,
                    "//a[contains(@href, '/recalls') and contains(@href, '/alerts') or contains(@href, '/recalls-')]"  # VERY GENERIC - CHANGE
                )
                logger.info(f"FSIS: Raw recall_links count = {len(recall_links)}")
                for idx, elem in enumerate(recall_links[:10], start=1):
                    logger.info(f"FSIS: Link {idx}: {elem.get_attribute('href')}")

                new_this_page = 0
                for elem in recall_links:
                    href = elem.get_attribute("href")
                    if not href:
                        continue

                    href = href.strip()
                    if href not in self.existing_urls and href not in self.new_urls:
                        self.new_urls.append(href)
                        new_this_page += 1

                logger.info(f"FSIS: Found {len(recall_links)} links, {new_this_page} new on this page")

                # TODO: Implement real pagination logic.
                #  E.g. click "Next" button, break if disabled or not found.
                if self.max_pages and page >= self.max_pages:
                    logger.info("FSIS: Reached max_pages limit, stopping")
                    break

                # Example pagination selector – you MUST update this:
                try:
                    next_button = self.driver.find_element(
                        By.XPATH, "//a[contains(@class,'pager__link--next')]"
                    )
                except Exception:
                    logger.info("FSIS: No 'Next' button found, assuming last page")
                    break

                if not next_button.is_enabled():
                    logger.info("FSIS: Next button disabled, assuming last page")
                    break

                next_button.click()
                page += 1
                time.sleep(delay)

            # After scraping all pages
            self._save_urls()
            duration = time.time() - start
            logger.info(f"FSIS: Completed with {len(self.new_urls)} new URLs in {duration:.2f}s")

            return {
                "success": True,
                "new_urls": self.new_urls,
                "duration": duration
            }

        except Exception as e:
            logger.error(f"FSIS: Error during scraping: {e}")
            return {
                "success": False,
                "error": str(e),
                "new_urls": []
            }
