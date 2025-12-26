"""Yale Economics department parser."""
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
from .base import SchoolParser


class YaleParser(SchoolParser):
    """Parser for Yale Economics department pages.

    Yale uses a mix of table and accordion/expandable structures.
    Job market page: https://economics.yale.edu/graduate/job-market
    Placement page: https://economics.yale.edu/graduate/placement
    """

    @property
    def school_name(self) -> str:
        return 'Yale'

    def parse(self, soup: BeautifulSoup) -> List[Dict]:
        """Parse candidates from Yale Economics pages."""
        candidates = []
        seen_names = set()

        # Strategy 1: Tables (primary for placement history)
        for table in soup.select('table'):
            table_candidates = self._parse_table(table)
            for c in table_candidates:
                if c['name'].lower() not in seen_names:
                    seen_names.add(c['name'].lower())
                    candidates.append(c)

        # Strategy 2: Accordion/expandable sections
        for accordion in soup.select('.accordion-item, .expandable, .panel, .collapse-item'):
            candidate = self._parse_accordion(accordion)
            if candidate and candidate['name'].lower() not in seen_names:
                seen_names.add(candidate['name'].lower())
                candidates.append(candidate)

        # Strategy 3: Card/profile structures
        for card in soup.select('.person, .profile, .candidate, .views-row, article'):
            candidate = self._parse_card(card)
            if candidate and candidate['name'].lower() not in seen_names:
                seen_names.add(candidate['name'].lower())
                candidates.append(candidate)

        # Strategy 4: Grid layouts
        for item in soup.select('.grid-item, .person-grid-item, .student-card'):
            candidate = self._parse_grid_item(item)
            if candidate and candidate['name'].lower() not in seen_names:
                seen_names.add(candidate['name'].lower())
                candidates.append(candidate)

        return candidates

    def _parse_table(self, table) -> List[Dict]:
        """Parse a placement table."""
        candidates = []
        rows = table.select('tr')

        # Try to identify header
        header_row = rows[0] if rows else None
        header_cells = header_row.select('th, td') if header_row else []
        header_text = [c.get_text(strip=True).lower() for c in header_cells]

        # Find column indices
        name_col = 0
        placement_col = -1
        year_col = -1
        fields_col = -1

        for i, h in enumerate(header_text):
            if 'name' in h or 'student' in h or 'candidate' in h:
                name_col = i
            elif 'placement' in h or 'employer' in h or 'position' in h:
                placement_col = i
            elif 'year' in h or 'cohort' in h:
                year_col = i
            elif 'field' in h or 'research' in h or 'area' in h:
                fields_col = i

        # Default: if no clear columns, assume first is name, last is placement
        if placement_col < 0 and len(header_cells) > 1:
            placement_col = len(header_cells) - 1

        for row in rows[1:]:  # Skip header
            cells = row.select('td')
            if len(cells) < 2:
                continue

            name = cells[name_col].get_text(strip=True) if name_col < len(cells) else ''
            if not name or len(name) < 3 or len(name) > 100:
                continue

            if name.lower() in ['name', 'candidate', 'student', '']:
                continue

            placement = cells[placement_col].get_text(strip=True) if 0 <= placement_col < len(cells) else ''
            fields = cells[fields_col].get_text(strip=True) if 0 <= fields_col < len(cells) else ''

            year = None
            if 0 <= year_col < len(cells):
                year = self.extract_year(cells[year_col].get_text())
            if year is None:
                year = self.extract_year(row.get_text())

            candidates.append(self.create_candidate(
                name=name,
                placement=placement,
                year=year,
                fields=fields
            ))

        return candidates

    def _parse_accordion(self, accordion) -> Optional[Dict]:
        """Parse an accordion/expandable section."""
        # Header usually contains name
        header = accordion.select_one('.accordion-header, .panel-heading, .collapse-header, button')
        if not header:
            return None

        name = header.get_text(strip=True)
        if not name or len(name) < 3 or len(name) > 100:
            return None

        # Skip year-only headers
        if name.isdigit() or (len(name) == 4 and name.startswith('20')):
            return None

        # Body contains details
        body = accordion.select_one('.accordion-body, .panel-body, .collapse-body, .collapse')

        fields = ''
        placement = ''
        if body:
            fields_elem = body.select_one('.research, .interests, .fields')
            fields = fields_elem.get_text(strip=True) if fields_elem else ''

            placement_elem = body.select_one('.placement, .position, .employer')
            placement = placement_elem.get_text(strip=True) if placement_elem else ''

        year = self.extract_year(accordion.get_text())

        return self.create_candidate(
            name=name,
            placement=placement,
            year=year,
            fields=fields
        )

    def _parse_card(self, card) -> Optional[Dict]:
        """Parse a profile/person card."""
        name_elem = card.select_one('h2 a, h3 a, h4 a, h2, h3, h4, .name, .title a, .title')
        if not name_elem:
            return None

        name = name_elem.get_text(strip=True)
        if not name or len(name) < 3 or len(name) > 100:
            return None

        # Skip garbage
        if any(g in name.lower() for g in ['yale', 'building', 'campus', 'click', 'website']):
            return None

        fields_elem = card.select_one('.research, .interests, .fields, .research-areas')
        fields = fields_elem.get_text(strip=True) if fields_elem else ''

        placement_elem = card.select_one('.placement, .position, .employer')
        placement = placement_elem.get_text(strip=True) if placement_elem else ''

        year = self.extract_year(card.get_text())

        return self.create_candidate(
            name=name,
            placement=placement,
            year=year,
            fields=fields
        )

    def _parse_grid_item(self, item) -> Optional[Dict]:
        """Parse a grid item."""
        name_elem = item.select_one('h2, h3, h4, a, .name, .title')
        if not name_elem:
            return None

        name = name_elem.get_text(strip=True)
        if not name or len(name) < 3 or len(name) > 100:
            return None

        fields_elem = item.select_one('.research, .interests, .field')
        fields = fields_elem.get_text(strip=True) if fields_elem else ''

        placement_elem = item.select_one('.placement, .position')
        placement = placement_elem.get_text(strip=True) if placement_elem else ''

        year = self.extract_year(item.get_text())

        return self.create_candidate(
            name=name,
            placement=placement,
            year=year,
            fields=fields
        )
