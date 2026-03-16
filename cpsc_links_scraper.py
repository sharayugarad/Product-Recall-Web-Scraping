# #!/usr/bin/env python3
# import json
# import time
# import logging
# import platform
# from datetime import datetime
# from typing import List, Set, Optional
# import os
# import sys

# from selenium import webdriver
# from urllib.parse import urlparse
# from selenium.webdriver.common.by import By
# from selenium.webdriver.support.ui import WebDriverWait
# from selenium.webdriver.support import expected_conditions as EC
# from selenium.webdriver.chrome.options import Options
# from selenium.common.exceptions import (
#     TimeoutException, 
#     NoSuchElementException, 
#     StaleElementReferenceException,
#     WebDriverException
# )


# BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# CONFIG_PATH = os.path.join(BASE_DIR, "scraper_config.json")

# SEEN_DIR = os.path.join(BASE_DIR, "data", "seen")
# os.makedirs(SEEN_DIR, exist_ok=True)
# CPSC_SEEN_FILE = os.path.join(SEEN_DIR, "cpsc_seen_urls.json")


# # Import email notifier
# try:
#     from notifier import EmailNotifier
#     EMAIL_NOTIFIER_AVAILABLE = True
# except ImportError:
#     EMAIL_NOTIFIER_AVAILABLE = False


# class CPSCScraper:
#     """
#     Simple scraper for CPSC recall links with cross-platform support.
#     """
    
#     def __init__(self, headless: bool = True):
#         """
#         Initialize the links scraper.
        
#         Args:
#             headless (bool): Run browser in headless mode
#         """
#         self.base_url = "https://www.cpsc.gov/Recalls"
#         self.headless = headless
#         self.scraped_links = set()
#         self.existing_links = set()
#         self.driver = None
        
#         # Setup logging
#         logging.basicConfig(
#             level=logging.INFO,
#             format='%(asctime)s - %(levelname)s - %(message)s',
#             handlers=[
#                 logging.FileHandler('cpsc_links_scraper.log', encoding='utf-8'),
#                 logging.StreamHandler(sys.stdout)
#             ]
#         )
#         self.logger = logging.getLogger(__name__)
        
#         # Load existing links to avoid duplicates
#         self._load_existing_links()
        
#         # Initialize WebDriver
#         self._setup_driver()
        
#         # Initialize email notifier
#         if EMAIL_NOTIFIER_AVAILABLE:
#             self.email_notifier = EmailNotifier(config_file=CONFIG_PATH)
#             self.logger.info("Email notifications enabled")
#         else:
#             self.email_notifier = None
#             self.logger.warning("Email notifications not available")
            
#     ##updated driver file-
#     def _setup_driver(self):
#         """Setup Chrome WebDriver with automatic driver management."""
#         try:
#             self.logger.info("Setting up Chrome WebDriver...")
            
#             # Chrome options
#             chrome_options = Options()
#             if self.headless:
#                 chrome_options.add_argument("--headless=new")
#             chrome_options.add_argument("--no-sandbox")
#             chrome_options.add_argument("--disable-dev-shm-usage")
#             chrome_options.add_argument("--disable-gpu")
#             chrome_options.add_argument("--window-size=1920,1080")
#             chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            
#             # Let Selenium handle driver automatically (Selenium 4.6+)
#             # Don't specify service - let Selenium Manager handle it
#             self.driver = webdriver.Chrome(options=chrome_options)
#             self.driver.implicitly_wait(10)
            
#             self.logger.info("Chrome WebDriver initialized successfully")
            
#         except Exception as e:
#             self.logger.error(f"Failed to initialize Chrome driver: {e}")
#             raise
            
#     # def _load_existing_links(self):
#     #     """Load existing links from JSON file to avoid duplicates."""
#     #     try:
#     #         if os.path.exists("cpsc_seen_urls.json"):
#     #             with open("cpsc_seen_urls.json", 'r', encoding='utf-8') as f:
#     #                 data = json.load(f)
#     #                 self.existing_links = set(data.get('links', []))
#     #                 self.logger.info(f"Loaded {len(self.existing_links)} existing URLs from cpsc_seen_urls.json")
#     #         else:
#     #             self.existing_links = set()
#     #             self.logger.info("No existing URLs file found, starting fresh")
#     #     except Exception as e:
#     #         self.logger.warning(f"Error loading existing URLs: {e}")
#     #         self.existing_links = set()

