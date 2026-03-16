#!/usr/bin/env python3
import os
import sys
import json
import time
import logging
import platform
import subprocess
import atexit
from typing import Dict, List, Any
from scoutyourcase_productrecall_scraper import ScoutYourCaseProductRecallScraper


# main.py (near the imports)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "scraper_config.json")

# Optional: if you are using data/seen and data/progress folders:
SEEN_DIR = os.path.join(BASE_DIR, "data", "seen")
PROGRESS_DIR = os.path.join(BASE_DIR, "data", "progress")

os.makedirs(SEEN_DIR, exist_ok=True)
os.makedirs(PROGRESS_DIR, exist_ok=True)
from fsis_selenium_scraper import FSISSeleniumScraper   

# ==================== CONFIGURATION ====================
# This change hardcodes the configuration path to avoid fallback to environment variables
def load_scraper_config():
    """Load configuration from scraper_config.json file."""
    config_path = CONFIG_PATH
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        print(f"Loaded configuration from {config_path}")
        return config
    except FileNotFoundError:
        print(f"Configuration file {config_path} not found!")
        return {}
    except json.JSONDecodeError as e:
        print(f"Error parsing {config_path}: {e}")
        return {}
    except Exception as e:
        print(f"Error loading {config_path}: {e}")
        return {}

# Load configuration from JSON file
config = load_scraper_config()

EMAIL_SENDER = config.get('EMAIL_USERNAME', '').strip()

# Email Settings - Load from scraper_config.json
EMAIL_SENDER = config.get('EMAIL_USERNAME', '').strip()
print(EMAIL_SENDER)
EMAIL_PASSWORD = config.get('EMAIL_PASSWORD', '').strip()
EMAIL_RECIPIENTS_STR = config.get('RECEIVER_EMAIL', '').strip()
EMAIL_RECIPIENTS = [r.strip() for r in EMAIL_RECIPIENTS_STR.split(',') if r.strip()]
SMTP_SERVER = config.get('EMAIL_SMTP_HOST', 'smtp-mail.outlook.com').strip()
SMTP_PORT = int(config.get('EMAIL_SMTP_PORT', '587').strip())
EMAIL_USE_SSL = config.get('EMAIL_USE_SSL', 'false').lower().strip() == 'true'
FSIS_ENABLED = config.get("FSIS_ENABLED", "false").lower().strip() == "true"
FSIS_MAX_PAGES = int(config.get("FSIS_MAX_PAGES", "0").strip())
FSIS_AVAILABLE = True   # mirror what you did for CPSC_AVAILABLE / FDA_AVAILABLE

def as_bool(v, default=False) -> bool:
    if v is None:
        return default
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return bool(v)
    if isinstance(v, str):
        return v.strip().lower() in ("1", "true", "yes", "y", "on")
    return default

def as_int(v, default=0) -> int:
    try:
        if v is None:
            return default
        if isinstance(v, (int, float)):
            return int(v)
        return int(str(v).strip())
    except Exception:
        return default


SCOUT_ENABLED = as_bool(config.get("SCOUT_ENABLED"), default=False)
SCOUT_MAX_PAGES = as_int(config.get("SCOUT_MAX_PAGES"), default=50)

try:
    SCOUT_MAX_PAGES = int(str(config.get("SCOUT_MAX_PAGES", "50")).strip())
except Exception:
    SCOUT_MAX_PAGES = 50

SCOUT_AVAILABLE = True


# ================== DIRECT EMAIL SETTINGS (TEST ONLY) ==================
# EMAIL_SENDER = "meetings@zlk.com"
# EMAIL_PASSWORD = "wer!23de5779yYutRRT"
# EMAIL_RECIPIENTS = ['teammarketinglnk@gmail.com', 'sgarad@zlk.com']


# #Outlook defaults
# SMTP_SERVER = "smtp-mail.outlook.com"
# SMTP_PORT = 587
# EMAIL_USE_SSL = False
# EMAIL_USE_STARTTLS = True

