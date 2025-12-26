"""Carnegie Mellon University Economics department parser."""
from bs4 import BeautifulSoup
from typing import List, Dict
import re
from .base import SchoolParser


class CMUParser(SchoolParser):
    """Parser for CMU Tepper School PhD placement pages.

    URL: https://www.cmu.edu/tepper/programs/phd/job-market
    Format: Table with year/name/placement columns
    """

    @property
    def school_name(self) -> str:
        return 'Carnegie Mellon'

    def parse(self, soup: BeautifulSoup) -> List[Dict]:
        """Parse candidates from CMU Tepper placement page."""
        candidates = []
        seen_names = set()
        current_program = ''

        # CMU Tepper uses tables organized by program
        for element in soup.select('h2, h3, h4, table'):
            tag_name = element.name

            # Track program headers
            if tag_name in ['h2', 'h3', 'h4']:
                text = element.get_text(strip=True).lower()
                if 'economics' in text:
                    current_program = 'Economics'
                elif 'operations' in text or 'aco' in text:
                    current_program = 'Operations Research'
                elif 'finance' in text or 'financial' in text:
                    current_program = 'Financial Economics'
                elif 'behavior' in text:
                    current_program = 'Behavioral Economics'
                elif 'statistic' in text:
                    current_program = 'Statistics'
                continue

            # Parse tables
            if tag_name == 'table':
                rows = element.select('tr')

                # Try to identify header
                header_row = rows[0] if rows else None
                header_cells = header_row.select('th, td') if header_row else []
                header_text = [c.get_text(strip=True).lower() for c in header_cells]

                # Find column indices
                name_col = 0
                placement_col = -1
                year_col = -1

                for i, h in enumerate(header_text):
                    if 'name' in h or 'student' in h or 'candidate' in h:
                        name_col = i
                    elif 'placement' in h or 'employer' in h or 'position' in h or 'company' in h:
                        placement_col = i
                    elif 'year' in h or 'cohort' in h or 'graduation' in h:
                        year_col = i

                # Default if no header detected
                if placement_col < 0 and len(header_cells) > 1:
                    placement_col = len(header_cells) - 1

                for row in rows[1:]:  # Skip header
                    cells = row.select('td')
                    if len(cells) < 2:
                        continue

                    name = cells[name_col].get_text(strip=True) if name_col < len(cells) else ''
                    placement = cells[placement_col].get_text(strip=True) if 0 <= placement_col < len(cells) else ''

                    # Validate name
                    if len(name) < 3 or len(name) > 80:
                        continue
                    if name.lower() in seen_names:
                        continue
                    if name.lower() in ['name', 'candidate', 'student', '']:
                        continue

                    # Extract year
                    year = None
                    if 0 <= year_col < len(cells):
                        year = self.extract_year(cells[year_col].get_text())
                    if year is None:
                        year = self.extract_year(row.get_text())

                    if self._is_tech_placement(placement):
                        seen_names.add(name.lower())
                        candidates.append({
                            'name': name,
                            'school': self.school_name,
                            'graduation_year': year or 2024,
                            'research_fields': current_program,
                            'initial_placement': self._normalize_placement(placement),
                            'initial_role': '',
                            'current_placement': '',
                            'current_role': '',
                            'linkedin_url': ''
                        })

        # Also try list-based parsing for non-table formats
        current_year = None
        for element in soup.select('h2, h3, h4, p, li'):
            text = element.get_text(strip=True)

            # Check for year
            year_match = re.match(r'^20(2[0-5]|1[5-9])$', text.strip())
            if year_match:
                current_year = int('20' + year_match.group(1))
                continue

            # Look for "Name - Company" patterns
            for sep in [' - ', ' – ', ' — ', ': ']:
                if sep in text:
                    parts = text.split(sep)
                    if len(parts) >= 2:
                        name = parts[0].strip()
                        placement = parts[-1].strip()

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
        if 'microsoft' in placement_lower:
            return 'Microsoft'
        if 'wayfair' in placement_lower:
            return 'Wayfair'
        if 'huawei' in placement_lower:
            return 'Huawei'
        if 'boeing' in placement_lower:
            return 'Boeing'
        if 'ibm' in placement_lower:
            return 'IBM'
        if 'walmart' in placement_lower:
            return 'Walmart'
        if 'goldman' in placement_lower:
            return 'Goldman Sachs'
        if 'mckinsey' in placement_lower:
            return 'McKinsey'
        if 'citadel' in placement_lower:
            return 'Citadel'

        return placement.strip()