#     def _load_existing_links(self):
#         """Load existing links from JSON file to avoid duplicates."""
#         try:
#             if os.path.exists(CPSC_SEEN_FILE):
#                 with open(CPSC_SEEN_FILE, 'r', encoding='utf-8') as f:
#                     data = json.load(f)
#                     self.existing_links = set(data.get('links', []))
#                 self.logger.info(f"Loaded {len(self.existing_links)} existing URLs from {CPSC_SEEN_FILE}")
#             else:
#                 self.existing_links = set()
#                 self.logger.info("No existing URLs file found, starting fresh")
#         except Exception as e:
#             self.logger.warning(f"Error loading existing URLs: {e}")
#             self.existing_links = set()

    
#     def scrape_all_links(self, start_page: int = 0, end_page: Optional[int] = None) -> List[str]:
#         """
#         Scrape all recall links from CPSC website.
        
#         Args:
#             start_page (int): Starting page number (0-based)
#             end_page (Optional[int]): Ending page number (0-based), None for all pages
            
#         Returns:
#             List[str]: List of new recall URLs found
#         """
#         try:
#             self.logger.info("Starting CPSC links scraping...")
#             start_time = time.time()
            
#             # Navigate to CPSC recalls page
#             self.logger.info(f"Navigating to {self.base_url}")
#             self.driver.get(self.base_url)
            
#             # Wait for page to load
#             try:
#                 WebDriverWait(self.driver, 15).until(
#                     EC.presence_of_element_located((By.CSS_SELECTOR, ".recall-list, .view-content, main"))
#                 )
#             except TimeoutException:
#                 time.sleep(3)
            
#             page_count = 0
#             total_links = 0
            
#             while True:
#                 if end_page is not None and page_count >= end_page:
#                     self.logger.info(f"Reached specified end page: {end_page}")
#                     break
                
#                 page_count += 1
#                 self.logger.info(f"Scraping page {page_count}")
                
#                 # Extract links from current page
#                 page_links = self._extract_links_from_page()
                
#                 # Add new links to scraped set
#                 self.scraped_links.update(page_links)
#                 total_links += len(page_links)
                
#                 self.logger.info(f"Page {page_count}: {len(page_links)} links found")
                
#                 # Check if there's a next page
#                 if not self._navigate_to_next_page():
#                     self.logger.info("No more pages found")
#                     break
                
#                 # Small delay between pages
#                 time.sleep(1)
            
#             duration = time.time() - start_time
            
#             # Filter out existing links to get only new ones
#             new_links = self.scraped_links - self.existing_links
#             all_links = self.scraped_links | self.existing_links
            
#             self.logger.info(f"Link scraping complete. Total scraped: {len(self.scraped_links)}")
#             self.logger.info(f"Existing links: {len(self.existing_links)}")
#             self.logger.info(f"New links found: {len(new_links)}")
            
#             # Update scraped_links to include all links for saving
#             self.scraped_links = all_links
            
#             # # Send email notification only for new links
#             # if self.email_notifier:
#             #     self._send_email_notification()
            
#             return list(new_links)
            
#         except Exception as e:
#             self.logger.error(f"Fatal error during scraping: {e}")
#             new_links = self.scraped_links - self.existing_links
#             return list(new_links)
    
#     def _extract_links_from_page(self) -> Set[str]:
#         """Extract recall links from current page."""
#         links = set()
        
#         try:
#             try:
#                 WebDriverWait(self.driver, 10).until(
#                     EC.presence_of_element_located((By.CSS_SELECTOR, ".recall-list, .view-content, main"))
#                 )
#             except TimeoutException:
#                 time.sleep(2)
            
#             selectors = [
#                 "a[href*='/Recalls/']",
#                 "a[href*='recall']", 
#                 ".recall-list a",
#                 "main a[href*='recall']",
#                 "a[href*='cpsc.gov/Recalls']"
#             ]
            
