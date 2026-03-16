#!/usr/bin/env python3
import json
import time
import logging
import os
from datetime import datetime, timedelta
from typing import List, Dict, Set, Optional
from notifier.notifier import EmailNotifier

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "scraper_config.json")
PROGRESS_DIR = os.path.join(BASE_DIR, "data", "progress")
os.makedirs(PROGRESS_DIR, exist_ok=True)
DEFAULT_PROGRESS_FILE = os.path.join(PROGRESS_DIR, "batch_progress.json")

LOG_DIR = os.path.join(BASE_DIR, "logs")
LOG_FILE = os.path.join(LOG_DIR, "batch_notifier.log")


class BatchNotifier:
    """
    Enhanced batch notifier that ALWAYS sends email notifications.
    """
    
    def __init__(self, batch_size: int = 20, delay_minutes: int = 15, progress_file: str = DEFAULT_PROGRESS_FILE):
        """Initialize the batch notifier."""
        self.batch_size = batch_size
        self.delay_minutes = delay_minutes
        self.delay_seconds = delay_minutes * 60
        self.progress_file = progress_file
        
        # Initialize email notifier
        self.email_notifier = EmailNotifier(config_file=CONFIG_PATH)
        
        # Setup logging
        self.logger = self._setup_logging()
        
        # Load progress data
        self.progress_data = self._load_progress()
        
    def _setup_logging(self) -> logging.Logger:
        """Setup logging for batch operations."""
        logger = logging.getLogger("BatchNotifier")
        logger.setLevel(logging.INFO)
        logger.handlers.clear()
        
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        file_handler = logging.FileHandler(LOG_FILE, encoding='utf-8')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
        return logger
    
    def _load_progress(self) -> Dict:
        """Load progress data from file."""
        if os.path.exists(self.progress_file):
            try:
                with open(self.progress_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, KeyError) as e:
                self.logger.warning(f"Error loading progress file: {e}. Starting fresh.")
        
        return {
            "sent_batches": 0,
            "total_urls_sent": 0,
            "sent_urls": [],
            "last_batch_time": None,
            "last_batch_number": 0,
            "total_batches_planned": 0,
            "scraper_results": {}
        }
    
    def _save_progress(self):
        """Save current progress to file."""
        try:
            with open(self.progress_file, 'w', encoding='utf-8') as f:
                json.dump(self.progress_data, f, indent=2, ensure_ascii=False)
            self.logger.debug("Progress saved successfully")
        except Exception as e:
            self.logger.error(f"Error saving progress: {e}")
    
    def _get_sent_urls_set(self) -> Set[str]:
        """Get set of already sent URLs."""
        return set(self.progress_data.get("sent_urls", []))
    
    def _add_sent_urls(self, urls: List[str]):
        """Add URLs to the sent URLs list."""
        sent_urls = self._get_sent_urls_set()
        sent_urls.update(urls)
        self.progress_data["sent_urls"] = list(sent_urls)
        self.progress_data["total_urls_sent"] = len(sent_urls)
    
    def _get_new_urls(self, all_urls: List[str]) -> List[str]:
        """Filter out URLs that have already been sent."""
        sent_urls = self._get_sent_urls_set()
        new_urls = [url for url in all_urls if url not in sent_urls]
        
        self.logger.info(f"Total URLs provided: {len(all_urls)}")
        self.logger.info(f"Already sent URLs: {len(sent_urls)}")
        self.logger.info(f"New URLs to send: {len(new_urls)}")
        
        return new_urls
    
    def _create_batches(self, urls: List[str]) -> List[List[str]]:
        """Split URLs into batches of specified size."""
        batches = []
        for i in range(0, len(urls), self.batch_size):
            batch = urls[i:i + self.batch_size]
            batches.append(batch)
        
        self.logger.info(f"Created {len(batches)} batches from {len(urls)} URLs")
        return batches
    
    def _send_batch(self, batch: List[str], batch_number: int, total_batches: int, scraper_name: str) -> bool:
        """Send a single batch of URLs."""
        try:
            self.logger.info(f"\n{'='*60}")
            self.logger.info(f"SENDING BATCH {batch_number}/{total_batches} ({len(batch)} URLs)")
            self.logger.info(f"{'='*60}")
            
            # Simple subject line
            subject = f"{scraper_name} Recalls Scrapped Links"
            
            # Batch information goes in the body
            batch_info = {
                'batch_number': batch_number,
                'total_batches': total_batches
            }
            
            # Send email notification with batch info in body
            success = self.email_notifier.send_notification(
                batch, 
                len(batch), 
                subject_prefix=subject,
                scraper_name=f"{scraper_name}",
                batch_info=batch_info
            )
            
            if success:
                self.logger.info(f"✅ Batch {batch_number} sent successfully")
                
                # Update progress
                self._add_sent_urls(batch)
                self.progress_data["sent_batches"] += 1
                self.progress_data["last_batch_time"] = datetime.now().isoformat()
                self.progress_data["last_batch_number"] = batch_number
                self._save_progress()
                
                return True
            else:
                self.logger.error(f"❌ Failed to send batch {batch_number}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error sending batch {batch_number}: {e}")
            return False
    
    def _wait_for_next_batch(self, batch_number: int, total_batches: int):
        """Wait for the specified delay before next batch."""
        if batch_number < total_batches:
            next_time = datetime.now() + timedelta(minutes=self.delay_minutes)
            self.logger.info(f"\n⏳ Waiting {self.delay_minutes} minutes before next batch...")
            self.logger.info(f"Next batch will be sent at: {next_time.strftime('%Y-%m-%d %H:%M:%S')}")
            
            # Wait with progress updates every 5 minutes
            for minute in range(0, self.delay_minutes, 5):
                time.sleep(300)  # Wait 5 minutes
                remaining = self.delay_minutes - minute - 5
                if remaining > 0:
                    self.logger.info(f"⏳ {remaining} minutes remaining until next batch...")
            
            # Wait for any remaining time
            remaining_seconds = (self.delay_minutes * 60) % 300
            if remaining_seconds > 0:
                time.sleep(remaining_seconds)
    
    def send_urls_in_batches(self, urls: List[str], scraper_name: str = "Unknown") -> Dict:
        """
        Send URLs in batches with delays.
        FIXED: ALWAYS sends email, even when 0 URLs.
        """
        self.logger.info(f"\n{'='*60}")
        self.logger.info(f"BATCH NOTIFICATION: {scraper_name.upper()}")
        self.logger.info(f"{'='*60}")
        
        # Filter out already sent URLs
        new_urls = self._get_new_urls(urls)
        
        # CRITICAL FIX: Always send email notification
        if not new_urls:
            self.logger.info("No new URLs found - sending 'No URLs Found' notification")
            
            try:
                subject = f"{scraper_name} Recalls Scrapped Links"
                success = self.email_notifier.send_notification(
                    [],  # Empty URL list
                    0,
                    subject_prefix=subject,
                    scraper_name=scraper_name,
                    batch_info=None,
                    no_urls_found=True  # Special flag
                )
                
                if success:
                    self.logger.info("✅ 'No URLs Found' email sent successfully")
                else:
                    self.logger.warning("❌ Failed to send 'No URLs Found' email")
                    
            except Exception as e:
                self.logger.error(f"Error sending 'No URLs Found' email: {e}")
            
            return {
                "success": True,
                "total_urls": len(urls),
                "new_urls": 0,
                "batches_sent": 0,
                "email_sent": success if 'success' in locals() else False,
                "message": "No new URLs - notification email sent"
            }
        
        # Create batches
        batches = self._create_batches(new_urls)
        total_batches = len(batches)
        
        # Update progress
        self.progress_data["total_batches_planned"] = total_batches
        if "scraper_results" not in self.progress_data:
            self.progress_data["scraper_results"] = {}
        if "last_batch_number" not in self.progress_data:
            self.progress_data["last_batch_number"] = 0
        self.progress_data["scraper_results"][scraper_name] = {
            "total_urls": len(urls),
            "new_urls": len(new_urls),
            "batches_planned": total_batches
        }
        self._save_progress()
        
        self.logger.info(f"Created {total_batches} batches from {len(new_urls)} new URLs")
        
        # Send batches
        successful_batches = 0
        failed_batches = 0
        
        for i, batch in enumerate(batches, 1):
            batch_number = self.progress_data.get("last_batch_number", 0) + i
            
            success = self._send_batch(batch, batch_number, total_batches, scraper_name)
            
            if success:
                successful_batches += 1
            else:
                failed_batches += 1
                self.logger.error(f"Batch {batch_number} failed - stopping batch sending")
                break
            
            # Wait before next batch
            if i < total_batches:
                self._wait_for_next_batch(i, total_batches)
        
        # Final summary
        self.logger.info(f"\n{'='*60}")
        self.logger.info(f"BATCH COMPLETED: {scraper_name.upper()}")
        self.logger.info(f"{'='*60}")
        
        return {
            "success": failed_batches == 0,
            "total_urls": len(urls),
            "new_urls": len(new_urls),
            "batches_sent": successful_batches,
            "batches_failed": failed_batches,
            "total_batches_planned": total_batches,
            "email_sent": True
        }
    
    def send_urls_by_scraper(self, urls_by_scraper: Dict[str, List[str]]) -> Dict:
        """
        Send URLs for multiple scrapers.
        FIXED: Each scraper gets its own email, even if 0 URLs.
        """
        self.logger.info(f"\n{'='*60}")
        self.logger.info("BATCH NOTIFICATION: MULTIPLE SCRAPERS")
        self.logger.info(f"{'='*60}")
        
        results = {}
        total_new_urls = 0
        total_batches_sent = 0
        
        # CRITICAL: Process ALL scrapers, even those with empty URL lists
        for scraper_name, urls in urls_by_scraper.items():
            self.logger.info(f"\nProcessing {scraper_name}: {len(urls)} URLs")
            
            # Send batches for this scraper (will send "No URLs" email if urls is empty)
            result = self.send_urls_in_batches(urls, scraper_name)
            results[scraper_name] = result
            
            total_new_urls += result.get("new_urls", 0)
            total_batches_sent += result.get("batches_sent", 0)
        
        # Overall summary
        self.logger.info(f"\n{'='*60}")
        self.logger.info("OVERALL BATCH SUMMARY")
        self.logger.info(f"{'='*60}")
        self.logger.info(f"Scrapers processed: {len(results)}")
        self.logger.info(f"Total new URLs: {total_new_urls}")
        self.logger.info(f"Total batches sent: {total_batches_sent}")
        
        return {
            "success": all(r.get("success", False) for r in results.values()),
            "scrapers": results,
            "total_new_urls": total_new_urls,
            "total_batches_sent": total_batches_sent
        }
    
    def get_progress_summary(self) -> Dict:
        """Get current progress summary."""
        return {
            "sent_batches": self.progress_data.get("sent_batches", 0),
            "total_urls_sent": self.progress_data.get("total_urls_sent", 0),
            "last_batch_time": self.progress_data.get("last_batch_time"),
            "last_batch_number": self.progress_data.get("last_batch_number", 0),
            "total_batches_planned": self.progress_data.get("total_batches_planned", 0),
            "scraper_results": self.progress_data.get("scraper_results", {})
        }
    
    def reset_progress(self):
        """Reset all progress data."""
        self.progress_data = {
            "sent_batches": 0,
            "total_urls_sent": 0,
            "sent_urls": [],
            "last_batch_time": None,
            "last_batch_number": 0,
            "total_batches_planned": 0,
            "scraper_results": {}
        }
        self._save_progress()
        self.logger.info("Progress data reset successfully")


if __name__ == "__main__":
    # Test with empty URLs to verify "No URLs Found" email
    print("Testing Batch Notifier with empty URLs...")
    
    notifier = BatchNotifier(batch_size=20, delay_minutes=0.1)
    
    # Test with empty URL lists
    urls_by_scraper = {
        "CPSC": [],  # Empty - should send "No URLs Found" email
        "FDA": []    # Empty - should send "No URLs Found" email
    }
    
    result = notifier.send_urls_by_scraper(urls_by_scraper)
    print(f"\nTest result: {result}")
    print("\nCheck your email inbox for 'No URLs Found' notifications!")
