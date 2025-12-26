#!/usr/bin/env python3
"""
Economics PhD → Tech Industry Placement Scraper
Scrapes placement data from top 20 econ PhD programs (2020-2025)
"""
import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import re
import hashlib
import json
import argparse
import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

# Selenium imports for JS-heavy sites
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# Import custom parsers
try:
    from parsers import CUSTOM_PARSERS
except ImportError:
    CUSTOM_PARSERS = {}

# Import normalization
from normalize import is_academia, normalize_company

# Paths for state tracking and caching
SCRAPE_STATE_FILE = 'data/scrape_state.json'
RAW_HTML_DIR = 'data/raw'

# School configurations
SCHOOLS = {
    'MIT': {
        'urls': [
            'https://economics.mit.edu/academic-programs/phd-program/job-market',
            'https://economics.mit.edu/sites/default/files/inline-files/Placement_Results_2024_website.pdf',
        ]
    },
    'Harvard': {
        'urls': [
            'https://www.economics.harvard.edu/placement',
            'https://www.economics.harvard.edu/job-market-candidates'
        ]
    },
    'Stanford': {
        'urls': [
            'https://economics.stanford.edu/graduate/job-market-candidates',
            'https://economics.stanford.edu/graduate/student-placement',
            'https://economics.stanford.edu/people/phd-alumni',
        ]
    },
    'Princeton': {
        'urls': [
            'https://economics.princeton.edu/graduate-program/job-market-and-placements/',
            'https://economics.princeton.edu/graduate-program/job-market-and-placements/statistics-on-past-placements/',
        ]
    },
    'UC Berkeley': {
        'urls': [
            'https://econ.berkeley.edu/graduate/professional-placement',
            'https://www.econ.berkeley.edu/grad/program/placement-outcomes',
            'https://haas.berkeley.edu/phd/careers/job-placements/',
        ]
    },
    'Yale': {
        'urls': [
            'https://economics.yale.edu/phd-program/placement',
            'https://economics.yale.edu/phd-program/placement/outcomes'
        ]
    },
    'University of Chicago': {
        'urls': [
            'https://economics.uchicago.edu/phd-program/career-placement',
        ]
    },
    'Northwestern': {
        'urls': [
            'https://economics.northwestern.edu/graduate/prospective/placement.html',
        ]
    },
    'Columbia': {
        'urls': [
            'https://econ.columbia.edu/phd/job-market-candidates/',
            'https://econ.columbia.edu/phd/placement/'
        ]
    },
    'NYU': {
        'urls': [
            'https://as.nyu.edu/departments/econ/job-market.html',
            'https://as.nyu.edu/departments/econ/job-market/placements.html',
            'https://www.stern.nyu.edu/programs-admissions/phd/job-placement/recent-job-placements'
        ]
    },
    # Next 10 schools
    'University of Pennsylvania': {
        'urls': [
            'https://economics.sas.upenn.edu/graduate/job-market-candidates',
            'https://economics.sas.upenn.edu/graduate/prospective-students/placement-information',
            'https://doctoral.wharton.upenn.edu/career-placement/',
        ]
    },
    'University of Michigan': {
        'urls': [
            'https://lsa.umich.edu/econ/doctoral-program/past-job-market-placements.html',
            'https://michiganross.umich.edu/programs/phd/placements',
        ]
    },
    'UCLA': {
        'urls': [
            'https://economics.ucla.edu/graduate/graduate-profiles/graduate-placement-history/',
            'https://www.anderson.ucla.edu/degrees/phd-program/placement',
        ]
    },
    'University of Wisconsin-Madison': {
        'urls': [
            'https://econ.wisc.edu/doctoral/career-placement/',
            'https://business.wisc.edu/phd/placements/',
        ]
    },
    'Duke': {
        'urls': [
            'https://econ.duke.edu/graduate/hire-duke-phd',
            'https://econ.duke.edu/phd-program/prospective-students/placements'
        ]
    },
    'University of Minnesota': {
        'urls': [
            'https://cla.umn.edu/economics/people/job-market-candidates',
            'https://apec.umn.edu/graduate/placement-recent-graduates'
        ]
    },
    'Brown': {
        'urls': [
            'https://economics.brown.edu/job-market-candidates-0',
            'https://economics.brown.edu/academics/graduate/job-placement-results'
        ]
    },
    'Cornell': {
        'urls': [
            'https://economics.cornell.edu/economics-phd-job-market-candidates',
            'https://economics.cornell.edu/historical-placement-phd-students'
        ]
    },
    'Carnegie Mellon': {
        'urls': [
            'https://www.cmu.edu/tepper/programs/phd/job-market',
            'https://www.heinz.cmu.edu/programs/phd-programs/phd-placements',
        ]
    },
    'University of Maryland': {
        'urls': [
            'https://www.econ.umd.edu/graduate/job-market-candidates-2024-2025',
            'https://www.econ.umd.edu/graduate/job-placement'
        ]
    },
    # Additional schools with known tech placements
    'University of Washington': {
        'urls': [
            'https://econ.washington.edu/job-placement',
        ]
    },
    'University of Illinois': {
        'urls': [
            'https://economics.illinois.edu/academics/phd-program/phd-placements-year-employer',
        ]
    },
    'University of Virginia': {
        'urls': [
            'https://economics.virginia.edu/placement-history',
        ]
    },
    'UT Austin': {
        'urls': [
            'https://liberalarts.utexas.edu/economics/phd/job-market.html',
        ]
    },
}

