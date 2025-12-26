"""NYU Economics department parser."""
from bs4 import BeautifulSoup
from typing import List, Dict
from .base import SchoolParser


class NYUParser(SchoolParser):
    """Parser for NYU Economics department pages."""

    @property
    def school_name(self) -> str:
        return 'NYU'

    def parse(self, soup: BeautifulSoup) -> List[Dict]:
        """Parse candidates from NYU Economics pages."""
        candidates = []

        # Strategy 1: NYU often uses accordions or expandable sections
        for section in soup.select('.accordion-item, .expandable, .panel, .card'):
            header = section.select_one('.accordion-header, .panel-heading, h3, h4')
            if not header:
                continue

            # Try to get year from header
            header_text = header.get_text(strip=True)
            year = self.extract_year(header_text)

            # Get content from body
            body = section.select_one('.accordion-body, .panel-body, .card-body')
            if not body:
                body = section

            # Look for person info in body
            for item in body.select('li, p, div.person'):
                text = item.get_text(strip=True)
                if len(text) < 5 or len(text) > 200:
                    continue

                # Try different separators
                for sep in [' - ', ': ', ' – ', ' — ', ', ']:
                    if sep in text:
                        parts = text.split(sep, 1)
                        if len(parts) == 2 and len(parts[0]) > 2 and len(parts[0]) < 80:
                            item_year = self.extract_year(text) or year
                            if item_year and (item_year < 2020 or item_year > 2025):
                                continue
                            candidates.append(self.create_candidate(
                                parts[0], parts[1], item_year
                            ))
                        break

        # Strategy 2: Grid/card layouts
        for card in soup.select('.person-grid-item, .faculty-grid-item, .student-card, article'):
            name_elem = card.select_one('h2, h3, h4, .name, .title, a')
            if not name_elem:
                continue

            name = name_elem.get_text(strip=True)
            if not name or len(name) < 3 or len(name) > 100:
                continue

            # Skip navigation elements
            if any(skip in name.lower() for skip in ['menu', 'search', 'home', 'back']):
                continue

            placement_elem = card.select_one('.placement, .position, .employer, .subtitle')
            placement = placement_elem.get_text(strip=True) if placement_elem else ''

            year = self.extract_year(card.get_text())
            candidates.append(self.create_candidate(name, placement, year))

        # Strategy 3: Tables
        for table in soup.select('table'):
            rows = table.select('tr')
            for row in rows[1:]:
                cells = row.select('td')
                if len(cells) >= 2:
                    name = cells[0].get_text(strip=True)
                    placement = cells[-1].get_text(strip=True)

                    if name.lower() in ['name', 'student', 'candidate', 'year']:
                        continue
                    if len(name) > 2 and len(name) < 100:
                        year = self.extract_year(row.get_text())
                        candidates.append(self.create_candidate(name, placement, year))

        # Strategy 4: Simple year-grouped lists
        current_year = None
        for elem in soup.select('h2, h3, h4, li, p'):
            text = elem.get_text(strip=True)

            # Year header
            year_match = self.extract_year(text)
            if year_match and len(text) < 20:
                current_year = year_match
                continue

            if current_year and 2020 <= current_year <= 2025:
                for sep in [' - ', ': ', ' – ']:
                    if sep in text:
                        parts = text.split(sep, 1)
                        if len(parts) == 2 and len(parts[0]) > 2 and len(parts[0]) < 80:
                            candidates.append(self.create_candidate(
                                parts[0], parts[1], current_year
                            ))
                        break

        return candidates