#             for selector in selectors:
#                 try:
#                     link_elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    
#                     for element in link_elements:
#                         try:
#                             href = element.get_attribute('href')
#                             text = element.text.strip()
                            
#                             if href and ('recall' in href.lower() or 'recall' in text.lower()):
#                                 if not any(skip in href.lower() for skip in ['#', 'javascript:', 'mailto:', 'tel:']):
#                                     if '/Recalls/' in href or 'recall' in href.lower():
#                                         links.add(href)
#                         except StaleElementReferenceException:
#                             continue
#                         except Exception as e:
#                             self.logger.warning(f"Error extracting link: {e}")
#                             continue
#                 except Exception as e:
#                     self.logger.warning(f"Error with selector '{selector}': {e}")
#                     continue
            
#         except Exception as e:
#             self.logger.error(f"Error extracting links from page: {e}")
        
#         self.logger.info(f"Extracted {len(links)} unique links from page")
#         return links
    
#     def _navigate_to_next_page(self) -> bool:
#         """Navigate to next page if available."""
#         try:
#             next_selectors = [
#                 "a[title*='Go to next page']",
#                 ".pager-next a",
#                 "a[title*='Next page']",
#                 "a[title*='Next']",
#                 ".pagination .next a",
#                 "a[href*='page=']"
#             ]
            
#             next_link = None
#             for selector in next_selectors:
#                 next_links = self.driver.find_elements(By.CSS_SELECTOR, selector)
#                 if next_links:
#                     next_link = next_links[0]
#                     self.logger.info(f"Found next page link using selector: {selector}")
#                     break
            
#             if next_link:
#                 self.driver.execute_script("arguments[0].scrollIntoView(true);", next_link)
#                 time.sleep(1)
                
#                 try:
#                     next_link.click()
#                     self.logger.info("Successfully clicked next page link")
#                 except Exception as click_error:
#                     self.logger.warning(f"Regular click failed: {click_error}, trying JavaScript click...")
#                     self.driver.execute_script("arguments[0].click();", next_link)
#                     self.logger.info("Successfully clicked next page link with JavaScript")
                
#                 try:
#                     WebDriverWait(self.driver, 15).until(
#                         EC.presence_of_element_located((By.CSS_SELECTOR, ".recall-list, .view-content, main"))
#                     )
#                 except TimeoutException:
#                     time.sleep(3)
                
#                 return True
#             else:
#                 self.logger.info("No next page link found")
#                 return False
                
#         except Exception as e:
#             self.logger.warning(f"Error navigating to next page: {e}")
#             return False

#     def save_links(self, output_file: str = CPSC_SEEN_FILE) -> str:
#         """
#         Save scraped links to JSON file with metadata.
        
#         Args:
#             output_file (str): Path to output JSON file
            
#         Returns:
#             str: Path to the saved file
#         """
#         try:
#             data = {
#                 'scraping_metadata': {
#                     'scraped_at': datetime.now().isoformat(),
#                     'total_links': len(self.scraped_links),
#                     'new_links_found': len(self.scraped_links - self.existing_links),
#                     'existing_links': len(self.existing_links),
#                     'source_url': self.base_url,
#                     'scraper_version': '2.0.1-cross-platform-fixed',
#                     'platform': platform.system()
#                 },
#                 'links': list(self.scraped_links)
#             }
            
#             with open(output_file, 'w', encoding='utf-8') as f:
#                 json.dump(data, f, indent=2, ensure_ascii=False)
            
#             self.logger.info(f"Links saved to {output_file}")
#             self.logger.info(f"Total links: {len(self.scraped_links)}")
#             self.logger.info(f"New links: {len(self.scraped_links - self.existing_links)}")
            
#             return output_file
            
#         except Exception as e:
#             self.logger.error(f"Error saving links: {e}")
#             raise

    
#     def _send_email_notification(self):
#         """Send email notification with new links."""
#         if not self.email_notifier:
#             return
        
