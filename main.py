#!/usr/bin/env python3
"""
XTream Credential Scraper - Main Application
Scrapes urlscan.io for XTream IPTV credentials and validates them
"""

import os
import sys
from datetime import datetime, UTC
from typing import List
from scrapers import UrlscanScraper
from validators import XtreamValidator
from exporters import XtreamExporter
from models import XtreamCredential

class XtreamScraperApp:
    """Main application class"""
    
    def __init__(self, api_key: str):
        self.scraper = UrlscanScraper(api_key)
        self.validator = XtreamValidator()
        self.exporter = XtreamExporter()
        self.output_dir: str | None = None
    
    def run(self, query: str = 'page.url:"/live/play/"', max_scans: int = 50, max_age_days: int = 30, validate: bool = True):
        """Run the complete scraping and validation process"""
        print("=" * 60)
        print("XTREAM IPTV CREDENTIAL SCRAPER")
        print("=" * 60)
        
        # Prepare timestamped output directory for this run
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        base_output = os.path.join(os.getcwd(), "output")
        os.makedirs(base_output, exist_ok=True)
        self.output_dir = os.path.join(base_output, timestamp)
        os.makedirs(self.output_dir, exist_ok=True)
        print(f"\nOutput directory: {self.output_dir}")
        
        # Step 1: Scrape credentials
        print("\n🔍 STEP 1: Scraping credentials from urlscan.io...")
        credentials = self.scraper.scrape_credentials(query, max_scans, max_age_days=max_age_days)
        
        if not credentials:
            print("❌ No credentials found!")
            return
        
        print(f"✅ Found {len(credentials)} credentials in valid XTream format")
        
        # Step 2: Validate credentials (optional)
        valid_credentials = credentials
        if validate:
            print("\n🔍 STEP 2: Validating credentials...")
            valid_credentials = self.validator.validate_credentials(credentials)
        
        # Step 3: Export results
        print("\n📁 STEP 3: Exporting results...")

        # Only keep credentials that were actually validated as True.
        # Use the main credentials list so we respect is_valid flags set during
        # validation even if the validator return list changes.
        if validate:
            now_ts = datetime.now(UTC).timestamp()
            filtered: List[XtreamCredential] = []
            for c in credentials:
                if not c.is_valid:
                    continue
                ui = c.user_info or {}
                status = str(ui.get('status', '')).lower()
                exp_raw = ui.get('exp_date')

                # If we have a numeric exp_date, drop entries that are already expired
                is_expired = False
                if isinstance(exp_raw, str) and exp_raw.isdigit():
                    try:
                        exp_ts = int(exp_raw)
                        if exp_ts < now_ts:
                            is_expired = True
                    except ValueError:
                        pass

                if status == 'expired' or is_expired:
                    continue

                filtered.append(c)

            valid_to_export = filtered
        else:
            # When validation is disabled, there are no "valid & reachable" creds
            valid_to_export = []

        # Export only JSON files
        self.exporter.to_json(valid_to_export, os.path.join(self.output_dir, "xtream_valid.json"))
        # Also export all credentials (including invalid/unreachable ones)
        self.exporter.to_json(credentials, os.path.join(self.output_dir, "xtream_all.json"))
        
        # Step 4: Display summary
        self.display_summary(valid_credentials, credentials)
    
    def display_summary(self, valid_credentials: List[XtreamCredential], all_credentials: List[XtreamCredential]):
        """Display final summary"""
        print("\n" + "=" * 60)
        print("FINAL SUMMARY")
        print("=" * 60)
        
        print(f"📊 Total credentials scraped: {len(all_credentials)}")
        print(f"✅ Valid credentials: {len(valid_credentials)}")
        print(f"❌ Invalid credentials: {len(all_credentials) - len(valid_credentials)}")
        
        if valid_credentials:
            print(f"\n🔥 TOP 10 VALID CREDENTIALS:")
            for i, cred in enumerate(valid_credentials[:10], 1):
                user_info = cred.user_info or {}
                active_cons = user_info.get('active_cons', 'N/A')
                max_cons = user_info.get('max_connections', 'N/A')
                exp_date = user_info.get('exp_date', 'N/A')
                
                print(f"{i:2d}. {cred.domain}:{cred.port}/{cred.username}")
                print(f"     Connections: {active_cons}/{max_cons} | Expires: {exp_date}")
            
            if len(valid_credentials) > 10:
                print(f"\n... and {len(valid_credentials) - 10} more valid credentials")
        
        if self.output_dir:
            print(f"\n📁 Files created in: {self.output_dir}")
            print(f"   • xtream_valid.json - Valid & reachable credentials (JSON with details)")
            print(f"   • xtream_all.json - All scraped credentials (including invalid/unreachable)")
        else:
            print("\n📁 Files created (output directory not set)")

