#!/usr/bin/env python3
"""
PDF parsing for economics PhD placement data.
Handles external PDF sources like UChicago Box.com links.
"""
import io
import re
import requests
from typing import List, Dict, Optional
from pathlib import Path

try:
    import pdfplumber
except ImportError:
    pdfplumber = None
    print("Warning: pdfplumber not installed. Run: pip install pdfplumber")

# Import tech companies and normalization from main scraper
from normalize import is_academia, normalize_company


class PDFPlacementParser:
    """Parse placement data from PDF documents."""

    # Tech companies to filter for
    TECH_COMPANIES = {
        # Big Tech
        'google', 'meta', 'facebook', 'amazon', 'apple', 'microsoft', 'netflix',
        # Tech Unicorns / Marketplaces
        'uber', 'lyft', 'airbnb', 'stripe', 'doordash', 'instacart', 'dropbox',
        'slack', 'zoom', 'spotify', 'pinterest', 'snap', 'twitter', 'x corp',
        'tiktok', 'bytedance', 'reddit', 'discord', 'nextdoor', 'thumbtack', 'turo',
        # AI/ML
        'openai', 'anthropic', 'deepmind', 'cohere', 'scale ai', 'databricks',
        'perplexity', 'xai', 'groq', 'codeium', 'cursor', 'anysphere',
        # Fintech
        'robinhood', 'coinbase', 'plaid', 'square', 'block', 'affirm', 'chime',
        'sofi', 'brex', 'toast', 'marqeta', 'klarna', 'revolut',
        # Quant Finance / Trading
        'two sigma', 'jane street', 'citadel', 'de shaw', 'renaissance', 'aqr',
        'point72', 'bridgewater', 'millennium', 'squarepoint', 'rokos',
        # Enterprise/Cloud
        'salesforce', 'oracle', 'snowflake', 'palantir', 'servicenow', 'workday',
        'splunk', 'crowdstrike', 'datadog', 'deel', 'rippling', 'gusto',
        # E-commerce / Logistics
        'shopify', 'ebay', 'wayfair', 'etsy', 'walmart', 'flexport', 'faire',
        # Hardware/Chips
        'nvidia', 'intel', 'amd', 'qualcomm', 'tesla', 'spacex',
        # Real Estate Tech
        'zillow', 'redfin', 'opendoor', 'compass', 'houzz',
        # Travel Tech
        'booking', 'expedia', 'tripadvisor', 'navan', 'hopper', 'kayak',
        # Other Tech
        'linkedin', 'indeed', 'glassdoor', 'yelp', 'doximity', 'veeva',
        'twilio', 'okta', 'cloudflare', 'mongodb', 'elastic',
        'asana', 'notion', 'figma', 'canva', 'airtable',
        'grammarly', 'duolingo', 'coursera', 'udemy', 'pandora', 'adobe',
    }

    def __init__(self, school_name: str):
        self.school_name = school_name

    def fetch_pdf(self, url: str) -> Optional[bytes]:
        """Download PDF from URL (handles Box.com public links)."""
        try:
            # Box.com shared links need special handling
            if 'box.com' in url:
                download_url = self._convert_box_link(url)
                if not download_url:
                    return None
            else:
                download_url = url

            print(f"  [PDF] Downloading: {download_url[:80]}...")
            response = requests.get(download_url, timeout=60, allow_redirects=True)
            response.raise_for_status()

            # Verify it's a PDF
            content_type = response.headers.get('content-type', '')
            if 'pdf' not in content_type.lower() and not response.content[:4] == b'%PDF':
                print(f"  [PDF] Warning: Response may not be PDF (content-type: {content_type})")

            return response.content

        except requests.RequestException as e:
            print(f"  [PDF] Error downloading: {e}")
            return None

    def _convert_box_link(self, share_url: str) -> Optional[str]:
        """Convert Box.com share URL to direct download URL.

        Box share links format: https://uchicago.app.box.com/s/{shared_id}
        We need to fetch the page and extract the actual download link.
        """
        try:
            # First, fetch the share page to get file info
            response = requests.get(share_url, timeout=30)
            response.raise_for_status()

            # Look for download link pattern in the page
            # Box typically has a download button or direct file link
            # Pattern: /file/{file_id} or download endpoint

            # Try to find file ID in the response
            file_id_match = re.search(r'"typedID":"f_(\d+)"', response.text)
            if file_id_match:
                file_id = file_id_match.group(1)
                # Construct download URL
                # Box API format for public file download
                return f"https://uchicago.app.box.com/index.php?rm=box_download_shared_file&shared_name={share_url.split('/s/')[-1]}&file_id=f_{file_id}"

            # Alternative: look for direct download link
            download_match = re.search(r'(https://[^"]+\.box\.com/shared/static/[^"]+\.pdf)', response.text)
            if download_match:
                return download_match.group(1)

            # Fallback: try the share URL with download parameter
            shared_name = share_url.split('/s/')[-1]
            return f"https://uchicago.app.box.com/public/static/{shared_name}"

        except Exception as e:
            print(f"  [PDF] Error converting Box link: {e}")
            return None

    def parse_pdf(self, pdf_bytes: bytes) -> List[Dict]:
        """Extract placement data from PDF."""
        if pdfplumber is None:
            print("  [PDF] pdfplumber not available")
            return []

        candidates = []

        try:
            with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                print(f"  [PDF] Processing {len(pdf.pages)} pages...")

                for page_num, page in enumerate(pdf.pages):
                    # Strategy 1: Extract tables
                    tables = page.extract_tables()
                    for table in tables:
                        table_candidates = self._parse_table(table)
                        candidates.extend(table_candidates)

                    # Strategy 2: If no tables, try text extraction
                    if not tables:
                        text = page.extract_text()
                        if text:
                            text_candidates = self._parse_text(text)
                            candidates.extend(text_candidates)

        except Exception as e:
            print(f"  [PDF] Error parsing PDF: {e}")

        print(f"  [PDF] Found {len(candidates)} candidates")
        return candidates

    def _parse_table(self, table: List[List]) -> List[Dict]:
        """Parse a table extracted from PDF."""
        candidates = []
        if not table or len(table) < 2:
            return candidates

        header = [str(cell).lower() if cell else '' for cell in table[0]]

        # Try to identify column indices
        name_col = self._find_column(header, ['name', 'student', 'candidate', 'graduate'])
        year_col = self._find_column(header, ['year', 'graduation', 'cohort'])
        placement_col = self._find_column(header, ['placement', 'employer', 'company', 'position', 'job'])

        # If no clear header, assume first column is name, last is placement
        if name_col is None:
            name_col = 0
        if placement_col is None:
            placement_col = len(header) - 1 if len(header) > 1 else 1

        for row in table[1:]:
            if not row or len(row) <= max(name_col, placement_col):
                continue

            name = str(row[name_col]).strip() if row[name_col] else ''
            placement = str(row[placement_col]).strip() if placement_col < len(row) and row[placement_col] else ''

            # Skip header-like rows
            if name.lower() in ['name', 'student', 'candidate', 'graduate', '']:
                continue

            # Skip if name is too short or too long
            if len(name) < 3 or len(name) > 100:
                continue

            # Extract year if available
            year = None
            if year_col is not None and year_col < len(row) and row[year_col]:
                year = self._extract_year(str(row[year_col]))
            if year is None:
                year = self._extract_year(name + ' ' + placement)

            # Filter for tech placements
            if not self._is_tech_placement(placement):
                continue

            candidates.append({
                'name': name,
                'school': self.school_name,
                'graduation_year': year or 2024,
                'research_fields': '',
                'initial_placement': normalize_company(placement),
                'initial_role': '',
                'current_placement': '',
                'current_role': '',
                'linkedin_url': ''
            })

        return candidates

    def _parse_text(self, text: str) -> List[Dict]:
        """Parse freeform text for placement data.

        UChicago PDF format: "Company field(s) Name" per line
        Example: "Amazon (3) international trade Maria Ignacia Cuevas de Saint Pierre"
        """
        candidates = []
        lines = text.split('\n')
        current_year = None
        in_private_sector = False

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Check for year header (e.g., "2024 – 2025", "2023 – 2024")
            year = self._extract_year(line)
            if year and ('–' in line or '-' in line) and len(line) < 30:
                current_year = year
                continue

            # Check for section headers
            if 'private sector' in line.lower():
                in_private_sector = True
                continue
            elif 'academic' in line.lower() or 'post-doc' in line.lower() or 'public sector' in line.lower():
                in_private_sector = False
                continue

            # Only parse private sector entries
            if not in_private_sector:
                continue

            # UChicago format: "Company field Name" - company at start, name at end
            # Try to extract: tech company at start, name is the capitalized words at end
            line_lower = line.lower()

            # Check if line starts with a tech company
            matched_company = None
            for company in self.TECH_COMPANIES:
                if line_lower.startswith(company):
                    matched_company = company.title()
                    break

            if not matched_company:
                continue

            # Extract name - typically the last 2-4 capitalized words
            # Remove company name and field from start, name is what remains
            words = line.split()

            # Find where the name starts (after company and field keywords)
            # Common fields: "international trade", "industrial organization", "macroeconomics", etc.
            name_words = []
            found_name_start = False

            for i, word in enumerate(words):
                # Skip if it's the company name
                if i == 0 or (i == 1 and words[0].lower() in self.TECH_COMPANIES):
                    continue
                # Skip parenthetical counts like "(3)"
                if word.startswith('(') and word.endswith(')'):
                    continue
                # Skip field keywords (lowercase words)
                if word.islower() or word.lower() in ['and', 'of', 'the', 'for']:
                    continue
                # This looks like a name (capitalized)
                if word and word[0].isupper():
                    found_name_start = True
                if found_name_start:
                    name_words.append(word)

            name = ' '.join(name_words)
            if len(name) < 3 or len(name) > 100:
                continue

            candidates.append({
                'name': name,
                'school': self.school_name,
                'graduation_year': current_year or 2024,
                'research_fields': '',
                'initial_placement': matched_company,
                'initial_role': '',
                'current_placement': '',
                'current_role': '',
                'linkedin_url': ''
            })

        # Also try the original separator-based parsing as fallback
        current_year = None
        for line in lines:
            line = line.strip()
            if not line:
                continue

            year = self._extract_year(line)
            if year and len(line) < 20:
                current_year = year
                continue

            for sep in [' - ', ': ', ' – ', ' — ']:
                if sep in line:
                    parts = line.split(sep, 1)
                    if len(parts) >= 2:
                        name = parts[0].strip()
                        placement = parts[1].strip()

                        if len(name) < 3 or len(name) > 100:
                            continue

                        if not self._is_tech_placement(placement):
                            continue

                        # Avoid duplicates
                        if any(c['name'] == name for c in candidates):
                            continue

                        candidates.append({
                            'name': name,
                            'school': self.school_name,
                            'graduation_year': current_year or 2024,
                            'research_fields': '',
                            'initial_placement': normalize_company(placement),
                            'initial_role': '',
                            'current_placement': '',
                            'current_role': '',
                            'linkedin_url': ''
                        })
                        break

        return candidates

    def _find_column(self, header: List[str], keywords: List[str]) -> Optional[int]:
        """Find column index matching any of the keywords."""
        for i, cell in enumerate(header):
            cell_lower = cell.lower() if cell else ''
            if any(kw in cell_lower for kw in keywords):
                return i
        return None

    def _extract_year(self, text: str) -> Optional[int]:
        """Extract a year (2015-2025) from text."""
        if not text:
            return None
        matches = re.findall(r'20(1[5-9]|2[0-5])', text)
        if matches:
            return int('20' + matches[0])
        return None

    def _is_tech_placement(self, placement: str) -> bool:
        """Check if a placement is at a tech company."""
        if not placement:
            return False
        placement_lower = placement.lower()

        # Exclude academia
        if is_academia(placement):
            return False

        return any(company in placement_lower for company in self.TECH_COMPANIES)


# UChicago-specific parser
class UChicagoPDFParser(PDFPlacementParser):
    """Parser for UChicago Economics PDF placement data."""

    # UChicago Box.com PDF URL
    PDF_URL = "https://uchicago.app.box.com/s/14o5hl9hoyuapm30xvzi48qi74oetu9c"

    def __init__(self):
        super().__init__('University of Chicago')

    def parse(self) -> List[Dict]:
        """Fetch and parse UChicago placement PDF."""
        pdf_bytes = self.fetch_pdf(self.PDF_URL)
        if not pdf_bytes:
            return []
        return self.parse_pdf(pdf_bytes)


def main():
    """Test PDF parsing."""
    print("Testing UChicago PDF Parser...")
    parser = UChicagoPDFParser()
    candidates = parser.parse()

    print(f"\nFound {len(candidates)} tech placement candidates:")
    for c in candidates[:10]:
        print(f"  {c['name']} ({c['graduation_year']}) -> {c['initial_placement']}")


if __name__ == "__main__":
    main()