#         try:
#             new_links = self.scraped_links - self.existing_links
#             if new_links:
#                 self.logger.info(f"Sending email notification with {len(new_links)} new links")
#                 success = self.email_notifier.send_notification(
#                     list(new_links), 
#                     len(new_links),
#                     subject_prefix="CPSC Recalls Scrapped Links",
#                     scraper_name="CPSC Scraper"
#                 )
#                 if success:
#                     self.logger.info("Email notification sent successfully")
#                 else:
#                     self.logger.warning("Failed to send email notification")
#             else:
#                 self.logger.info("Sending email notification: No new links found")
#                 success = self.email_notifier.send_notification(
#                     [], 
#                     0,
#                     subject_prefix="CPSC Recalls Scrapped Links - No Updates",
#                     scraper_name="CPSC Scraper",
#                     no_urls_found=True
#                 )
#                 if success:
#                     self.logger.info("No updates email notification sent successfully")
#                 else:
#                     self.logger.warning("Failed to send no updates email notification")
#         except Exception as e:
#             self.logger.error(f"Error sending email notification: {e}")
    
#     def get_statistics(self) -> dict:
#         """Get scraping statistics."""
#         return {
#             'total_links': len(self.scraped_links),
#             'new_links': len(self.scraped_links - self.existing_links),
#             'existing_links': len(self.existing_links),
#             'platform': platform.system()
#         }
    
#     def close(self):
#         """Clean up resources."""
#         try:
#             if self.driver:
#                 self.driver.quit()
#                 self.logger.info("WebDriver closed successfully")
#         except Exception as e:
#             self.logger.warning(f"Error closing WebDriver: {e}")


# if __name__ == "__main__":
#     # Test the scraper
#     scraper = CPSCScraper(headless=True)
#     try:
#         links = scraper.scrape_all_links(start_page=0, end_page=2)
#         print(f"Found {len(links)} new links")
#         scraper.save_links()
#     finally:
#         scraper.close()





























#!/usr/bin/env python3
# cpsc_links_scraper.py

import json
import time
import logging
import platform
from datetime import datetime
from typing import List, Set, Optional
import os
import sys
from urllib.parse import urlparse

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import (
    TimeoutException,
    StaleElementReferenceException,
)

# ------------------------------------------------------------
# Paths
# ------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "scraper_config.json")

SEEN_DIR = os.path.join(BASE_DIR, "data", "seen")
os.makedirs(SEEN_DIR, exist_ok=True)
CPSC_SEEN_FILE = os.path.join(SEEN_DIR, "cpsc_seen_urls.json")

# ------------------------------------------------------------
# Import email notifier (optional)
# ------------------------------------------------------------
try:
    from notifier import EmailNotifier  # your existing notifier module
    EMAIL_NOTIFIER_AVAILABLE = True
except ImportError:
    EMAIL_NOTIFIER_AVAILABLE = False


