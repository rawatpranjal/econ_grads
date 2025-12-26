"""MIT Economics department parser."""
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
from .base import SchoolParser


class MITParser(SchoolParser):
    """Parser for MIT Economics department pages.

    MIT uses a figure/figcaption structure in a 3-column grid layout.
    Job market page: https://economics.mit.edu/academic-programs/phd-program/job-market
    """

    @property
    def school_name(self) -> str:
        return 'MIT'

    def parse(self, soup: BeautifulSoup) -> List[Dict]:
        """Parse candidates from MIT Economics pages."""
        candidates = []
        seen_names = set()

        # Strategy 1: Figure/figcaption structure (primary layout)
        for figure in soup.select('figure.caption, figure[role="group"], figure'):
            candidate = self._parse_figure(figure)
            if candidate and candidate['name'].lower() not in seen_names:
                seen_names.add(candidate['name'].lower())
                candidates.append(candidate)

        # Strategy 2: Card/profile structure
        for card in soup.select('.person, .profile, .candidate, article'):
            candidate = self._parse_card(card)
            if candidate and candidate['name'].lower() not in seen_names:
                seen_names.add(candidate['name'].lower())
                candidates.append(candidate)

        # Strategy 3: Table structure (placement history)
        for table in soup.select('table'):
            table_candidates = self._parse_table(table)
            for c in table_candidates:
                if c['name'].lower() not in seen_names:
                    seen_names.add(c['name'].lower())
                    candidates.append(c)

        # Strategy 4: Grid items
        for item in soup.select('.grid-item, .views-row, .node'):
            candidate = self._parse_grid_item(item)
            if candidate and candidate['name'].lower() not in seen_names:
                seen_names.add(candidate['name'].lower())
                candidates.append(candidate)

        return candidates

    def _parse_figure(self, figure) -> Optional[Dict]:
        """Parse a figure/figcaption element."""
        figcaption = figure.select_one('figcaption')
        if not figcaption:
            return None

        # Name is usually a link in the figcaption
        name_link = figcaption.select_one('a')
        if name_link:
            name = name_link.get_text(strip=True)
        else:
            # Try first line of text
            text = figcaption.get_text(separator='\n', strip=True)
            lines = [l.strip() for l in text.split('\n') if l.strip()]
            name = lines[0] if lines else ''

        if not name or len(name) < 3 or len(name) > 100:
            return None

        # Skip garbage
        if any(g in name.lower() for g in ['mit', 'building', 'campus', 'click']):
            return None

        # Research fields from remaining lines
        caption_text = figcaption.get_text(separator='\n', strip=True)
        lines = [l.strip() for l in caption_text.split('\n') if l.strip()]
        fields = ', '.join(lines[1:]) if len(lines) > 1 else ''

        year = self.extract_year(caption_text)

        return self.create_candidate(
            name=name,
            fields=fields,
            year=year
        )

    def _parse_card(self, card) -> Optional[Dict]:
        """Parse a profile/person card."""
        name_elem = card.select_one('h2 a, h3 a, h4 a, h2, h3, h4, .name, .title')
        if not name_elem:
            return None

        name = name_elem.get_text(strip=True)
        if not name or len(name) < 3 or len(name) > 100:
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

    def _parse_table(self, table) -> List[Dict]:
        """Parse a placement table."""
        candidates = []
        rows = table.select('tr')

        for row in rows[1:]:  # Skip header
            cells = row.select('td')
            if len(cells) < 2:
                continue

            name = cells[0].get_text(strip=True)
            if not name or len(name) < 3 or len(name) > 100:
                continue

            if name.lower() in ['name', 'candidate', 'student']:
                continue

            if len(cells) >= 3:
                placement = cells[2].get_text(strip=True)
                fields = cells[1].get_text(strip=True)
            else:
                placement = cells[1].get_text(strip=True)
                fields = ''

            year = self.extract_year(row.get_text())

            candidates.append(self.create_candidate(
                name=name,
                placement=placement,
                year=year,
                fields=fields
            ))

        return candidates

    def _parse_grid_item(self, item) -> Optional[Dict]:
        """Parse a grid/views-row item."""
        name_elem = item.select_one('h2, h3, h4, a, .name, .title')
        if not name_elem:
            return None

        name = name_elem.get_text(strip=True)
        if not name or len(name) < 3 or len(name) > 100:
            return None

        if any(g in name.lower() for g in ['mit', 'building', 'campus']):
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
