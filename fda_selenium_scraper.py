#!/usr/bin/env python3

import os
import sys
import time
import json
import logging
import platform
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from urllib.parse import urljoin, urlparse

# Selenium imports
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException, 
    NoSuchElementException, 
    WebDriverException,
    ElementNotInteractableException
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "scraper_config.json")
print(CONFIG_PATH)
SEEN_DIR = os.path.join(BASE_DIR, "data", "seen")
os.makedirs(SEEN_DIR, exist_ok=True)
FDA_SEEN_FILE = os.path.join(SEEN_DIR, "fda_seen_urls.json")

# Try different ChromeDriver installation methods
try:
    import chromedriver_autoinstaller
    CHROMEDRIVER_AUTOINSTALLER_AVAILABLE = True
except ImportError:
    CHROMEDRIVER_AUTOINSTALLER_AVAILABLE = False

try:
    from webdriver_manager.chrome import ChromeDriverManager
    WEBDRIVER_MANAGER_AVAILABLE = True
except ImportError:
    WEBDRIVER_MANAGER_AVAILABLE = False

# Import email notifier
try:
    from notifier import EmailNotifier
    EMAIL_NOTIFIER_AVAILABLE = True
except ImportError:
    EMAIL_NOTIFIER_AVAILABLE = False


