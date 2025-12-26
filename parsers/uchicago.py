"""University of Chicago Economics department parser."""
from bs4 import BeautifulSoup
from typing import List, Dict
from .base import SchoolParser


class UChicagoParser(SchoolParser):
    """Parser for UChicago Economics department pages.

    Note: UChicago's placement data is primarily in an external PDF.
    This parser handles both the PDF and any HTML page content.
    """

    @property
    def school_name(self) -> str:
        return 'University of Chicago'

    def parse(self, soup: BeautifulSoup) -> List[Dict]:
        """Parse candidates from UChicago Economics pages."""
        candidates = []

        # Strategy 0: Try PDF parsing first (primary data source)
        pdf_candidates = self._parse_pdf()
        candidates.extend(pdf_candidates)

        # If we got PDF data, that's the authoritative source
        if pdf_candidates:
            return candidates

        # Fallback to HTML parsing if PDF fails
        # Strategy 1: Person cards (UChicago uses specific classes)
        for card in soup.select('.person-card, .person, .profile, .views-row, article.candidate'):
            name_elem = card.select_one('h2, h3, h4, .name, .person-name, a')
            if not name_elem:
                continue

            name = name_elem.get_text(strip=True)
            if not name or len(name) < 3 or len(name) > 100:
                continue

            # Skip navigation/header elements
            if any(skip in name.lower() for skip in ['menu', 'navigation', 'search', 'home']):
                continue

            # Look for placement
            placement_elem = card.select_one('.placement, .position, .job, .employer')
            placement = placement_elem.get_text(strip=True) if placement_elem else ''

            # Look for fields
            fields_elem = card.select_one('.fields, .research, .interests, .specialty')
            fields = fields_elem.get_text(strip=True) if fields_elem else ''

            year = self.extract_year(card.get_text())
            candidates.append(self.create_candidate(name, placement, year, fields))

        # Strategy 2: Drupal/Views-based listing (common at UChicago)
        for item in soup.select('.views-row, .view-content > div'):
            links = item.select('a')
            for link in links:
                name = link.get_text(strip=True)
                if not name or len(name) < 3 or len(name) > 100:
                    continue
                if any(skip in name.lower() for skip in ['read more', 'view', 'click', 'learn']):
                    continue

                # Check surrounding text for placement
                parent_text = item.get_text(strip=True)
                placement = ''
                year = self.extract_year(parent_text)

                candidates.append(self.create_candidate(name, placement, year))

        # Strategy 3: Year-organized sections
        current_year = None
        for elem in soup.select('h2, h3, h4, li, p, div.field-item'):
            text = elem.get_text(strip=True)

            # Check for year header
            year_match = self.extract_year(text)
            if year_match and len(text) < 20:
                current_year = year_match
                continue

            # Look for name - placement pattern
            if current_year and 2020 <= current_year <= 2025:
                for sep in [' - ', ': ', ' – ', ', ']:
                    if sep in text:
                        parts = text.split(sep, 1)
                        if len(parts) == 2 and len(parts[0]) > 2 and len(parts[0]) < 80:
                            candidates.append(self.create_candidate(
                                parts[0], parts[1], current_year
                            ))
                        break

        return candidates

    def _parse_pdf(self) -> List[Dict]:
        """Parse placement data from UChicago's PDF."""
        try:
            from pdf_parser import UChicagoPDFParser
            parser = UChicagoPDFParser()
            return parser.parse()
        except ImportError:
            print("  [UChicago] PDF parser not available")
            return []
        except Exception as e:
            print(f"  [UChicago] PDF parsing failed: {e}")
            return []
