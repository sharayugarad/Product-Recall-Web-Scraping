#!/usr/bin/env python3
import json
import os
import smtplib
import re
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


class EmailNotifier:
    """
    Handles email notifications for new URLs with dynamic subject lines.
    Enhanced security and validation.
    """

    def __init__(self, config_file="scraper_config.json"):
        self.config_file = config_file
        self.config = self._load_config()
        self._validate_config()

    def _load_config(self):
        """
        Load email configuration from scraper_config.json file.
        ✅ UPDATED: Now uses JSON configuration as primary source (no environment variable fallback)
        """
        # Load from scraper_config.json file
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    config = json.load(f)
                print(f"✅ Loaded email configuration from {self.config_file}")
                return config
            except (json.JSONDecodeError, KeyError) as e:
                print(f"❌ Error loading config file: {e}")
                return {}
        else:
            print(f"❌ Configuration file {self.config_file} not found!")
            return {}

    def _validate_config(self):
        """Validate configuration and show warnings."""
        warnings = []
        
        # Check credentials
        if not self.config["EMAIL_USERNAME"]:
            warnings.append("EMAIL_USERNAME not configured")
        else:
            # Validate email format
            if not self._is_valid_email(self.config["EMAIL_USERNAME"]):
                warnings.append(f"EMAIL_USERNAME has invalid format: {self.config['EMAIL_USERNAME']}")
        
        if not self.config["EMAIL_PASSWORD"]:
            warnings.append("EMAIL_PASSWORD not configured")
        
        if not self.config["RECEIVER_EMAIL"]:
            warnings.append("RECEIVER_EMAIL not configured")
        else:
            # Validate recipient emails
            recipients = self.config["RECEIVER_EMAIL"].split(",")
            for recipient in recipients:
                if not self._is_valid_email(recipient.strip()):
                    warnings.append(f"Invalid recipient email format: {recipient.strip()}")
        
        # Show warnings if any
        if warnings:
            print("\n" + "="*60)
            print("⚠️  EMAIL CONFIGURATION WARNINGS")
            print("="*60)
            for warning in warnings:
                print(f"  • {warning}")
            print("\n💡 How to fix:")
            print("  Update scraper_config.json with:")
            print("    EMAIL_USERNAME: 'your-email@example.com'")
            print("    EMAIL_PASSWORD: 'your-password'")
            print("    RECEIVER_EMAIL: 'recipient@example.com'")
            print("    EMAIL_SMTP_HOST: 'smtp-mail.outlook.com'")
            print("    EMAIL_SMTP_PORT: '587'")
            print("    EMAIL_USE_SSL: 'false'")
            print("="*60 + "\n")

    def _is_valid_email(self, email: str) -> bool:
        """
        Validate email format.
        
        Args:
            email: Email address to validate
            
        Returns:
            bool: True if valid email format
        """
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None

    def _is_config_complete(self):
        """Check that all necessary config fields are present."""
        required_fields = [
            "EMAIL_USERNAME",
            "EMAIL_PASSWORD",
            "EMAIL_SMTP_HOST",
            "EMAIL_SMTP_PORT",
            "RECEIVER_EMAIL",
        ]
        missing_fields = [field for field in required_fields if not self.config.get(field)]
        
        if missing_fields:
            print(f"❌ Missing configuration fields: {', '.join(missing_fields)}")
            return False
        return True

    def _create_email_body(self, urls, scraper_name="Scraper", batch_info=None, no_urls_found=False):
        """
        Generate email body with URLs and timestamp.
        
        Args:
            urls: List of URLs
            scraper_name: Name of the scraper
            batch_info: Dict with batch details like {'batch_number': 1, 'total_batches': 3}
            no_urls_found: Boolean flag for "No URLs found" message
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Handle "No URLs found" case
        if no_urls_found or not urls:
            body = f"{scraper_name} - Scraping Complete\n"
            body += "="*60 + "\n\n"
            body += "NO NEW RECALLS FOUND\n\n"
            body += "The scraper ran successfully but did not find any new recall URLs.\n"
            body += "This could mean:\n"
            body += "  • No new recalls have been posted\n"
            body += "  • All recalls have already been scraped previously\n\n"
            body += "="*60 + "\n"
            body += f"Scraping completed at: {timestamp}\n"
            body += "This is an automated notification."
            return body
        
        # Normal case with URLs
        body = f"{scraper_name} - New URLs Found\n"
        body += "="*60 + "\n\n"
        
        # Add batch information if provided
        # Add batch information if provided
        if batch_info:
            body += "SOURCE BREAKDOWN:\n"

            # Case A: batch notifier style
            if "batch_number" in batch_info or "total_batches" in batch_info:
                batch_num = batch_info.get("batch_number", 1)
                total_batches = batch_info.get("total_batches", 1)

                body += f"  Batch: {batch_num} of {total_batches}\n"
                body += f"  URLs in this batch: {len(urls)}\n"
                body += "\n" + "-"*60 + "\n\n"

            # Case B: unified digest style (CPSC/FDA/FSIS/SCOUT counts)
            else:
                # Print each source count (works for SCOUT too)
                for k, v in batch_info.items():
                    try:
                        body += f"  {k}: {int(v)}\n"
                    except Exception:
                        body += f"  {k}: {v}\n"

                body += f"\nTotal URLs found: {len(urls)}\n\n"
                body += "-"*60 + "\n\n"
        else:
            body += f"Total URLs found: {len(urls)}\n\n"
            body += "-"*60 + "\n\n"

        
        # Add URLs
        body += f"URLs:\n\n"
        for i, url in enumerate(urls, 1):
            body += f"{i}. {url}\n"
        
        # Add footer
        body += "\n" + "="*60 + "\n"
        body += f"Scraping completed at: {timestamp}\n"
        body += "This is an automated notification."
        
        return body

    def send_notification(self, new_urls, new_recalls_count=0, subject_prefix="Scraper Notification", scraper_name="Scraper", batch_info=None, no_urls_found=False):
        """
        Send email with new URLs.

        Args:
            new_urls (list): List of new URLs (can be empty for "no URLs found")
            new_recalls_count (int): Number of new recalls
            subject_prefix (str): Subject prefix for email
            scraper_name (str): Scraper name
            batch_info (dict): Optional batch information {'batch_number': 1, 'total_batches': 3}
            no_urls_found (bool): Flag to send "No URLs found" email
        Returns:
            bool: True if email sent successfully
        """
        # Allow sending email even with no URLs if no_urls_found flag is set
        if not new_urls and not no_urls_found:
            print("ℹ️  No new URLs to send via email.")
            return False

        if not self._is_config_complete():
            print("❌ Email configuration incomplete. Please check scraper_config.json")
            return False

        try:
            msg = MIMEMultipart()
            msg["From"] = self.config["EMAIL_USERNAME"]
            msg["To"] = self.config["RECEIVER_EMAIL"]
            msg["Subject"] = subject_prefix
            body = self._create_email_body(new_urls, scraper_name, batch_info, no_urls_found)
            msg.attach(MIMEText(body, "plain"))

            # Choose SSL or TLS
            use_ssl = str(self.config.get("EMAIL_USE_SSL", "false")).lower() == "true"
            
            print(f"📧 Connecting to {self.config['EMAIL_SMTP_HOST']}:{self.config['EMAIL_SMTP_PORT']}...")
            
            if use_ssl:
                server = smtplib.SMTP_SSL(
                    self.config["EMAIL_SMTP_HOST"], int(self.config["EMAIL_SMTP_PORT"])
                )
            else:
                server = smtplib.SMTP(
                    self.config["EMAIL_SMTP_HOST"], int(self.config["EMAIL_SMTP_PORT"])
                )
                server.starttls()

            server.login(self.config["EMAIL_USERNAME"], self.config["EMAIL_PASSWORD"])
            server.sendmail(
                self.config["EMAIL_USERNAME"],
                self.config["RECEIVER_EMAIL"].split(","),
                msg.as_string(),
            )
            server.quit()
            print(f"✅ Email sent successfully to {self.config['RECEIVER_EMAIL']}")
            return True

        except smtplib.SMTPAuthenticationError as e:
            print(f"\n❌ SMTP Authentication Error: {e}")
            print("💡 Possible causes:")
            print("   • Incorrect username or password")
            print("   • Two-factor authentication enabled (use app password)")
            print("   • Account locked or security restrictions")
            print("\n🔧 How to fix:")
            print("   1. Verify EMAIL_USERNAME and EMAIL_PASSWORD in scraper_config.json")
            print("   2. For Outlook: Enable app passwords in security settings")
            print("   3. For Gmail: Use app-specific password, not account password")
            return False
        except smtplib.SMTPConnectError as e:
            print(f"\n❌ SMTP Connection Error: {e}")
            print("💡 Check your SMTP server and port settings")
            return False
        except smtplib.SMTPServerDisconnected as e:
            print(f"\n❌ SMTP Server Disconnected: {e}")
            print("💡 The server unexpectedly closed the connection")
            return False
        except smtplib.SMTPException as e:
            print(f"\n❌ SMTP Error: {e}")
            print("💡 Check your email configuration")
            return False
        except Exception as e:
            print(f"\n❌ Unexpected error sending email: {e}")
            print(f"   Error type: {type(e).__name__}")
            return False
    
    
# Test function
def test_email_config():
    """Test email configuration."""
    print("\n" + "="*60)
    print("📧 TESTING EMAIL CONFIGURATION")
    print("="*60)
    
    notifier = EmailNotifier()
    
    if not notifier._is_config_complete():
        print("\n❌ Configuration incomplete - cannot send test email")
        return False
    
    print("\n📋 Current Configuration:")
    print(f"   SMTP Server: {notifier.config['EMAIL_SMTP_HOST']}:{notifier.config['EMAIL_SMTP_PORT']}")
    print(f"   Sender: {notifier.config['EMAIL_USERNAME']}")
    print(f"   Recipients: {notifier.config['RECEIVER_EMAIL']}")
    print(f"   SSL: {notifier.config['EMAIL_USE_SSL']}")
    
    test_urls = ["https://example.com/test-url-1", "https://example.com/test-url-2"]
    
    print("\n📤 Sending test email...")
    success = notifier.send_notification(
        test_urls, 
        2, 
        "🧪 Test Email - Scraper Configuration", 
        "Test Scraper"
    )
    
    if success:
        print("\n✅ Email configuration test PASSED!")
        print("   Check your inbox for the test email")
    else:
        print("\n❌ Email configuration test FAILED")
        print("   Review the error messages above")
    
    print("="*60 + "\n")
    return success


if __name__ == "__main__":
    test_email_config()