# Tech companies to filter for
TECH_COMPANIES = {
    # Big Tech
    'google', 'meta', 'facebook', 'amazon', 'apple', 'microsoft', 'netflix',
    # Tech Unicorns / Marketplaces
    'uber', 'lyft', 'airbnb', 'stripe', 'doordash', 'instacart', 'dropbox',
    'slack', 'zoom', 'spotify', 'pinterest', 'snap', 'snapchat', 'twitter', 'x corp',
    'tiktok', 'bytedance', 'reddit', 'discord', 'nextdoor', 'thumbtack', 'turo',
    # AI/ML
    'openai', 'anthropic', 'deepmind', 'cohere', 'stability ai', 'midjourney',
    'hugging face', 'scale ai', 'databricks', 'perplexity', 'xai', 'groq',
    'codeium', 'cursor', 'anysphere', 'writer', 'elevenlabs', 'harvey',
    'cognition', 'character ai', 'inflection',
    # Fintech
    'robinhood', 'coinbase', 'plaid', 'square', 'block', 'affirm', 'chime',
    'sofi', 'brex', 'ripple', 'kraken', 'toast', 'marqeta', 'klarna', 'revolut',
    # Enterprise/Cloud/HR
    'salesforce', 'oracle', 'sap', 'vmware', 'snowflake', 'palantir',
    'servicenow', 'workday', 'splunk', 'crowdstrike', 'datadog',
    'deel', 'remote', 'rippling', 'gusto', 'qualtrics', 'amplitude',
    # E-commerce / Logistics
    'shopify', 'ebay', 'wayfair', 'etsy', 'walmart labs', 'flexport', 'faire',
    # Hardware/Chips
    'nvidia', 'intel', 'amd', 'qualcomm', 'tesla', 'spacex',
    # Real Estate Tech
    'zillow', 'redfin', 'opendoor', 'compass', 'houzz', 'corelogic', 'realtor.com',
    # Travel Tech
    'booking', 'expedia', 'tripadvisor', 'navan', 'tripactions', 'hopper', 'kayak',
    # Other Tech
    'linkedin', 'indeed', 'glassdoor', 'yelp', 'doximity', 'veeva',
    'twilio', 'okta', 'cloudflare', 'mongodb', 'elastic',
    'asana', 'notion', 'figma', 'canva', 'airtable',
    'grammarly', 'duolingo', 'coursera', 'udemy', 'pandora',
    'roblox', 'epic games', 'unity', 'activision', 'electronic arts', 'adobe',
}


