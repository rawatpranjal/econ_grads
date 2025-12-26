"""Columbia Economics department parser."""
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
from .base import SchoolParser


class ColumbiaParser(SchoolParser):
    """Parser for Columbia Economics department pages.

    URLs:
    - https://econ.columbia.edu/phd/job-market-candidates/
    - https://econ.columbia.edu/phd/placement/
    """

    @property
    def school_name(self) -> str:
        return 'Columbia'

    def parse(self, soup: BeautifulSoup) -> List[Dict]:
        """Parse candidates from Columbia Economics pages."""
        candidates = []
        seen_names = set()

        # Strategy 1: Tables with year headers (H3 before each table)
        current_year = None
        for elem in soup.select('h3, table'):
            if elem.name == 'h3':
                # Extract year from header like "2024 Placement Information"
                current_year = self.extract_year(elem.get_text())
            elif elem.name == 'table':
                table_candidates = self._parse_table(elem, override_year=current_year)
                for c in table_candidates:
                    if c['name'].lower() not in seen_names:
                        seen_names.add(c['name'].lower())
                        candidates.append(c)

        # Strategy 2: Card/profile structure (job market candidates)
        for card in soup.select('.person, .profile, .candidate, article, .views-row, .faculty-member'):
            candidate = self._parse_card(card)
            if candidate and candidate['name'].lower() not in seen_names:
                seen_names.add(candidate['name'].lower())
                candidates.append(candidate)

        # Strategy 3: Grid items
        for item in soup.select('.grid-item, .team-member, .people-item'):
            candidate = self._parse_grid_item(item)
            if candidate and candidate['name'].lower() not in seen_names:
                seen_names.add(candidate['name'].lower())
                candidates.append(candidate)

        # Strategy 4: Placement lists by year
        for section in soup.select('.placement-year, .year-section, details, .accordion-item'):
            section_candidates = self._parse_year_section(section)
            for c in section_candidates:
                if c['name'].lower() not in seen_names:
                    seen_names.add(c['name'].lower())
                    candidates.append(c)

        return candidates

    def _parse_table(self, table, override_year=None) -> List[Dict]:
        """Parse a placement table."""
        candidates = []
        rows = table.select('tr')

        header_row = rows[0] if rows else None
        headers = []
        if header_row:
            headers = [th.get_text(strip=True).lower() for th in header_row.select('th, td')]

        name_col = self._find_col(headers, ['name', 'student', 'candidate'])
        placement_col = self._find_col(headers, ['placement', 'employer', 'position', 'first', 'initial'])
        year_col = self._find_col(headers, ['year', 'class', 'cohort'])
        fields_col = self._find_col(headers, ['field', 'research', 'area'])

        for row in rows[1:]:
            cells = row.select('td')
            if len(cells) < 2:
                continue

            name = cells[name_col].get_text(strip=True) if name_col < len(cells) else cells[0].get_text(strip=True)
            if not name or len(name) < 3 or len(name) > 100:
                continue

            if name.lower() in ['name', 'candidate', 'student', '']:
                continue

            placement = ''
            if placement_col is not None and placement_col < len(cells):
                placement = cells[placement_col].get_text(strip=True)
            elif len(cells) > 1:
                placement = cells[1].get_text(strip=True)

            fields = ''
            if fields_col is not None and fields_col < len(cells):
                fields = cells[fields_col].get_text(strip=True)

            year = override_year
            if not year and year_col is not None and year_col < len(cells):
                year = self.extract_year(cells[year_col].get_text())
            if not year:
                year = self.extract_year(row.get_text())

            candidates.append(self.create_candidate(
                name=name,
                placement=placement,
                year=year,
                fields=fields
            ))

        return candidates

    def _find_col(self, headers, keywords):
        """Find column index matching any keyword."""
        for i, h in enumerate(headers):
            for kw in keywords:
                if kw in h:
                    return i
        return 0

    def _parse_card(self, card) -> Optional[Dict]:
        """Parse a profile/person card."""
        name_elem = card.select_one('h2, h3, h4, .name, .title, a.name, .person-name')
        if not name_elem:
            return None

        name = name_elem.get_text(strip=True)
        if not name or len(name) < 3 or len(name) > 100:
            return None

        skip_words = ['columbia', 'economics', 'department', 'placement', 'phd program']
        if any(w in name.lower() for w in skip_words):
            return None

        fields_elem = card.select_one('.research, .interests, .fields, .research-interests')
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
        """Parse a grid/team member item."""
        name_elem = item.select_one('h2, h3, h4, .name, .title, a')
        if not name_elem:
            return None

        name = name_elem.get_text(strip=True)
        if not name or len(name) < 3 or len(name) > 100:
            return None

        skip_words = ['columbia', 'economics', 'department']
        if any(w in name.lower() for w in skip_words):
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

    def _parse_year_section(self, section) -> List[Dict]:
        """Parse a section grouped by year."""
        candidates = []

        header = section.select_one('h2, h3, h4, summary, .year-header')
        year = self.extract_year(header.get_text() if header else section.get_text()[:50])

        for item in section.select('li, p, .placement-item'):
            text = item.get_text(separator=' ', strip=True)
            if not text or len(text) < 10:
                continue

            parts = text.replace(' - ', ', ').replace(' – ', ', ').split(',')
            name = parts[0].strip()

            if not name or len(name) < 3 or len(name) > 100:
                continue

            if name.isdigit() or name.lower() in ['class', 'year', 'placement']:
                continue

            placement = parts[1].strip() if len(parts) > 1 else ''

            candidates.append(self.create_candidate(
                name=name,
                placement=placement,
                year=year
            ))

        return candidates
