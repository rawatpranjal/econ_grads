"""Brown University Economics department parser."""
from bs4 import BeautifulSoup
from typing import List, Dict
import re
from .base import SchoolParser


class BrownParser(SchoolParser):
    """Parser for Brown Economics department placement pages.

    URL: https://economics.brown.edu/academics/graduate/job-placement-results
    Format: Year sections with name -> placement listings
    """

    @property
    def school_name(self) -> str:
        return 'Brown'

    def parse(self, soup: BeautifulSoup) -> List[Dict]:
        """Parse candidates from Brown Economics placement page."""
        candidates = []
        seen_names = set()
        current_year = None

        # Brown uses h2/h3 year headers with lists of placements
        for element in soup.select('h2, h3, h4, p, li, div.field-item'):
            text = element.get_text(strip=True)

            # Check for year header (e.g., "2024", "2023-2024")
            year_match = re.search(r'20(2[0-5]|1[5-9])', text)
            if year_match and len(text) < 30:
                current_year = int('20' + year_match.group(1))
                continue

            # Look for "Name - Placement" or "Name: Placement" patterns
            for sep in [' - ', ': ', ' – ', ' — ', '→']:
                if sep in text:
                    parts = text.split(sep, 1)
                    if len(parts) == 2:
                        name = parts[0].strip()
                        placement = parts[1].strip()

                        # Validate name
                        if len(name) < 3 or len(name) > 80:
                            continue
                        if name.lower() in seen_names:
                            continue

                        # Check if tech placement
                        if self._is_tech_placement(placement):
                            seen_names.add(name.lower())
                            candidates.append(self.create_candidate(
                                name=name,
                                placement=self._normalize_placement(placement),
                                year=current_year
                            ))
                        break

        # Also try table parsing
        for table in soup.select('table'):
            rows = table.select('tr')
            for row in rows[1:]:  # Skip header
                cells = row.select('td')
                if len(cells) >= 2:
                    name = cells[0].get_text(strip=True)
                    placement = cells[-1].get_text(strip=True)

                    if len(name) < 3 or len(name) > 80:
                        continue
                    if name.lower() in seen_names:
                        continue

                    # Extract year from row
                    row_text = row.get_text()
                    year = self.extract_year(row_text) or current_year

                    if self._is_tech_placement(placement):
                        seen_names.add(name.lower())
                        candidates.append(self.create_candidate(
                            name=name,
                            placement=self._normalize_placement(placement),
                            year=year
                        ))

        return candidates

    def _is_tech_placement(self, placement: str) -> bool:
        """Check if placement is at a tech company."""
        if not placement:
            return False
        placement_lower = placement.lower()

        # Exclude academia
        if any(kw in placement_lower for kw in ['university', 'college', 'professor', 'postdoc', 'faculty']):
            return False

        return any(company in placement_lower for company in self.TECH_COMPANIES)

    def _normalize_placement(self, placement: str) -> str:
        """Normalize company name."""
        placement_lower = placement.lower()

        if 'amazon' in placement_lower:
            return 'Amazon'
        if 'google' in placement_lower:
            return 'Google'
        if 'meta' in placement_lower or 'facebook' in placement_lower:
            return 'Meta'
        if 'netflix' in placement_lower:
            return 'Netflix'
        if 'microsoft' in placement_lower:
            return 'Microsoft'
        if 'uber' in placement_lower:
            return 'Uber'
        if 'capital one' in placement_lower:
            return 'Capital One'

        return placement.strip()
