"""
Urlscan.io scraper for XTream credentials
"""

import requests
import re
import json
import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from urllib.parse import urlparse, parse_qs
from rich.progress import Progress, SpinnerColumn, BarColumn, TimeElapsedColumn, TimeRemainingColumn, TextColumn
from models import XtreamCredential

class UrlscanScraper:
    """Scrapes urlscan.io for XTream IPTV credentials"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://urlscan.io/api/v1"
        self.session = requests.Session()
        self.session.headers.update({
            'API-Key': api_key,
            'Content-Type': 'application/json',
            'User-Agent': 'XTream-Scraper/2.0'
        })
        
        # Enhanced patterns for different redirect formats
        self.redirect_patterns = [
            # Standard "Redirect from:" pattern with optional trailing number
            re.compile(r'Redirect from:\s*([a-zA-Z0-9.-]+\.[a-zA-Z]{2,}):(\d+)/([a-zA-Z0-9@._-]+)/([a-zA-Z0-9._-]+)(?:/\d+)?', re.IGNORECASE),
            # Direct URL pattern with optional trailing number - only match valid domains
            re.compile(r'([a-zA-Z0-9.-]+\.[a-zA-Z]{2,}):(\d+)/([a-zA-Z0-9@._-]+)/([a-zA-Z0-9._-]+)(?:/\d+)?', re.IGNORECASE),
            # Pattern with quotes or brackets and optional trailing number
            re.compile(r'[\"\']?([a-zA-Z0-9.-]+\.[a-zA-Z]{2,}):(\d+)/([a-zA-Z0-9@._-]+)/([a-zA-Z0-9._-]+)(?:/\d+)?[\"\']?', re.IGNORECASE),
        ]
    
    def search_scans(self, query: str, size: int = 100, search_after: str = None) -> Dict:
        """Search for scans using urlscan.io API with proper pagination"""
        url = f"{self.base_url}/search/"
        params = {
            'q': query,
            'size': size
        }
        
        if search_after:
            params['search_after'] = search_after
        
        try:
            response = self.session.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error searching scans: {e}")
            return {'results': [], 'total': 0, 'has_more': False}
    
    def get_scan_result(self, scan_id: str) -> Optional[Dict]:
        """Get detailed scan result with retry logic"""
        url = f"{self.base_url}/result/{scan_id}/"
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = self.session.get(url)
                if response.status_code == 404:
                    return None
                response.raise_for_status()
                return response.json()
            except Exception as e:
                if attempt < max_retries - 1:
                    time.sleep(1)
                else:
                    return None
        return None
    
    def extract_text_from_data(self, data, path=""):
        """Recursively extract all text content from scan data"""
        texts = []
        
        if isinstance(data, dict):
            for key, value in data.items():
                texts.extend(self.extract_text_from_data(value, f"{path}.{key}" if path else key))
        elif isinstance(data, list):
            for i, item in enumerate(data):
                texts.extend(self.extract_text_from_data(item, f"{path}[{i}]" if path else f"[{i}]"))
        elif isinstance(data, str):
            texts.append((path, data))
        
        return texts
    
    def extract_xtream_credentials(self, scan_data: Dict, scan_id: str) -> List[XtreamCredential]:
        """Extract XTream credentials from scan data.

        Strategy:
        - Look for real HTTP(S) URLs inside the scan JSON.
        - Parse each URL with urlparse.
        - Expect paths like /<USERNAME>/<PASSWORD>/<STREAMID> or /<USERNAME>/<PASSWORD>.
        - Derive domain, optional port, username, password from the parsed URL.
        """
        credentials: List[XtreamCredential] = []

        # Extract all text content from the scan data
        all_texts = self.extract_text_from_data(scan_data)

        # Domains we know are not IPTV backends
        non_iptv_domains = {
            "urlscan.io",
            "mozilla.org",
            "cloudflare.com",
            "cloudflareregistrar.com",
            "google.com",
            "facebook.com",
            "appxzzgroup.com",
        }

        # Username/password values that clearly are not real IPTV creds
        invalid_usernames = {"live", "play", "test", "demo", "admin", "result", "screenshots", "dom", "report"}
        invalid_passwords = {"live", "play", "test", "demo", "admin", "password", "123456"}

        url_regex = re.compile(r"https?://[^\s\"'<>]+", re.IGNORECASE)

        for path, text in all_texts:
            if not text or "http" not in text:
                continue

            for url in url_regex.findall(text):
                try:
                    parsed = urlparse(url)
                    if not parsed.netloc or not parsed.path:
                        continue

                    host = parsed.hostname or ""
                    if not host or "." not in host:
                        continue

                    # Filter out obviously non-IPTV domains
                    if any(bad in host.lower() for bad in non_iptv_domains):
                        continue

                    port = str(parsed.port or 80)

                    username: Optional[str] = None
                    password: Optional[str] = None

                    # First, try to extract from query string for get.php-style URLs
                    query_params = parse_qs(parsed.query)
                    q_user = query_params.get("username", [])
                    q_pass = query_params.get("password", [])

                    if q_user and q_pass:
                        username = q_user[0]
                        password = q_pass[0]
                    else:
                        # Fallback: derive from path segments (/user/pass[/streamid])
                        segments = [seg for seg in parsed.path.split("/") if seg]
                        if len(segments) < 2:
                            continue

                        # If last segment is numeric -> assume /user/pass/streamid
                        if len(segments) >= 3 and segments[-1].isdigit():
                            username = segments[-3]
                            password = segments[-2]
                        else:
                            # Otherwise, assume /user/pass
                            username = segments[-2]
                            password = segments[-1]

                    if not username or not password:
                        continue

                    # Basic sanity checks
                    if len(username) <= 2 or len(password) <= 2:
                        continue

                    if username.lower() in invalid_usernames or password.lower() in invalid_passwords:
                        continue

                    # Skip obvious asset/file names (JS, CSS, images, etc.)
                    asset_exts = (
                        ".js", ".css", ".png", ".jpg", ".jpeg", ".gif", ".svg",
                        ".webp", ".ico", ".json", ".map", ".txt", ".xml", ".html", ".php",
                    )
                    if username.lower().endswith(asset_exts) or password.lower().endswith(asset_exts):
                        continue

                    xtream_url = (
                        f"http://{host}:{port}/get.php?"
                        f"username={username}&password={password}&type=m3u_plus"
                    )

                    credential = XtreamCredential(
                        domain=host,
                        port=port,
                        username=username,
                        password=password,
                        xtream_url=xtream_url,
                        original_redirect=f"{host}:{port}/{username}/{password}",
                        source_path=path,
                        source_text=text[:200] + "..." if len(text) > 200 else text,
                        scan_id=scan_id,
                        scan_date=scan_data.get("task", {}).get("time", ""),
                        page_url=scan_data.get("data", {}).get("page", {}).get("url", ""),
                    )

                    # Only add if not duplicate in this scan
                    if not any(c.xtream_url == credential.xtream_url for c in credentials):
                        credentials.append(credential)

                except Exception:
                    # If anything goes wrong for this URL, skip it and continue
                    continue

        return credentials
    
    def scrape_credentials(self, query: str = 'page.url:"/live/play/"', max_scans: int = 50, max_age_days: int = 30) -> List[XtreamCredential]:
        """Main scraping function with Rich progress bar.

        max_age_days limits how far back in time scans are considered based on
        the scan's task.time field. Older scans are skipped.
        """
        print(f"Searching urlscan.io for: {query}")
        print(f"Maximum scans to process: {max_scans}")
        print(f"Maximum scan age: {max_age_days} days")
        
        all_credentials: List[XtreamCredential] = []
        processed_scans = 0
        search_after = None
        cutoff_time = datetime.utcnow() - timedelta(days=max(1, max_age_days))

        # Rich progress bar for scan processing
        with Progress(
            SpinnerColumn(),
            TextColumn("[bold cyan]Scraping[/bold cyan]"),
            BarColumn(),
            TextColumn("{task.completed}/{task.total}"),
            TimeElapsedColumn(),
            TimeRemainingColumn(),
        ) as progress:
            task_id = progress.add_task("scraping", total=max_scans)
            
            while processed_scans < max_scans:
                # Search for scans
                search_result = self.search_scans(query, size=min(100, max_scans - processed_scans), search_after=search_after)
                
                scans = search_result.get('results', [])
                if not scans:
                    break
                
                for scan in scans:
                    if processed_scans >= max_scans:
                        break
                    
                    scan_id = scan.get('_id') or scan.get('id')
                    if not scan_id:
                        # Even if scan_id is missing, count this as processed to avoid stalling
                        processed_scans += 1
                        progress.update(task_id, advance=1)
                        continue
                    
                    # Get detailed scan result
                    scan_data = self.get_scan_result(scan_id)
                    if scan_data:
                        # Skip scans older than max_age_days if task.time is present
                        task_time_str = scan_data.get("task", {}).get("time")
                        if task_time_str:
                            try:
                                # urlscan times are ISO 8601, often with 'Z'
                                dt_str = task_time_str.replace("Z", "+00:00")
                                task_time = datetime.fromisoformat(dt_str)
                                if task_time < cutoff_time:
                                    processed_scans += 1
                                    progress.update(task_id, advance=1)
                                    continue
                            except Exception:
                                # If parsing fails, fall back to including the scan
                                pass

                        # Extract credentials
                        credentials = self.extract_xtream_credentials(scan_data, scan_id)
                        for cred in credentials:
                            all_credentials.append(cred)
                    
                    processed_scans += 1
                    progress.update(task_id, advance=1)
                    
                    # Rate limiting
                    if processed_scans % 10 == 0:
                        time.sleep(1)
                
                # Check if there are more results
                if not search_result.get('has_more', False):
                    break
                
                # Get the sort value for pagination
                if scans:
                    search_after = scans[-1].get('sort')
                    if not search_after:
                        break
        
        # Remove duplicates
        unique_credentials = []
        seen_urls = set()
        
        for cred in all_credentials:
            if cred.xtream_url not in seen_urls:
                seen_urls.add(cred.xtream_url)
                unique_credentials.append(cred)
        
        # Filter out invalid formats (live/play)
        valid_format_credentials = [
            cred for cred in unique_credentials 
            if cred.is_valid_xtream_format()
        ]
        
        print(f"\n=== SCRAPING SUMMARY ===")
        print(f"Total scans processed: {processed_scans}")
        print(f"Total credentials found: {len(all_credentials)}")
        print(f"Unique credentials: {len(unique_credentials)}")
        print(f"Valid XTREAM format: {len(valid_format_credentials)}")
        
        return valid_format_credentials