def get_api_key():
    """Get API key from user input or environment"""
    api_key = os.getenv('URLSCAN_API_KEY')
    
    if not api_key:
        api_key = input("Enter your urlscan.io API key: ").strip()
    
    if not api_key:
        print("❌ API key is required!")
        sys.exit(1)
    
    return api_key


def prompt_run_configuration() -> tuple[str, int, int, bool]:
    """Interactively ask the user for query, scan limit, age limit and validation settings."""
    # Default values
    default_max_scans = 50
    default_max_age_days = 30
    default_validate = True

    # Predefined query options
    queries = {
        "1": 'page.url:"/live/play/"',
        "2": 'page.url:"/get.php?username="',
        "3": 'page.url:"/player_api.php?username="',
        "4": 'page.url:"&type=m3u_plus"',
        "5": 'page.url:"&type=m3u"',
        "6": 'page.url:"&type=m3u8"',
        "7": 'page.url:"&output=hls"',
        "8": 'page.url:"&output=ts"',
        "9": 'page.url:"streaming/clients_live.php?username="',
    }

    print("\n=== RUN CONFIGURATION ===")
    print("Select search query:")
    print("  1. page.url:\"/live/play/\"")
    print("  2. page.url:\"/get.php?username=\"")
    print("  3. page.url:\"/player_api.php?username=\"")
    print("  4. page.url:\"&type=m3u_plus\"")
    print("  5. page.url:\"&type=m3u\"")
    print("  6. page.url:\"&type=m3u8\"")
    print("  7. page.url:\"&output=hls\"")
    print("  8. page.url:\"&output=ts\"")
    print("  9. page.url:\"streaming/clients_live.php?username=\"")
    print("  0. ALL OF THE ABOVE (OR-combined, 1-8)")

    choice = input("> ").strip()

    if choice == "0":
        # Combine main individual queries (1-8) with OR to broaden the search
        query = "(" + " OR ".join(queries[key] for key in sorted(queries.keys()) if key != "9") + ")"
    else:
        # Fallback to option 1 if input is invalid or empty
        query = queries.get(choice, queries["1"])

    print(f"Max scans to process [default: {default_max_scans}]")
    max_scans_raw = input("> ").strip()
    max_scans = default_max_scans
    if max_scans_raw.isdigit():
        max_scans = max(1, min(500, int(max_scans_raw)))

    print(f"Maximum age of scans in days (1-365) [default: {default_max_age_days}]")
    max_age_raw = input("> ").strip()
    max_age_days = default_max_age_days
    if max_age_raw.isdigit():
        max_age_days = max(1, min(365, int(max_age_raw)))

    print("Validate credentials? [Y/n] (Y = validate all, n = skip validation)")
    validate_raw = input("> ").strip().lower()
    validate = default_validate if validate_raw == "" else validate_raw.startswith("y")

    return query, max_scans, max_age_days, validate

def main():
    """Main entry point"""
    try:
        # Get API key
        api_key = get_api_key()

        # Ask user how they want to run this session
        query, max_scans, max_age_days, validate = prompt_run_configuration()

        # Create and run app
        app = XtreamScraperApp(api_key)
        app.run(query=query, max_scans=max_scans, max_age_days=max_age_days, validate=validate)
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Process interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
