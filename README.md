# Product Recalls Scraper with Batch Notifications

A comprehensive web scraping system that collects product recall data from CPSC and FDA websites and sends URLs in controlled batches.

## Features

- **Dual Scrapers**: CPSC and FDA recall data collection
- **Batch Notifications**: Sends URLs in batches of 20 with 15-minute delays
- **Progress Tracking**: Resumes from where it left off if interrupted
- **Duplicate Prevention**: Never sends the same URL twice
- **Comprehensive Logging**: Detailed logs with timestamps

## Quick Start

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Run the scraper**:
   ```bash
   python main.py
   ```

3. **Check batch status**:
   ```bash
   python main.py --batch-status
   ```

4. **Reset progress** (if needed):
   ```bash
   python main.py --reset-batch
   ```

## Configuration

Edit settings in `main.py`:

```python
# Batch Notification Settings
BATCH_SIZE = 20                    # URLs per batch
BATCH_DELAY_MINUTES = 15           # Delay between batches
USE_BATCH_NOTIFICATION = True      # Enable batch mode

# Email Settings
EMAIL_SENDER = "your-email@domain.com"
EMAIL_PASSWORD = "your-password"
EMAIL_RECIPIENTS = ["recipient@domain.com"]
```

## How It Works

1. **Scraping**: Collects URLs from CPSC and FDA websites
2. **Batching**: Groups URLs into batches of 20
3. **Sending**: Sends each batch as a separate email
4. **Waiting**: Waits 15 minutes between batches
5. **Tracking**: Saves progress to resume later if needed

## Files

- `main.py` - Main scraper with batch notification system
- `batch_notifier.py` - Batch notification handler
- `cpsc_links_scraper.py` - CPSC website scraper
- `fda_selenium_scraper.py` - FDA website scraper
- `notifier.py` - Email notification system
- `batch_progress.json` - Progress tracking file
- `batch_notifier.log` - Batch operation logs

## Commands

- `python main.py` - Run scraper with batch notifications
- `python main.py --batch-status` - Check current batch status
- `python main.py --reset-batch` - Reset batch progress
- `python main.py --test-email` - Test email configuration
- `python main.py --help` - Show all options

## Logs

- `scraper.log` - Main scraper logs
- `batch_notifier.log` - Batch notification logs
- `cpsc_links_scraper.log` - CPSC scraper logs

## Benefits

- **Rate Limiting**: Respects email server limits
- **Reliability**: Can resume after interruptions
- **No Duplicates**: Prevents sending same URLs multiple times
- **Monitoring**: Comprehensive logging for troubleshooting
- **Scalability**: Handles thousands of URLs efficiently