class FDASeleniumScraper:
    """
    Enhanced FDA recall data scraper with cross-platform WebDriver support.
    Optimized for reliability and performance across Windows and Linux systems.
    """
    
    def __init__(self, headless: bool = True, enable_email: bool = True, max_retries: int = 2):
        """
        Initialize the FDA scraper.
        
        Args:
            headless (bool): Run browser in headless mode
            enable_email (bool): Enable email notifications
            max_retries (int): Maximum retry attempts for failed operations
        """
        self.base_url = "https://www.fda.gov/safety/recalls-market-withdrawals-safety-alerts"
        self.headless = headless
        self.enable_email = enable_email
        self.max_retries = max_retries
        self.driver = None
        self.seen_urls = set()
        self.new_urls = []
        self.recalls = []
        
        # Setup logging
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        
        # Setup email notifier
        if enable_email and EMAIL_NOTIFIER_AVAILABLE:
            try:
                self.email_notifier = EmailNotifier(config_file=CONFIG_PATH)
            except Exception as e:
                self.logger.warning(f"Email notifications not available: {e}")
                self.enable_email = False
        else:
            self.enable_email = False
            if enable_email:
                self.logger.warning("Email notifications not available")
    
    def _get_chromedriver_paths(self) -> List[str]:
        """Get possible ChromeDriver paths for different platforms."""
        if platform.system() == "Windows":
            return [
                "chromedriver.exe",  # Local file first
                os.path.join(os.getcwd(), "chromedriver.exe"),
                os.path.join(os.path.dirname(__file__), "chromedriver.exe"),
                r"C:\chromedriver\chromedriver.exe",
                r"C:\Program Files\chromedriver\chromedriver.exe",
            ]
        else:  # Linux/Unix
            return [
                "chromedriver",  # Local file first
                "/usr/bin/chromedriver",
                "/usr/local/bin/chromedriver",
                "/opt/chromedriver/chromedriver",
                "/snap/bin/chromium.chromedriver",
                os.path.join(os.getcwd(), "chromedriver"),
            ]
    
    def _get_enhanced_chrome_options(self) -> Options:
        """
        Get enhanced Chrome options for maximum compatibility.
        
        FIXED: Removed JavaScript and CSS disabling to allow DataTables to work properly.
        Only images are disabled for performance optimization.
        """
        chrome_options = Options()
        
        if self.headless:
            chrome_options.add_argument("--headless")
        
        # Performance optimizations
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-web-security")
        chrome_options.add_argument("--allow-running-insecure-content")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-plugins")
        
        # Only disable images for performance - keep JavaScript and CSS enabled
        chrome_options.add_argument("--disable-images")
        
        # Platform-specific User-Agent
        if platform.system() == "Windows":
            user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        else:  # Linux/Unix
            user_agent = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        
        chrome_options.add_argument(f"--user-agent={user_agent}")
        
        # Optimized preferences - only disable images
        prefs = {
            "profile.managed_default_content_settings.images": 2,
            "profile.managed_default_content_settings.popups": 2,
            "profile.managed_default_content_settings.geolocation": 2,
            "profile.managed_default_content_settings.media_stream": 2,
        }
        chrome_options.add_experimental_option("prefs", prefs)
        
        return chrome_options
    
    def load_seen_urls(self):
        """
        Load existing seen URLs from JSON file for comparison.
        """
        try:
            if os.path.exists(FDA_SEEN_FILE):
                with open(FDA_SEEN_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict) and "urls" in data:
                        self.seen_urls = set(data["urls"])
                    elif isinstance(data, list):
                        self.seen_urls = set(data)
                    else:
                        self.seen_urls = set()
                self.logger.info(f"Loaded {len(self.seen_urls)} existing URLs from {FDA_SEEN_FILE}")
            else:
                self.seen_urls = set()
                self.logger.info("No existing URLs file found, starting fresh")
        except Exception as e:
            self.logger.warning(f"Error loading seen URLs: {e}")
            self.seen_urls = set()

    
    def _setup_driver(self) -> bool:
        """
        Setup Chrome WebDriver with multiple fallback methods.
        Returns True if successful, False otherwise.
        """
        try:
            self.logger.info("Initializing Chrome WebDriver with enhanced cross-platform support...")
            
            # Method 1: Try system ChromeDriver
            self.logger.info("Trying ChromeDriver method 1/3...")
            try:
                chrome_options = self._get_enhanced_chrome_options()
                
                # Try different ChromeDriver paths
                for path in self._get_chromedriver_paths():
                    try:
                        if os.path.exists(path):
                            service = Service(path)
                            self.driver = webdriver.Chrome(service=service, options=chrome_options)
                            self.logger.info(f"Using system ChromeDriver: {path}")
                            self.logger.info("ChromeDriver method 1 successful")
                            return True
                    except Exception as e:
                        self.logger.debug(f"Failed to use ChromeDriver at {path}: {e}")
                        continue
                
                # Try without specifying path (use system PATH)
                self.driver = webdriver.Chrome(options=chrome_options)
                self.logger.info("Using system ChromeDriver: chromedriver.exe")
                self.logger.info("ChromeDriver method 1 successful")
                return True
                
            except Exception as e:
                self.logger.warning(f"ChromeDriver method 1 failed: {e}")
            
            # Method 2: Try chromedriver_autoinstaller
            if CHROMEDRIVER_AUTOINSTALLER_AVAILABLE:
                self.logger.info("Trying ChromeDriver method 2/3...")
                try:
                    chromedriver_autoinstaller.install()
                    chrome_options = self._get_enhanced_chrome_options()
                    self.driver = webdriver.Chrome(options=chrome_options)
                    self.logger.info("ChromeDriver method 2 successful")
                    return True
                except Exception as e:
                    self.logger.warning(f"ChromeDriver method 2 failed: {e}")
            
            # Method 3: Try webdriver_manager
            if WEBDRIVER_MANAGER_AVAILABLE:
                self.logger.info("Trying ChromeDriver method 3/3...")
                try:
                    chrome_options = self._get_enhanced_chrome_options()
                    service = Service(ChromeDriverManager().install())
                    self.driver = webdriver.Chrome(service=service, options=chrome_options)
                    self.logger.info("ChromeDriver method 3 successful")
                    return True
                except Exception as e:
                    self.logger.warning(f"ChromeDriver method 3 failed: {e}")
            
            self.logger.error("All WebDriver initialization methods failed")
            return False
            
        except Exception as e:
            self.logger.error(f"Unexpected error during WebDriver setup: {e}")
            return False
    
    def scrape_all_recalls(self, max_pages=None, delay=2):
        """
        Scrape all FDA recalls with enhanced error handling.
        
        Args:
            max_pages (int): Maximum number of pages to scrape
            delay (float): Delay between page requests
            
        Returns:
            Dict: Scraping results with new URLs and recalls
        """
        try:
            self.logger.info("Starting FDA recall scraping...")
            start_time = time.time()
            
            # Load existing URLs
            self.load_seen_urls()
            
            # Setup WebDriver
            if not self._setup_driver():
                return {
                    "success": False,
                    "error": "Failed to initialize WebDriver"
                }
            
            # Navigate to FDA recalls page
            self.logger.info(f"Navigating to {self.base_url}")
            self.driver.get(self.base_url)
            
            # Wait for the table to load
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "table#datatable tbody"))
            )
            
            # Wait for DataTables to fully initialize
            self.logger.info("Waiting for DataTables to fully initialize...")
            try:
                # Wait for DataTables wrapper to be present
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".dataTables_wrapper"))
                )
                
                # Wait for pagination to be present
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".dataTables_paginate"))
                )
                
                # Additional wait for DataTables to finish loading
                time.sleep(3)
                self.logger.info("DataTables initialization complete")
                
            except TimeoutException:
                self.logger.warning("DataTables pagination not found, continuing anyway...")
                time.sleep(5)
            
            page_count = 0
            total_recalls = 0
            
            while True:
                if max_pages and page_count >= max_pages:
                    self.logger.info(f"Reached maximum pages limit: {max_pages}")
                    break
                
                page_count += 1
                self.logger.info(f"Scraping page {page_count}")
                
                # Extract recalls from current page
                page_recalls, page_urls = self._extract_recalls_from_page()
                
                # Filter new URLs
                new_recalls = []
                for recall in page_recalls:
                    if recall['url'] not in self.seen_urls:
                        new_recalls.append(recall)
                        self.new_urls.append(recall['url'])
                        self.seen_urls.add(recall['url'])
                
                self.recalls.extend(new_recalls)
                total_recalls += len(page_recalls)
                
                self.logger.info(f"Page {page_count}: {len(page_recalls)} recalls, {len(new_recalls)} new")
                
                # Check if there's a next page
                if not self._navigate_to_next_page():
                    self.logger.info("No more pages found")
                    break
                
                # Rate limiting
                time.sleep(delay)
            
            duration = time.time() - start_time
            
            # Save results
            self._save_results()
            
            # # Send email notification if enabled
            # if self.enable_email:
            #     self._send_email_notification()
            
            self.logger.info(f"Scraping completed in {duration:.2f} seconds")
            self.logger.info(f"Total recalls: {total_recalls}")
            self.logger.info(f"New recalls: {len(self.recalls)}")
            self.logger.info(f"New URLs: {len(self.new_urls)}")
            
            return {
                "success": True,
                "total_recalls": total_recalls,
                "new_recalls": self.recalls,
                "new_urls": self.new_urls,
                "duration": duration
            }
            
        except Exception as e:
            error_msg = f"Fatal error during scraping: {str(e)}"
            self.logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg
            }
    
    def _extract_recalls_from_page(self) -> tuple:
        """Extract recall URLs from the FDA table."""
        recalls = []
        urls = []
        
        try:
            # Wait for the table to load
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "table#datatable tbody"))
            )
            
            # Find all table rows
            table_rows = self.driver.find_elements(By.CSS_SELECTOR, "table#datatable tbody tr")
            
            self.logger.info(f"Found {len(table_rows)} table rows on current page")
            
            for row in table_rows:
                try:
                    # Get all cells in the row
                    cells = row.find_elements(By.CSS_SELECTOR, "td")
                    
                    if len(cells) >= 2:  # Ensure we have at least 2 cells
                        # Brand name is typically in the second cell (index 1)
                        brand_cell = cells[1]
                        
                        # Look for links in the brand cell
                        brand_links = brand_cell.find_elements(By.CSS_SELECTOR, "a")
                        
                        for brand_link in brand_links:
                            href = brand_link.get_attribute('href')
                            if href:
                                # Convert relative URL to absolute URL
                                if href.startswith('/'):
                                    full_url = f"https://www.fda.gov{href}"
                                else:
                                    full_url = href
                                
                                urls.append(full_url)
                                
                                # Create minimal recall data for consistency
                                recall_data = {
                                    'url': full_url,
                                    'brand_name': brand_link.text.strip(),
                                    'scraped_at': datetime.now().isoformat(),
                                    'source': 'FDA'
                                }
                                recalls.append(recall_data)
                                
                except Exception as e:
                    self.logger.warning(f"Error extracting URL from table row: {e}")
                    continue
            
        except Exception as e:
            self.logger.error(f"Error extracting recalls from page: {e}")
        
        self.logger.info(f"Extracted {len(urls)} URLs from table")
        return recalls, urls
    
    def _navigate_to_next_page(self) -> bool:
        """Navigate to next page if available using DataTables pagination."""
        try:
            # Look for DataTables next button - use the correct selectors
            next_selectors = [
                ".paginate_button.next",                # Primary DataTables next button
                "#datatable_next",                      # DataTables next button ID
                ".pagination li.paginate_button.next",  # Alternative selector
                ".next"                                 # Simple next class
            ]
            
            next_link = None
            for selector in next_selectors:
                next_links = self.driver.find_elements(By.CSS_SELECTOR, selector)
                self.logger.info(f"Selector '{selector}' found {len(next_links)} elements")
                if next_links:
                    # Check if the button is enabled (not disabled)
                    next_button = next_links[0]
                    class_name = next_button.get_attribute("class")
                    text = next_button.text.strip()
                    self.logger.info(f"Next button: class='{class_name}', text='{text}'")
                    
                    if "disabled" not in class_name and text.lower() == "next":
                        next_link = next_button
                        self.logger.info(f"Found enabled next page button using selector: {selector}")
                        break
                    else:
                        self.logger.info(f"Next page button found but disabled or wrong text: {selector}")
            
            if next_link:
                # Use JavaScript click directly (more reliable for DataTables)
                self.driver.execute_script("arguments[0].click();", next_link)
                
                # Wait for the table to load on the new page
                try:
                    WebDriverWait(self.driver, 15).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "table#datatable tbody"))
                    )
                    # Additional wait for DataTables to finish loading
                    time.sleep(3)
                except TimeoutException:
                    # Fallback - just wait a bit
                    time.sleep(5)
                
                return True
            else:
                self.logger.info("No next page link found or all next buttons are disabled")
                return False
                
        except Exception as e:
            self.logger.warning(f"Error navigating to next page: {e}")
            return False
    
    def _save_results(self):
        """Save scraped data to JSON file."""
        try:
            output_data = {
                "urls": list(self.seen_urls),
                "recalls": self.recalls,
                "last_updated": datetime.now().isoformat(),
                "total_urls": len(self.seen_urls),
                "new_urls": len(self.new_urls)
            }
            
            # with open("fda_seen_urls.json", "w", encoding="utf-8") as f:
            #     json.dump(output_data, f, indent=2, ensure_ascii=False)
            
            # self.logger.info("Results saved to fda_seen_urls.json")

            with open(FDA_SEEN_FILE, "w", encoding="utf-8") as f:
                json.dump(output_data, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"Results saved to {FDA_SEEN_FILE}")
            
        except Exception as e:
            self.logger.error(f"Error saving results: {e}")
    
    def _send_email_notification(self):
        """Send email notification with new URLs or no updates message."""
        if not self.enable_email:
            return
        
        try:
            if self.new_urls:
                self.logger.info(f"Sending email notification with {len(self.new_urls)} new URLs")
                success = self.email_notifier.send_notification(
                    self.new_urls, 
                    len(self.new_urls),
                    subject_prefix="FDA Recalls Scrapped Links",
                    scraper_name="FDA Scraper"
                )
                if success:
                    self.logger.info("Email notification sent successfully")
                else:
                    self.logger.warning("Failed to send email notification")
            else:
                self.logger.info("Sending email notification: No new URLs found")
                success = self.email_notifier.send_notification(
                    [], 
                    0,
                    subject_prefix="FDA Recalls Scrapped Links - No Updates",
                    scraper_name="FDA Scraper",
                    no_urls_found=True
                )
                if success:
                    self.logger.info("No updates email notification sent successfully")
                else:
                    self.logger.warning("Failed to send no updates email notification")
                
        except Exception as e:
            self.logger.error(f"Error sending email notification: {e}")
    
    def close(self):
        """Close the WebDriver."""
        if self.driver:
            try:
                self.driver.quit()
                self.logger.info("WebDriver closed successfully")
            except Exception as e:
                self.logger.warning(f"Error closing WebDriver: {e}")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


def main():
    """Main function for testing the scraper."""
    scraper = FDASeleniumScraper(headless=True, enable_email=False)
    try:
        result = scraper.scrape_all_recalls(max_pages=2)
        print(f"Scraping result: {result}")
    finally:
        scraper.close()


if __name__ == "__main__":
    main()