class EconPhDScraper:
    def __init__(self, force: bool = False):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })
        self.candidates = []
        self.driver = None  # Lazy-initialized Selenium driver
        self.force = force  # Force re-scrape all pages
        self.state = self._load_state()

    def _load_state(self) -> dict:
        """Load scrape state from disk."""
        if Path(SCRAPE_STATE_FILE).exists():
            try:
                with open(SCRAPE_STATE_FILE) as f:
                    return json.load(f)
            except json.JSONDecodeError:
                pass
        return {'pages': {}, 'last_run': None}

    def _save_state(self):
        """Save scrape state to disk."""
        self.state['last_run'] = datetime.now().isoformat()
        Path(SCRAPE_STATE_FILE).parent.mkdir(parents=True, exist_ok=True)
        with open(SCRAPE_STATE_FILE, 'w') as f:
            json.dump(self.state, f, indent=2)

    def _hash_content(self, html: str) -> str:
        """Generate hash of page content."""
        return hashlib.md5(html.encode()).hexdigest()

    def _save_raw_html(self, url: str, html: str):
        """Cache raw HTML for debugging."""
        Path(RAW_HTML_DIR).mkdir(parents=True, exist_ok=True)
        filename = hashlib.md5(url.encode()).hexdigest()[:12] + '.html'
        with open(f"{RAW_HTML_DIR}/{filename}", 'w', encoding='utf-8') as f:
            f.write(html)

    def _get_selenium_driver(self):
        """Lazy-initialize Selenium WebDriver with anti-detection measures."""
        if self.driver is None:
            options = Options()
            options.add_argument('--headless=new')  # New headless mode
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-gpu')
            options.add_argument('--window-size=1920,1080')
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_argument(
                'user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
            # Anti-detection measures
            options.add_experimental_option('excludeSwitches', ['enable-automation'])
            options.add_experimental_option('useAutomationExtension', False)

            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=options)

            # Additional anti-detection
            self.driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
                'source': 'Object.defineProperty(navigator, "webdriver", {get: () => undefined})'
            })
        return self.driver

    def _close_driver(self):
        """Close Selenium driver if open."""
        if self.driver:
            self.driver.quit()
            self.driver = None

    def fetch_page_selenium(self, url: str, wait_for: str = None) -> Optional[BeautifulSoup]:
        """Fetch page using Selenium for JS-rendered content with retry logic."""
        max_retries = 3

        for attempt in range(max_retries):
            try:
                print(f"  [Selenium] Fetching (attempt {attempt + 1}): {url}")
                driver = self._get_selenium_driver()
                driver.get(url)

                # Wait for page load
                WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )

                # Wait for specific element if specified
                if wait_for:
                    try:
                        WebDriverWait(driver, 10).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, wait_for))
                        )
                    except Exception as e:
                        print(f"  [Selenium] Wait for element timeout: {e}")

                # Extra wait for JS rendering
                time.sleep(3)

                page_source = driver.page_source

                # Check if page has actual content
                if len(page_source) < 1000:
                    print(f"  [Selenium] Page too small ({len(page_source)} chars), retrying...")
                    time.sleep(2)
                    continue

                # Cache the HTML
                self._save_raw_html(url, page_source)

                return BeautifulSoup(page_source, 'lxml')

            except Exception as e:
                print(f"  [Selenium] Attempt {attempt + 1} failed: {e}")
                if attempt == max_retries - 1:
                    return None
                time.sleep(2)

        return None

    def fetch_page(self, url: str) -> tuple[Optional[BeautifulSoup], bool]:
        """Fetch and parse a webpage with change detection.

        Returns:
            Tuple of (BeautifulSoup or None, needs_selenium: bool)
        """
        try:
            time.sleep(1)  # Rate limiting
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            html = response.text

            # Detect empty or JS-rendered pages that need Selenium
            js_markers = ['loading...', 'please enable javascript', 'noscript',
                          'javascript is required', 'this page requires javascript']
            html_lower = html.lower()

            if len(html) < 1000:
                print(f"  [INFO] Page too small ({len(html)} chars), needs Selenium")
                return None, True

            if any(marker in html_lower for marker in js_markers):
                print(f"  [INFO] JS-required markers detected, needs Selenium")
                return None, True

            # Check if content changed (skip if unchanged and not forcing)
            new_hash = self._hash_content(html)
            old_hash = self.state['pages'].get(url, {}).get('hash')

            if not self.force and old_hash == new_hash:
                print(f"  [SKIP] No changes detected")
                return None, False  # Skip processing unchanged pages

            # Update state
            self.state['pages'][url] = {
                'hash': new_hash,
                'last_scraped': datetime.now().isoformat()
            }

            # Cache raw HTML for debugging
            self._save_raw_html(url, html)

            return BeautifulSoup(html, 'lxml'), False
        except requests.RequestException as e:
            print(f"  Error fetching {url}: {e}")
            return None, True  # Network error, try Selenium

    def is_tech_placement(self, placement: str) -> bool:
        """Check if a placement is at a tech company AND not academia."""
        if not placement:
            return False
        placement_lower = placement.lower()

        # Exclude academia first (professors, universities, etc.)
        if is_academia(placement):
            return False

        # Skip garbage/contact info
        if '@' in placement or 'phone' in placement_lower or 'campus map' in placement_lower:
            return False
        if 'connect with us' in placement_lower or 'econ[at]' in placement_lower:
            return False

        return any(company in placement_lower for company in TECH_COMPANIES)

    def extract_year(self, text: str) -> Optional[int]:
        """Extract a year (2020-2025) from text."""
        if not text:
            return None
        matches = re.findall(r'20(2[0-5])', text)
        if matches:
            return int('20' + matches[0])
        return None

    def parse_page(self, soup: BeautifulSoup, school: str) -> List[Dict]:
        """Parse page using custom parser if available, otherwise generic strategies."""
        candidates = []

        # Try custom parser first if available for this school
        if school in CUSTOM_PARSERS:
            print(f"  Using custom parser for {school}")
            candidates = CUSTOM_PARSERS[school].parse(soup)
            if candidates:
                return candidates
            print(f"  Custom parser returned 0 results, falling back to generic")

        # Generic strategies
        # Strategy 1: Tables
        candidates.extend(self._parse_tables(soup, school))

        # Strategy 2: Structured cards/articles
        candidates.extend(self._parse_cards(soup, school))

        # Strategy 3: Year-grouped lists
        candidates.extend(self._parse_year_lists(soup, school))

        return candidates

    def _parse_tables(self, soup: BeautifulSoup, school: str) -> List[Dict]:
        """Parse placement tables."""
        candidates = []
        for table in soup.select('table'):
            rows = table.select('tr')
            for row in rows[1:]:  # Skip header
                cells = row.select('td')
                if len(cells) >= 2:
                    name = cells[0].get_text(strip=True)
                    # Handle 3-column tables (Name, Fields, Placement) vs 2-column (Name, Placement)
                    if len(cells) >= 3:
                        fields = cells[1].get_text(strip=True)
                        placement = cells[2].get_text(strip=True)
                    else:
                        fields = ''
                        placement = cells[1].get_text(strip=True)

                    year = self.extract_year(row.get_text())

                    # Skip header-like rows and garbage
                    if name.lower() in ['candidate', 'name', 'student', 'phd']:
                        continue
                    if 'click on' in name.lower() or 'website' in name.lower():
                        continue
                    if 'building' in name.lower() or 'stanford way' in name.lower():
                        continue
                    if name and len(name) > 2 and len(name) < 100:
                        if year is None or (2020 <= year <= 2025):
                            candidates.append({
                                'name': name,
                                'school': school,
                                'graduation_year': year or datetime.now().year,
                                'research_fields': fields,
                                'initial_placement': placement,
                                'initial_role': '',
                                'current_placement': '',
                                'current_role': '',
                                'linkedin_url': ''
                            })
        return candidates

    def _parse_cards(self, soup: BeautifulSoup, school: str) -> List[Dict]:
        """Parse candidate cards/articles with expanded selectors."""
        candidates = []
        # Expanded selectors based on actual school HTML structures
        selectors = [
            # Standard CMS selectors
            '.views-row', '.node', 'article', '.person', '.candidate',
            '.faculty-member', '.profile', '.person-teaser', '.cu-person',
            # Stanford (Drupal with HB cards)
            '.hb-card', '.hb-card--horizontal',
            # MIT (figure/figcaption structure)
            'figure.caption', 'figure[role="group"]',
            # Additional common patterns
            '.profile-card', '.student-profile', '.graduate-profile',
            '.component_item', '.person-grid-item', '.faculty-grid-item',
            '.student-card', '.job-candidate',
            # Drupal-specific
            '.view-content > div', '.field-collection-item',
            # Generic attribute selectors
            'div[class*="person"]', 'div[class*="candidate"]', 'div[class*="profile"]',
            # List items with rich content
            'li.person', 'li.candidate',
        ]

        seen_names = set()  # Avoid duplicates

        for selector in selectors:
            for card in soup.select(selector):
                # Expanded name element selectors
                name_elem = card.select_one(
                    'h2 a, h3 a, h4 a, h2, h3, h4, .title a, .name a, .title, .name, '
                    'figcaption a, .hb-card__title a, .hb-card__title, '
                    '.field--name-title a, .component_title_link'
                )
                if not name_elem:
                    continue

                name = name_elem.get_text(strip=True)
                if not name or len(name) < 3 or len(name) > 100:
                    continue
                # Skip garbage
                garbage_markers = ['click on', 'building', 'stanford way', 'website',
                                   'campus map', 'connect with', 'phone', 'email']
                if any(marker in name.lower() for marker in garbage_markers):
                    continue
                # Skip if already seen
                if name.lower() in seen_names:
                    continue
                seen_names.add(name.lower())

                # Expanded placement selectors
                placement_elem = card.select_one(
                    '.placement, .position, .field--name-field-placement, '
                    '.field--name-field-initial-placement, .employer, .company, '
                    '.hb-card__subtitle, .job-placement'
                )
                placement = placement_elem.get_text(strip=True) if placement_elem else ""

                # Expanded research fields selectors
                fields_elem = card.select_one(
                    '.field--name-field-research-areas, .research, .interests, '
                    '.research-interests, .fields, .specialization, '
                    '.field--name-field-research-interests'
                )
                fields = fields_elem.get_text(strip=True) if fields_elem else ""

                year = self.extract_year(card.get_text())
                if year and (year < 2020 or year > 2025):
                    continue

                candidates.append({
                    'name': name,
                    'school': school,
                    'graduation_year': year or datetime.now().year,
                    'research_fields': fields,
                    'initial_placement': placement,
                    'initial_role': '',
                    'current_placement': '',
                    'current_role': '',
                    'linkedin_url': ''
                })

        return candidates

    def _parse_year_lists(self, soup: BeautifulSoup, school: str) -> List[Dict]:
        """Parse year-grouped list formats."""
        candidates = []
        current_year = None

        for elem in soup.select('h2, h3, h4, li, p'):
            text = elem.get_text(strip=True)
            year = self.extract_year(text)

            # Check if this is a year header
            if year and len(text) < 20:
                current_year = year
                continue

            if current_year and 2020 <= current_year <= 2025:
                # Try different separators
                for sep in [' - ', ': ', ', ']:
                    if sep in text:
                        parts = text.split(sep, 1)
                        if len(parts) >= 2 and len(parts[0]) > 2 and len(parts[0]) < 100:
                            candidates.append({
                                'name': parts[0].strip(),
                                'school': school,
                                'graduation_year': current_year,
                                'research_fields': '',
                                'initial_placement': parts[1].strip(),
                                'initial_role': '',
                                'current_placement': '',
                                'current_role': '',
                                'linkedin_url': ''
                            })
                        break

        return candidates

    def scrape_school(self, school: str, config: dict) -> List[Dict]:
        """Scrape all URLs for a school."""
        print(f"\nScraping {school}...")
        all_candidates = []
        urls_needing_selenium = []

        for url in config['urls']:
            print(f"  Fetching: {url}")
            soup, needs_selenium = self.fetch_page(url)

            if needs_selenium:
                urls_needing_selenium.append(url)
            elif soup:
                candidates = self.parse_page(soup, school)
                print(f"  Found {len(candidates)} candidates")
                all_candidates.extend(candidates)

        # Try Selenium for URLs that need it (JS-rendered, empty responses, errors)
        if urls_needing_selenium:
            print(f"  Trying Selenium for {len(urls_needing_selenium)} URL(s)...")
            for url in urls_needing_selenium:
                soup = self.fetch_page_selenium(url)
                if soup:
                    candidates = self.parse_page(soup, school)
                    print(f"  [Selenium] Found {len(candidates)} candidates")
                    all_candidates.extend(candidates)

        # If still no candidates, try Selenium on all URLs as last resort
        if len(all_candidates) == 0 and not urls_needing_selenium:
            print(f"  No results with requests, trying Selenium on all URLs...")
            for url in config['urls']:
                soup = self.fetch_page_selenium(url)
                if soup:
                    candidates = self.parse_page(soup, school)
                    print(f"  [Selenium] Found {len(candidates)} candidates")
                    all_candidates.extend(candidates)

        # Filter for tech placements
        tech_candidates = [c for c in all_candidates if self.is_tech_placement(c.get('initial_placement', ''))]
        print(f"  Tech placements: {len(tech_candidates)}")

        return tech_candidates

    def scrape_all(self) -> pd.DataFrame:
        """Scrape all schools and return consolidated DataFrame."""
        all_candidates = []

        try:
            for school, config in SCHOOLS.items():
                candidates = self.scrape_school(school, config)
                all_candidates.extend(candidates)
        finally:
            # Clean up Selenium driver
            self._close_driver()
            # Save state for incremental scraping
            self._save_state()

        # Deduplicate by name + school
        df = pd.DataFrame(all_candidates)
        if not df.empty:
            df = df.drop_duplicates(subset=['name', 'school'])

        print(f"\n{'='*50}")
        print(f"Total tech placements found: {len(df)}")
        return df

    def save(self, df: pd.DataFrame, output_path: str):
        """Save results to CSV with normalized company names."""
        # Create backup before overwriting
        output_file = Path(output_path)
        if output_file.exists():
            backup_dir = output_file.parent / 'backups'
            backup_dir.mkdir(exist_ok=True)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_path = backup_dir / f"{output_file.stem}_{timestamp}.csv"
            shutil.copy(output_path, backup_path)
            print(f"Backed up existing file to {backup_path}")

        # Normalize company names (Facebook→Meta, Twitter→X, etc.)
        if 'initial_placement' in df.columns:
            df['initial_placement'] = df['initial_placement'].apply(normalize_company)
        df.to_csv(output_path, index=False)
        print(f"Saved to {output_path}")


def main():
    parser = argparse.ArgumentParser(description='Scrape economics PhD placement data')
    parser.add_argument('--force', '-f', action='store_true',
                        help='Force re-scrape all pages, ignoring cache')
    args = parser.parse_args()

    print(f"{'='*50}")
    print("Economics PhD → Tech Placement Scraper")
    print(f"Force mode: {args.force}")
    print(f"{'='*50}")

    scraper = EconPhDScraper(force=args.force)
    df = scraper.scrape_all()

    if not df.empty:
        scraper.save(df, 'data/candidates.csv')

        # Print summary
        print(f"\n{'='*50}")
        print("SUMMARY BY SCHOOL:")
        print(df.groupby('school').size().sort_values(ascending=False))

        print(f"\n{'='*50}")
        print("TOP TECH PLACEMENTS:")
        if 'initial_placement' in df.columns:
            placements = df['initial_placement'].value_counts().head(10)
            print(placements)
    else:
        print("No candidates found. This may be due to:")
        print("- Website structure changes")
        print("- Rate limiting/blocking")
        print("- No tech placements in the scraped data")
        print("- All pages unchanged since last run (use --force to re-scrape)")


if __name__ == "__main__":
    main()