# ==============================================================================
### Added quick debug print to verify JSON configuration
print("\n Email Configuration Loaded from scraper_config.json:")
print(f"  EMAIL_SENDER: {EMAIL_SENDER or '[MISSING]'}")
print(f"  EMAIL_RECIPIENTS: {EMAIL_RECIPIENTS or '[MISSING]'}")
print(f"  SMTP_SERVER: {SMTP_SERVER}")
print(f"  SMTP_PORT: {SMTP_PORT}")
print(f"  EMAIL_USE_SSL: {EMAIL_USE_SSL}")
print("=" * 60 + "\n")

print(" Scraper Flags:")
print(f"  FSIS_ENABLED: {FSIS_ENABLED}, FSIS_MAX_PAGES: {FSIS_MAX_PAGES}")
print(f"  SCOUT_ENABLED: {SCOUT_ENABLED}, SCOUT_MAX_PAGES: {SCOUT_MAX_PAGES}")
print("=" * 60 + "\n")

# Scraper Settings
CPSC_ENABLED = True
CPSC_MAX_PAGES = 10
FDA_ENABLED = True
FDA_MAX_PAGES = 115

# General Settings
HEADLESS_MODE = True
BATCH_SIZE = 20
BATCH_DELAY_MINUTES = 1
# USE_BATCH_NOTIFICATION = True
USE_BATCH_NOTIFICATION = False
LOG_FILE = "scraper.log"

# Platform Detection
IS_LINUX = platform.system() == "Linux"
IS_WINDOWS = platform.system() == "Windows"

# ==================== IMPORTS ====================

try:
    from cpsc_links_scraper import CPSCScraper
    CPSC_AVAILABLE = True
except ImportError as e:
    print(f"⚠️  CPSC scraper not available: {e}")
    CPSC_AVAILABLE = False

try:
    from fda_selenium_scraper import FDASeleniumScraper
    FDA_AVAILABLE = True
except ImportError as e:
    print(f" FDA scraper not available: {e}")
    FDA_AVAILABLE = False

try:
    from notifier import EmailNotifier
    EMAIL_AVAILABLE = True
except ImportError as e:
    print(f" Email notifier not available: {e}")
    EMAIL_AVAILABLE = False

try:
    from batch_notifier import BatchNotifier
    BATCH_AVAILABLE = True
except ImportError as e:
    print(f" Batch notifier not available: {e}")
    BATCH_AVAILABLE = False


