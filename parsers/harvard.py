"""Harvard Economics department parser."""
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
from .base import SchoolParser


class HarvardParser(SchoolParser):
    """Parser for Harvard Economics department pages.

    URLs:
    - https://www.economics.harvard.edu/placement
    - https://www.economics.harvard.edu/job-market-candidates
    """

    @property
    def school_name(self) -> str:
        return 'Harvard'

    def parse(self, soup: BeautifulSoup) -> List[Dict]:
        """Parse candidates from Harvard Economics pages."""
        candidates = []
        seen_names = set()

        # Strategy 1: Table structure (placement history)
        for table in soup.select('table'):
            table_candidates = self._parse_table(table)
            for c in table_candidates:
                if c['name'].lower() not in seen_names:
                    seen_names.add(c['name'].lower())
                    candidates.append(c)

        # Strategy 2: Card/profile structure (job market candidates)
        for card in soup.select('.views-row, .person, .profile, .candidate, article, .node'):
            candidate = self._parse_card(card)
            if candidate and candidate['name'].lower() not in seen_names:
                seen_names.add(candidate['name'].lower())
                candidates.append(candidate)

        # Strategy 3: List items
        for item in soup.select('li.placement, li.candidate, ul.placement-list li'):
            candidate = self._parse_list_item(item)
            if candidate and candidate['name'].lower() not in seen_names:
                seen_names.add(candidate['name'].lower())
                candidates.append(candidate)

        # Strategy 4: Definition lists
        for dl in soup.select('dl'):
            dl_candidates = self._parse_definition_list(dl)
            for c in dl_candidates:
                if c['name'].lower() not in seen_names:
                    seen_names.add(c['name'].lower())
                    candidates.append(c)

        return candidates

    def _parse_table(self, table) -> List[Dict]:
        """Parse a placement table."""
        candidates = []
        rows = table.select('tr')

        # Try to identify header row
        header_row = rows[0] if rows else None
        headers = []
        if header_row:
            headers = [th.get_text(strip=True).lower() for th in header_row.select('th, td')]

        # Find column indices
        name_col = self._find_col(headers, ['name', 'student', 'candidate'])
        placement_col = self._find_col(headers, ['placement', 'employer', 'position', 'job', 'company'])
        year_col = self._find_col(headers, ['year', 'class', 'cohort'])
        fields_col = self._find_col(headers, ['field', 'research', 'area', 'interest'])

        for row in rows[1:]:  # Skip header
            cells = row.select('td')
            if len(cells) < 2:
                continue

            # Extract based on column positions or defaults
            name = cells[name_col].get_text(strip=True) if name_col < len(cells) else cells[0].get_text(strip=True)
            if not name or len(name) < 3 or len(name) > 100:
                continue

            if name.lower() in ['name', 'candidate', 'student', '']:
                continue

            placement = ''
            if placement_col is not None and placement_col < len(cells):
                placement = cells[placement_col].get_text(strip=True)
            elif len(cells) > 1:
                placement = cells[-1].get_text(strip=True)

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
        name_elem = card.select_one('h2 a, h3 a, h4 a, h2, h3, h4, .name, .title, a.name')
        if not name_elem:
            return None

        name = name_elem.get_text(strip=True)
        if not name or len(name) < 3 or len(name) > 100:
            return None

        # Skip non-name content
        skip_words = ['harvard', 'economics', 'department', 'placement', 'contact', 'about']
        if any(w in name.lower() for w in skip_words):
            return None

        fields_elem = card.select_one('.research, .interests, .fields, .research-areas, .field')
        fields = fields_elem.get_text(strip=True) if fields_elem else ''

        placement_elem = card.select_one('.placement, .position, .employer, .job')
        placement = placement_elem.get_text(strip=True) if placement_elem else ''

        year = self.extract_year(card.get_text())

        return self.create_candidate(
            name=name,
            placement=placement,
            year=year,
            fields=fields
        )

    def _parse_list_item(self, item) -> Optional[Dict]:
        """Parse a list item."""
        text = item.get_text(separator=' ', strip=True)
        if not text or len(text) < 5:
            return None

        # Try to extract name (usually first part before comma or dash)
        parts = text.replace(' - ', ', ').split(',')
        name = parts[0].strip()

        if not name or len(name) < 3 or len(name) > 100:
            return None

        placement = parts[1].strip() if len(parts) > 1 else ''
        year = self.extract_year(text)

        return self.create_candidate(
            name=name,
            placement=placement,
            year=year
        )

    def _parse_definition_list(self, dl) -> List[Dict]:
        """Parse a definition list (dt/dd pairs)."""
        candidates = []
        dts = dl.select('dt')
        dds = dl.select('dd')

        for dt, dd in zip(dts, dds):
            name = dt.get_text(strip=True)
            placement = dd.get_text(strip=True)

            if name and len(name) >= 3 and len(name) <= 100:
                year = self.extract_year(dd.get_text())
                candidates.append(self.create_candidate(
                    name=name,
                    placement=placement,
                    year=year
                ))

        return candidates
