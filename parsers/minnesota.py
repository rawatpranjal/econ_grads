"""University of Minnesota Economics department parser."""
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
from .base import SchoolParser


class MinnesotaParser(SchoolParser):
    """Parser for University of Minnesota Economics department pages.

    URLs:
    - https://cla.umn.edu/economics/people/job-market-candidates
    - https://apec.umn.edu/graduate/placement-recent-graduates
    """

    @property
    def school_name(self) -> str:
        return 'University of Minnesota'

    def parse(self, soup: BeautifulSoup) -> List[Dict]:
        """Parse candidates from Minnesota Economics pages."""
        candidates = []
        seen_names = set()

        # Strategy 1: Table structure
        for table in soup.select('table'):
            table_candidates = self._parse_table(table)
            for c in table_candidates:
                if c['name'].lower() not in seen_names:
                    seen_names.add(c['name'].lower())
                    candidates.append(c)

        # Strategy 2: Card/profile structure
        for card in soup.select('.person, .profile, .candidate, article, .views-row, .people-listing'):
            candidate = self._parse_card(card)
            if candidate and candidate['name'].lower() not in seen_names:
                seen_names.add(candidate['name'].lower())
                candidates.append(candidate)

        # Strategy 3: Year-grouped sections
        for section in soup.select('.year-section, section, details'):
            section_candidates = self._parse_year_section(section)
            for c in section_candidates:
                if c['name'].lower() not in seen_names:
                    seen_names.add(c['name'].lower())
                    candidates.append(c)

        # Strategy 4: Lists
        for ul in soup.select('ul'):
            list_candidates = self._parse_list(ul)
            for c in list_candidates:
                if c['name'].lower() not in seen_names:
                    seen_names.add(c['name'].lower())
                    candidates.append(c)

        return candidates

    def _parse_table(self, table) -> List[Dict]:
        """Parse a placement table."""
        candidates = []
        rows = table.select('tr')

        header_row = rows[0] if rows else None
        headers = []
        if header_row:
            headers = [th.get_text(strip=True).lower() for th in header_row.select('th, td')]

        name_col = self._find_col(headers, ['name', 'student', 'candidate'])
        placement_col = self._find_col(headers, ['placement', 'employer', 'position', 'first'])
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

            year = None
            if year_col is not None and year_col < len(cells):
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
        name_elem = card.select_one('h2, h3, h4, .name, .title, a')
        if not name_elem:
            return None

        name = name_elem.get_text(strip=True)
        if not name or len(name) < 3 or len(name) > 100:
            return None

        skip_words = ['minnesota', 'economics', 'department', 'placement']
        if any(w in name.lower() for w in skip_words):
            return None

        fields_elem = card.select_one('.research, .interests, .fields')
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

    def _parse_year_section(self, section) -> List[Dict]:
        """Parse a section grouped by year."""
        candidates = []

        header = section.select_one('h2, h3, h4, summary, .year-header')
        year = self.extract_year(header.get_text() if header else section.get_text()[:50])

        for item in section.select('li, p'):
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

    def _parse_list(self, ul) -> List[Dict]:
        """Parse a list."""
        candidates = []

        if ul.find_parent('nav') or ul.find_parent('header'):
            return candidates

        for li in ul.select('li'):
            text = li.get_text(separator=' ', strip=True)
            if not text or len(text) < 10:
                continue

            parts = text.replace(' - ', ', ').replace(' – ', ', ').split(',')
            if len(parts) < 2:
                continue

            name = parts[0].strip()
            if not name or len(name) < 3 or len(name) > 100:
                continue

            if name.isdigit():
                continue

            placement = parts[1].strip()
            year = self.extract_year(text)

            candidates.append(self.create_candidate(
                name=name,
                placement=placement,
                year=year
            ))

        return candidates