class UnifiedScraper:
    """Main scraper orchestrator."""
    
    def __init__(self):
        """Initialize the scraper."""
        self.logger = self._setup_logging()
        self.results = {}
        self.xvfb_process = None
        
        # Register cleanup
        atexit.register(self._cleanup)
        
        # Show security warning if needed
        self._check_security()
        
        # Initialize batch notifier
        if USE_BATCH_NOTIFICATION and BATCH_AVAILABLE:
            try:
                self.batch_notifier = BatchNotifier(
                    batch_size=BATCH_SIZE,
                    delay_minutes=BATCH_DELAY_MINUTES
                )
                self.logger.info(" Batch notification enabled")
            except Exception as e:
                self.logger.error(f" Failed to initialize batch notifier: {e}")
                self.batch_notifier = None
        else:
            self.batch_notifier = None
        
        # Setup platform-specific environment
        if IS_LINUX:
            self._setup_linux()
    
    def _setup_logging(self) -> logging.Logger:
        """Setup logging."""
        logger = logging.getLogger("UnifiedScraper")
        logger.setLevel(logging.INFO)
        logger.handlers.clear()
        
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        )
        
        # File handler
        try:
            fh = logging.FileHandler(LOG_FILE, encoding='utf-8')
            fh.setFormatter(formatter)
            logger.addHandler(fh)
        except Exception as e:
            print(f"  Could not create log file: {e}")
        
        # Console handler
        ch = logging.StreamHandler(sys.stdout)
        ch.setFormatter(formatter)
        logger.addHandler(ch)
        
        return logger
    
    def _check_security(self):
        """Check if credentials are configured."""
        if not EMAIL_SENDER or not EMAIL_PASSWORD:
            self.logger.warning("\n" + "="*60)
            self.logger.warning("  EMAIL CREDENTIALS NOT CONFIGURED!")
            self.logger.warning("="*60)
            self.logger.warning("Update scraper_config.json with:")
            self.logger.warning("  EMAIL_USERNAME: 'your-email@example.com'")
            self.logger.warning("  EMAIL_PASSWORD: 'your-password'")
            self.logger.warning("  RECEIVER_EMAIL: 'recipient@example.com'")
            self.logger.warning("="*60 + "\n")

    def _setup_linux(self):
        """Setup Linux environment."""
        try:
            # Set display
            if not os.environ.get('DISPLAY'):
                os.environ['DISPLAY'] = ':99'
            
            # Try to start Xvfb
            try:
                result = subprocess.run(['pgrep', '-f', 'Xvfb :99'], 
                                      capture_output=True, text=True)
                if result.returncode != 0:
                    self.xvfb_process = subprocess.Popen([
                        'Xvfb', ':99', '-screen', '0', '1920x1080x24'
                    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    time.sleep(2)
                    self.logger.info(" Started Xvfb")
            except Exception as e:
                self.logger.warning(f"  Could not start Xvfb: {e}")
                
        except Exception as e:
            self.logger.warning(f"  Linux setup error: {e}")
    
    def _cleanup(self):
        """Cleanup resources."""
        try:
            if self.xvfb_process and self.xvfb_process.poll() is None:
                self.xvfb_process.terminate()
                try:
                    self.xvfb_process.wait(timeout=5)
                    self.logger.info(" Cleaned up Xvfb")
                except subprocess.TimeoutExpired:
                    self.xvfb_process.kill()
                    self.logger.warning("  Forced Xvfb kill")
        except Exception as e:
            self.logger.warning(f"  Cleanup error: {e}")
    
    def run_cpsc_scraper(self) -> Dict[str, Any]:
        """Run CPSC scraper."""
        if not CPSC_ENABLED:
            return {"skipped": True, "reason": "disabled"}
        
        if not CPSC_AVAILABLE:
            return {"skipped": True, "reason": "not available"}
        
        try:
            self.logger.info("\n" + "="*60)
            self.logger.info(" Running CPSC Scraper")
            self.logger.info("="*60)
            
            start_time = time.time()
            scraper = CPSCScraper(headless=HEADLESS_MODE)
            
            links = scraper.scrape_all_links(
                start_page=0,
                end_page=CPSC_MAX_PAGES-1 if CPSC_MAX_PAGES > 0 else None
            )
            
            scraper.save_links()
            scraper.close()
            
            duration = time.time() - start_time
            
            self.logger.info(f" CPSC completed: {len(links)} new links in {duration:.2f}s")
            
            return {
                "scraper_name": "CPSC",
                "success": True,
                "new_links": len(links),
                "new_urls": links,
                "duration": duration
            }
            
        except Exception as e:
            self.logger.error(f" CPSC error: {e}")
            return {
                "scraper_name": "CPSC",
                "success": False,
                "error": str(e),
                "new_urls": []
            }
    
    def run_fda_scraper(self) -> Dict[str, Any]:
        """Run FDA scraper."""
        if not FDA_ENABLED:
            return {"skipped": True, "reason": "disabled"}
        
        if not FDA_AVAILABLE:
            return {"skipped": True, "reason": "not available"}
        
        try:
            self.logger.info("\n" + "="*60)
            self.logger.info(" Running FDA Scraper")
            self.logger.info("="*60)
            
            start_time = time.time()
            scraper = FDASeleniumScraper(headless=HEADLESS_MODE, enable_email=True)
            
            result = scraper.scrape_all_recalls(
                max_pages=FDA_MAX_PAGES if FDA_MAX_PAGES > 0 else None,
                delay=0.5
            )
            
            scraper.close()
            duration = time.time() - start_time
            
            if result.get("success"):
                new_urls = result.get("new_urls", [])
                self.logger.info(f" FDA completed: {len(new_urls)} new URLs in {duration:.2f}s")
                
                return {
                    "scraper_name": "FDA",
                    "success": True,
                    "new_urls": new_urls,
                    "duration": duration
                }
            else:
                self.logger.error(f" FDA error: {result.get('error', 'Unknown')}")
                return {
                    "scraper_name": "FDA",
                    "success": False,
                    "error": result.get("error", "Unknown"),
                    "new_urls": []
                }
                
        except Exception as e:
            self.logger.error(f" FDA error: {e}")
            return {
                "scraper_name": "FDA",
                "success": False,
                "error": str(e),
                "new_urls": []
            }
    
    def run_fsis_scraper(self) -> Dict[str, Any]:
        """Run FSIS scraper."""
        if not FSIS_ENABLED:
            return {"skipped": True, "reason": "disabled"}

        if not FSIS_AVAILABLE:
            return {"skipped": True, "reason": "not available"}

        try:
            self.logger.info("\n" + "="*60)
            self.logger.info(" Running FSIS Scraper")
            self.logger.info("="*60)

            start_time = time.time()
            scraper = FSISSeleniumScraper(
                headless=HEADLESS_MODE,
                max_pages=FSIS_MAX_PAGES if FSIS_MAX_PAGES > 0 else None
            )

            result = scraper.scrape_all_recalls()
            scraper.close()
            duration = time.time() - start_time

            if result.get("success"):
                new_urls = result.get("new_urls", [])
                self.logger.info(f" FSIS completed: {len(new_urls)} new URLs in {duration:.2f}s")

                return {
                    "scraper_name": "FSIS",
                    "success": True,
                    "new_urls": new_urls,
                    "duration": duration
                }
            else:
                self.logger.error(f" FSIS error: {result.get('error', 'Unknown')}")
                return {
                    "scraper_name": "FSIS",
                    "success": False,
                    "error": result.get("error", "Unknown"),
                    "new_urls": []
                }

        except Exception as e:
            self.logger.error(f" FSIS error: {e}")
            return {
                "scraper_name": "FSIS",
                "success": False,
                "error": str(e),
                "new_urls": []
            }
        
    def run_scout_scraper(self) -> Dict[str, Any]:
        """Run ScoutYourCase Product Recall scraper."""
        if not SCOUT_ENABLED:
            return {"skipped": True, "reason": "disabled"}

        if not SCOUT_AVAILABLE:
            return {"skipped": True, "reason": "not available"}

        try:
            self.logger.info("\n" + "="*60)
            self.logger.info(" Running SCOUT (Product Recall) Scraper")
            self.logger.info("="*60)

            start_time = time.time()

            scraper = ScoutYourCaseProductRecallScraper(
                start_url="https://ld.scoutyourcase.com/index",     
                max_clicks=SCOUT_MAX_PAGES if SCOUT_MAX_PAGES > 0 else 30,  
                click_pause=1.0,                                    
                headless=False,                             
                debug=True,
                timeout=20,
            )

            result = scraper.scrape()
            scraper.close()
            duration = time.time() - start_time

            if result.get("success"):
                new_urls = result.get("new_urls", [])
                self.logger.info(f" SCOUT completed: {len(new_urls)} new URLs in {duration:.2f}s")
                return {
                    "scraper_name": "SCOUT",
                    "success": True,
                    "new_urls": new_urls,
                    "duration": duration
                }

            self.logger.error(f" SCOUT error: {result.get('error', 'Unknown')}")
            return {
                "scraper_name": "SCOUT",
                "success": False,
                "error": result.get("error", "Unknown"),
                "new_urls": []
            }

        except Exception as e:
            self.logger.error(f" SCOUT error: {e}")
            return {"scraper_name": "SCOUT", "success": False, "error": str(e), "new_urls": []}





    def _send_batch_notifications(self, results: Dict[str, Any]):
        """Send batch notifications."""
        if not USE_BATCH_NOTIFICATION or not self.batch_notifier:
            return {"skipped": True}
        
        try:
            # Collect URLs by scraper - INCLUDE ALL successful scrapers, even with 0 URLs
            urls_by_scraper = {}
            
            for scraper_name, result in results.items():
                # Include scraper if it ran successfully (even if 0 URLs found)
                if result.get("success") or (result.get("success") is not False and not result.get("skipped")):
                    urls_by_scraper[scraper_name] = result.get("new_urls", [])
            
            if not urls_by_scraper:
                self.logger.info("  No scrapers ran successfully")
                return {"skipped": True}
            
            # Send batches
            self.logger.info("\n" + "="*60)
            self.logger.info(" Sending Batch Notifications")
            self.logger.info("="*60)
            
            batch_result = self.batch_notifier.send_urls_by_scraper(urls_by_scraper)
            
            self.logger.info(" Batch notification complete")
            self.logger.info(f"   Total batches: {batch_result.get('total_batches_sent', 0)}")
            
            return batch_result
            
        except Exception as e:
            self.logger.error(f" Batch notification error: {e}")
            return {"success": False, "error": str(e)}
    
    def run_all(self) -> Dict[str, Any]:
        """Run all scrapers and send a single combined digest email."""
        from notifier import EmailNotifier  # local import to avoid cycles

        self.logger.info("\n" + "="*60)
        self.logger.info(" STARTING UNIFIED SCRAPER")
        self.logger.info("="*60)
        self.logger.info(f"Platform: {platform.system()}")
        self.logger.info(f"CPSC: {'ON' if CPSC_ENABLED else 'OFF'}")
        self.logger.info(f"FDA:  {'ON' if FDA_ENABLED else 'OFF'}")
        self.logger.info(f"FSIS: {'ON' if FSIS_ENABLED else 'OFF'}")
        self.logger.info(f"SCOUT: {'ON' if SCOUT_ENABLED else 'OFF'}")
        self.logger.info(f"Batch: {'ON' if USE_BATCH_NOTIFICATION else 'OFF'}")

        overall_start = time.time()
        results: Dict[str, Any] = {}

        # -------- CPSC --------
        if CPSC_ENABLED and CPSC_AVAILABLE:
            results["CPSC"] = self.run_cpsc_scraper()
        else:
            results["CPSC"] = {"success": False, "skipped": True, "new_urls": []}

        # -------- FDA ---------
        if FDA_ENABLED and FDA_AVAILABLE:
            results["FDA"] = self.run_fda_scraper()
        else:
            results["FDA"] = {"success": False, "skipped": True, "new_urls": []}

        # -------- FSIS --------
        if FSIS_ENABLED and FSIS_AVAILABLE:
            results["FSIS"] = self.run_fsis_scraper()
        else:
            results["FSIS"] = {"success": False, "skipped": True, "new_urls": []}

        # -------- SCOUT --------
        if SCOUT_ENABLED and SCOUT_AVAILABLE:
            results["SCOUT"] = self.run_scout_scraper()
        else:
            results["SCOUT"] = {"success": False, "skipped": True, "new_urls": []}

        self.logger.info(
            f"SCOUT run result: success={results['SCOUT'].get('success')} "
            f"new_urls={len(results['SCOUT'].get('new_urls', []))} "
            f"error={results['SCOUT'].get('error')}"
        )

        # Optional: per-scraper/batch notifications (no-op if flag is OFF)
        batch_result = self._send_batch_notifications(results)

        # ---- Single combined digest email (one email per run) ----
        try:
            notifier = EmailNotifier(config_file=CONFIG_PATH)

            cpsc_urls = results.get("CPSC", {}).get("new_urls", []) if results.get("CPSC", {}).get("success") else []
            fda_urls  = results.get("FDA",  {}).get("new_urls", []) if results.get("FDA",  {}).get("success")  else []
            fsis_urls = results.get("FSIS", {}).get("new_urls", []) if results.get("FSIS", {}).get("success") else []
            scout_urls = results.get("SCOUT", {}).get("new_urls", []) if results.get("SCOUT", {}).get("success") else []

            combined = (cpsc_urls or []) + (fda_urls or []) + (fsis_urls or []) + (scout_urls or [])
            count = len(combined)

            batch_info = {
                "CPSC": len(cpsc_urls),
                "FDA":  len(fda_urls),
                "FSIS": len(fsis_urls),
                "SCOUT": len(scout_urls),
            }

            self.logger.info(
                " Sending combined digest email "
                f"(CPSC={batch_info['CPSC']}, FDA={batch_info['FDA']}, FSIS={batch_info['FSIS']}, SCOUT={batch_info['SCOUT']})"
            )

            notifier.send_notification(
                combined,
                count,
                subject_prefix="Daily Product Recall Links",
                scraper_name="CPSC + FDA + FSIS + SCOUT Digest",
                batch_info=batch_info,
                no_urls_found=(count == 0),
            )
        except Exception as e:
            self.logger.warning(f"  Combined digest email failed: {e}")

        # ---- Summary ----
        overall_duration = time.time() - overall_start
        successful = sum(1 for r in results.values() if r.get("success"))
        failed = sum(
            1
            for r in results.values()
            if not r.get("success") and not r.get("skipped")
        )
        total_urls = sum(len(r.get("new_urls", [])) for r in results.values())

        self.logger.info("\n" + "="*60)
        self.logger.info(" SUMMARY")
        self.logger.info("="*60)
        self.logger.info(f"Successful: {successful}")
        self.logger.info(f"Failed: {failed}")
        self.logger.info(f"Total URLs: {total_urls}")
        self.logger.info(f"Duration: {overall_duration:.2f}s")
        self.logger.info("="*60 + "\n")

        return {
            "success": failed == 0,
            "results": results,
            "batch_result": batch_result,
            "total_urls": total_urls,
            "duration": overall_duration,
        }


def test_email():
    """Test email configuration."""
    print("\n" + "="*60)
    print(" TESTING EMAIL CONFIGURATION")
    print("="*60)
    
    if not EMAIL_SENDER or not EMAIL_PASSWORD:
        print(" Email credentials not configured")
        print("Update scraper_config.json with EMAIL_USERNAME and EMAIL_PASSWORD")
        return False
    
    if not EMAIL_RECIPIENTS:
        print(" No recipients configured")
        print("Update scraper_config.json with RECEIVER_EMAIL")
        return False
    
    if not EMAIL_AVAILABLE:
        print(" Email notifier not available")
        return False
    
    try:
        notifier = EmailNotifier()
        test_urls = ["https://example.com/test-1", "https://example.com/test-2"]
        
        print(f"\nSending test email to: {', '.join(EMAIL_RECIPIENTS)}")
        success = notifier.send_notification(
            test_urls,
            2,
            "🧪 Test Email - Scraper",
            "Test Scraper"
        )
        
        if success:
            print("\n Email test PASSED!")
        else:
            print("\n Email test FAILED!")
        
        return success
        
    except Exception as e:
        print(f"\n Error: {e}")
        return False


def main():
    """Main entry point."""
    print("\n" + "="*60)
    print("PRODUCT RECALLS SCRAPER")
    print("="*60)
    
    # Check credentials
    if not EMAIL_SENDER or not EMAIL_PASSWORD:
        print("\n  WARNING: Email credentials not configured!")
        print("Update scraper_config.json with:")
        print("  EMAIL_USERNAME: 'your-email@example.com'")
        print("  EMAIL_PASSWORD: 'your-password'")
        print("  RECEIVER_EMAIL: 'recipient@example.com'")
        print("\nSee SECURITY_README.md for details.")
        print("="*60)
    
    try:
        scraper = UnifiedScraper()
        result = scraper.run_all()
        
        if result.get("success"):
            print("\n All scrapers completed successfully!")
            return 0
        else:
            print("\n  Some scrapers failed. Check logs.")
            return 1
            
    except KeyboardInterrupt:
        print("\n  Interrupted by user")
        return 1
    except Exception as e:
        print(f"\n Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "--test-email":
            sys.exit(0 if test_email() else 1)
        elif sys.argv[1] == "--help":
            print("Usage:")
            print("  python main.py              # Run scraper")
            print("  python main.py --test-email # Test email")
            print("  python main.py --help       # Show help")
            sys.exit(0)
        else:
            print(f"Unknown argument: {sys.argv[1]}")
            print("Use --help for options")
            sys.exit(1)
    else:
        sys.exit(main())