class CPSCScraper:
    """
    Scraper for CPSC recall detail links:
      - Only keeps URLs like https://www.cpsc.gov/Recalls/....
      - Blocks CSV export endpoints (Visualization-Export-Recall* and _format=csv)
      - Stores seen URLs in data/seen/cpsc_seen_urls.json
    """

    def __init__(self, headless: bool = True):
        self.base_url = "https://www.cpsc.gov/Recalls"
        self.headless = headless

        self.scraped_links: Set[str] = set()
        self.existing_links: Set[str] = set()

        self.driver = None

        # Logging
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - %(message)s",
            handlers=[
                logging.FileHandler(os.path.join(BASE_DIR, "cpsc_links_scraper.log"), encoding="utf-8"),
                logging.StreamHandler(sys.stdout),
            ],
        )
        self.logger = logging.getLogger(__name__)

        # Load + driver
        self._load_existing_links()
        self._setup_driver()

        # Email notifier (optional)
        if EMAIL_NOTIFIER_AVAILABLE:
            self.email_notifier = EmailNotifier(config_file=CONFIG_PATH)
            self.logger.info("Email notifications enabled")
        else:
            self.email_notifier = None
            self.logger.warning("Email notifications not available (notifier import failed)")

    # ------------------------------------------------------------
    # Driver
    # ------------------------------------------------------------
    def _setup_driver(self):
        """Setup Chrome WebDriver (Selenium Manager handles driver download)."""
        self.logger.info("Setting up Chrome WebDriver...")

        chrome_options = Options()
        if self.headless:
            chrome_options.add_argument("--headless=new")

        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")

        self.driver = webdriver.Chrome(options=chrome_options)
        self.driver.implicitly_wait(10)

        self.logger.info("Chrome WebDriver initialized successfully")

    def close(self):
        """Clean up resources."""
        try:
            if self.driver:
                self.driver.quit()
                self.logger.info("WebDriver closed successfully")
        except Exception as e:
            self.logger.warning(f"Error closing WebDriver: {e}")

    # ------------------------------------------------------------
    # Seen file handling
    # ------------------------------------------------------------
    def _load_existing_links(self):
        """Load existing links from JSON file (supports both list and dict formats)."""
        try:
            if os.path.exists(CPSC_SEEN_FILE):
                with open(CPSC_SEEN_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)

                # Supports:
                # 1) {"links": [...]}
                # 2) [...]
                if isinstance(data, list):
                    self.existing_links = set(data)
                else:
                    self.existing_links = set(data.get("links", []))

                self.logger.info(f"Loaded {len(self.existing_links)} existing URLs from {CPSC_SEEN_FILE}")
            else:
                self.existing_links = set()
                self.logger.info("No existing URLs file found, starting fresh")
        except Exception as e:
            self.logger.warning(f"Error loading existing URLs: {e}")
            self.existing_links = set()

    def save_links(self, output_file: str = CPSC_SEEN_FILE) -> str:
        """
        Save scraped links to JSON file with metadata.
        """
        try:
            data = {
                "scraping_metadata": {
                    "scraped_at": datetime.now().isoformat(),
                    "total_links": len(self.scraped_links),
                    "new_links_found": len(self.scraped_links - self.existing_links),
                    "existing_links": len(self.existing_links),
                    "source_url": self.base_url,
                    "scraper_version": "3.0.0-cpsc-filtered",
                    "platform": platform.system(),
                },
                "links": sorted(self.scraped_links),
            }

            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            self.logger.info(f"Links saved to {output_file}")
            self.logger.info(f"Total links saved: {len(self.scraped_links)}")
            return output_file

        except Exception as e:
            self.logger.error(f"Error saving links: {e}")
            raise

    # ------------------------------------------------------------
    # URL filtering
    # ------------------------------------------------------------
    @staticmethod
    def is_valid_cpsc_recall_url(url: str) -> bool:
        """
        Allow only real recall detail pages on cpsc.gov/Recalls/...
        Block CSV export endpoints and junk protocols.
        """
        if not url:
            return False

        u = url.strip()

        # Block CSV export endpoints (your problem URLs)
        if "Visualization-Export-Recall" in u:
            return False
        if "_format=csv" in u:
            return False

        # Block junk protocols
        low = u.lower()
        if any(low.startswith(p) for p in ("javascript:", "mailto:", "tel:")):
            return False
        if "#" in u and u.endswith("#"):
            return False

        parsed = urlparse(u)

        # Only keep cpsc.gov recall details
        return parsed.netloc.endswith("cpsc.gov") and parsed.path.startswith("/Recalls/")

    # ------------------------------------------------------------
    # Scrape
    # ------------------------------------------------------------
    def scrape_all_links(self, start_page: int = 0, end_page: Optional[int] = None) -> List[str]:
        """
        Scrape recall links from CPSC website.
        Args:
            start_page: currently unused (kept for API compatibility)
            end_page: scrape up to N pages total (1-based in practice here). None = until no next page.
        Returns:
            List[str]: new recall URLs found in this run
        """
        try:
            self.logger.info("Starting CPSC links scraping...")
            start_time = time.time()

            self.logger.info(f"Navigating to {self.base_url}")
            self.driver.get(self.base_url)

            # Wait for page
            try:
                WebDriverWait(self.driver, 15).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "main"))
                )
            except TimeoutException:
                time.sleep(2)

            page_num = 0

            while True:
                page_num += 1
                self.logger.info(f"Scraping page {page_num}")

                page_links = self._extract_links_from_page()
                self.scraped_links.update(page_links)

                self.logger.info(f"Page {page_num}: {len(page_links)} valid recall links found")

                if end_page is not None and page_num >= end_page:
                    self.logger.info(f"Reached specified end_page limit: {end_page}")
                    break

                if not self._navigate_to_next_page():
                    self.logger.info("No more pages found")
                    break

                time.sleep(1)

            duration = time.time() - start_time

            new_links = self.scraped_links - self.existing_links
            all_links = self.scraped_links | self.existing_links
            self.scraped_links = all_links  # so save_links keeps full history

            self.logger.info(f"Scrape complete in {duration:.2f}s")
            self.logger.info(f"Total scraped this run (valid): {len(self.scraped_links)}")
            self.logger.info(f"Existing before run: {len(self.existing_links)}")
            self.logger.info(f"New links found: {len(new_links)}")

            return sorted(new_links)

        except Exception as e:
            self.logger.error(f"Fatal error during scraping: {e}")
            # Return whatever new we already found
            new_links = self.scraped_links - self.existing_links
            return sorted(new_links)

    def _extract_links_from_page(self) -> Set[str]:
        """Extract ONLY valid CPSC recall detail links from the current page."""
        links: Set[str] = set()

        try:
            # Only use specific selectors for recall detail pages
            selectors = [
                "a[href*='/Recalls/']",
                "a[href*='cpsc.gov/Recalls']",
            ]

            for selector in selectors:
                try:
                    elems = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for el in elems:
                        try:
                            href = el.get_attribute("href")
                            if not href:
                                continue

                            if self.is_valid_cpsc_recall_url(href):
                                links.add(href.strip())

                        except StaleElementReferenceException:
                            continue
                        except Exception:
                            continue
                except Exception:
                    continue

        except Exception as e:
            self.logger.error(f"Error extracting links from page: {e}")

        return links

    def _navigate_to_next_page(self) -> bool:
        """Click Next page (safe selectors only)."""
        try:
            # IMPORTANT: do NOT include broad selectors like a[href*='page=']
            next_selectors = [
                "a[title*='Go to next page']",
                "li.pager__item--next a",
                "a.pager__link--next",
                "a[rel='next']",
            ]

            next_link = None
            for selector in next_selectors:
                candidates = self.driver.find_elements(By.CSS_SELECTOR, selector)
                if candidates:
                    next_link = candidates[0]
                    break

            if not next_link:
                return False

            # Scroll + click (try normal, then JS)
            self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", next_link)
            time.sleep(0.5)

            try:
                next_link.click()
            except Exception:
                self.driver.execute_script("arguments[0].click();", next_link)

            # Wait for main to re-render
            try:
                WebDriverWait(self.driver, 15).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "main"))
                )
            except TimeoutException:
                time.sleep(2)

            return True

        except Exception as e:
            self.logger.warning(f"Error navigating to next page: {e}")
            return False

    # ------------------------------------------------------------
    # Optional email (not used if you do combined digest in main.py)
    # ------------------------------------------------------------
    def _send_email_notification(self):
        """
        If you still ever use per-scraper email (you said you want combined only),
        keep this, but DO NOT call it from scrape_all_links().
        """
        if not self.email_notifier:
            return

        try:
            new_links = self.scraped_links - self.existing_links

            if new_links:
                self.logger.info(f"Sending email notification with {len(new_links)} new links")
                self.email_notifier.send_notification(
                    list(new_links),
                    len(new_links),
                    subject_prefix="CPSC Recalls Scraped Links",
                    scraper_name="CPSC Scraper",
                )
            else:
                self.logger.info("Sending email notification: No new links found")
                self.email_notifier.send_notification(
                    [],
                    0,
                    subject_prefix="CPSC Recalls Scraped Links - No Updates",
                    scraper_name="CPSC Scraper",
                    no_urls_found=True,
                )
        except Exception as e:
            self.logger.error(f"Error sending email notification: {e}")

    def get_statistics(self) -> dict:
        return {
            "total_links": len(self.scraped_links),
            "new_links": len(self.scraped_links - self.existing_links),
            "existing_links": len(self.existing_links),
            "platform": platform.system(),
        }


if __name__ == "__main__":
    # Quick local test
    scraper = CPSCScraper(headless=True)
    try:
        new_links = scraper.scrape_all_links(end_page=2)
        print(f"Found {len(new_links)} new links")
        scraper.save_links()
    finally:
        scraper.close()

