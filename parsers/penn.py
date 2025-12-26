"""University of Pennsylvania Economics department parser."""
from bs4 import BeautifulSoup
from typing import List, Dict
import re
from .base import SchoolParser


class PennParser(SchoolParser):
    """Parser for Penn Economics and Wharton placement pages.

    URLs:
    - https://economics.sas.upenn.edu/graduate/prospective-students/placement-information
    - https://doctoral.wharton.upenn.edu/career-placement/
    """

    @property
    def school_name(self) -> str:
        return 'University of Pennsylvania'

    def parse(self, soup: BeautifulSoup) -> List[Dict]:
        """Parse candidates from Penn Economics/Wharton placement pages."""
        candidates = []
        seen_names = set()
        current_year = None

        # Check if this is Wharton page (different format)
        page_text = soup.get_text().lower()
        is_wharton = 'wharton' in page_text

        if is_wharton:
            candidates.extend(self._parse_wharton(soup, seen_names))
        else:
            candidates.extend(self._parse_economics(soup, seen_names))

        return candidates

    def _parse_economics(self, soup: BeautifulSoup, seen_names: set) -> List[Dict]:
        """Parse Penn Economics department placement data."""
        candidates = []
        current_year = None

        # Penn Econ uses year headers followed by lists
        for element in soup.select('h2, h3, h4, p, li, tr'):
            text = element.get_text(strip=True)

            # Check for year header (e.g., "2023-2024", "2022-2023")
            year_match = re.search(r'20(2[0-5]|1[5-9])', text)
            if year_match and len(text) < 30 and '-' in text:
                current_year = int('20' + year_match.group(1))
                continue

            # Look for patterns like "Name - Company" or "Name, Company"
            for sep in [' - ', ' – ', ' — ', ', ']:
                if sep in text:
                    parts = text.split(sep)
                    if len(parts) >= 2:
                        name = parts[0].strip()
                        placement = parts[-1].strip()

                        # Validate
                        if len(name) < 3 or len(name) > 80:
                            continue
                        if name.lower() in seen_names:
                            continue

                        if self._is_tech_placement(placement):
                            seen_names.add(name.lower())
                            candidates.append(self.create_candidate(
                                name=name,
                                placement=self._normalize_placement(placement),
                                year=current_year
                            ))
                        break

        # Also parse tables
        for table in soup.select('table'):
            rows = table.select('tr')
            for row in rows:
                cells = row.select('td, th')
                if len(cells) >= 2:
                    # Try different column arrangements
                    for i, cell in enumerate(cells):
                        cell_text = cell.get_text(strip=True)
                        if self._is_tech_placement(cell_text):
                            # Found a tech company, name is likely in previous cell
                            name_cell = cells[i-1] if i > 0 else cells[0]
                            name = name_cell.get_text(strip=True)

                            if len(name) < 3 or len(name) > 80:
                                continue
                            if name.lower() in seen_names:
                                continue

                            # Get year from row
                            row_text = row.get_text()
                            year = self.extract_year(row_text) or None

                            seen_names.add(name.lower())
                            candidates.append(self.create_candidate(
                                name=name,
                                placement=self._normalize_placement(cell_text),
                                year=year
                            ))
                            break

        return candidates

    def _parse_wharton(self, soup: BeautifulSoup, seen_names: set) -> List[Dict]:
        """Parse Wharton doctoral placement data."""
        candidates = []
        current_year = None
        current_program = ''

        # Wharton lists companies by year under program headers
        for element in soup.select('h2, h3, h4, p, li, strong'):
            text = element.get_text(strip=True)

            # Check for program header
            if any(p in text.lower() for p in ['statistics', 'finance', 'economics', 'applied economics']):
                current_program = text
                continue

            # Check for year (e.g., "2024", "2023")
            year_match = re.match(r'^20(2[0-5]|1[5-9])$', text.strip())
            if year_match:
                current_year = int('20' + year_match.group(1))
                continue

            # Check if this is a tech company
            if self._is_tech_placement(text):
                # Wharton doesn't list names, just companies
                # We'll create entries with company as placement
                placement = self._normalize_placement(text)
                if placement.lower() not in seen_names:
                    seen_names.add(placement.lower())
                    candidates.append({
                        'name': f'Wharton PhD ({current_year or 2024})',
                        'school': self.school_name,
                        'graduation_year': current_year or 2024,
                        'research_fields': current_program,
                        'initial_placement': placement,
                        'initial_role': '',
                        'current_placement': '',
                        'current_role': '',
                        'linkedin_url': ''
                    })

        return candidates

    def _is_tech_placement(self, placement: str) -> bool:
        """Check if placement is at a tech company."""
        if not placement:
            return False
        placement_lower = placement.lower()

        # Exclude academia
        if any(kw in placement_lower for kw in ['university', 'college', 'professor', 'postdoc', 'faculty', 'school of']):
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
        if 'openai' in placement_lower:
            return 'OpenAI'
        if 'microsoft' in placement_lower:
            return 'Microsoft'
        if 'uber' in placement_lower:
            return 'Uber'
        if 'two sigma' in placement_lower:
            return 'Two Sigma'
        if 'jane street' in placement_lower:
            return 'Jane Street'
        if 'citadel' in placement_lower:
            return 'Citadel'
        if 'vanguard' in placement_lower:
            return 'Vanguard'
        if 'blackrock' in placement_lower:
            return 'BlackRock'

        return placement.strip()
