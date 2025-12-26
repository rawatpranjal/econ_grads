"""University of Maryland Economics department parser."""
from bs4 import BeautifulSoup
from typing import List, Dict
import re
from .base import SchoolParser


class MarylandParser(SchoolParser):
    """Parser for Maryland Economics department placement pages.

    URL: https://www.econ.umd.edu/graduate/job-placement
    Format: Year-based accordion sections with placements
    """

    @property
    def school_name(self) -> str:
        return 'University of Maryland'

    def parse(self, soup: BeautifulSoup) -> List[Dict]:
        """Parse candidates from Maryland Economics placement page."""
        candidates = []
        seen_names = set()
        current_year = None

        # Maryland uses accordion/expandable sections by year
        for element in soup.select('.accordion-item, .panel, .field-item, h2, h3, h4, p, li, tr'):
            text = element.get_text(strip=True)

            # Check for year header
            year_match = re.search(r'20(2[0-5]|1[5-9])', text)
            if year_match and len(text) < 30:
                current_year = int('20' + year_match.group(1))
                continue

            # Look for "Name - Company" or "Name, Company" patterns
            for sep in [' - ', ' – ', ' — ', ': ', ', ']:
                if sep in text:
                    parts = text.split(sep)
                    if len(parts) >= 2:
                        name = parts[0].strip()
                        placement = parts[-1].strip()

                        # Validate name
                        if len(name) < 3 or len(name) > 80:
                            continue
                        if name.lower() in seen_names:
                            continue
                        # Skip year-only entries
                        if name.isdigit():
                            continue

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
                    # Try to find year column
                    year = None
                    for cell in cells:
                        cell_text = cell.get_text(strip=True)
                        year_match = re.match(r'^20(2[0-5]|1[5-9])$', cell_text)
                        if year_match:
                            year = int('20' + year_match.group(1))
                            break

                    # First non-year cell is likely name
                    name = None
                    placement = None
                    for i, cell in enumerate(cells):
                        cell_text = cell.get_text(strip=True)
                        if cell_text.isdigit() and len(cell_text) == 4:
                            continue  # Skip year cell
                        if not name:
                            name = cell_text
                        elif self._is_tech_placement(cell_text):
                            placement = cell_text
                            break

                    if name and placement:
                        if len(name) < 3 or len(name) > 80:
                            continue
                        if name.lower() in seen_names:
                            continue

                        seen_names.add(name.lower())
                        candidates.append(self.create_candidate(
                            name=name,
                            placement=self._normalize_placement(placement),
                            year=year or current_year
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
        if 'microsoft' in placement_lower:
            return 'Microsoft'
        if 'citi' in placement_lower:
            return 'Citi'
        if 'capital one' in placement_lower:
            return 'Capital One'
        if 'dimensional' in placement_lower:
            return 'Dimensional Fund Advisors'

        return placement.strip()
