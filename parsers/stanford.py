"""Stanford Economics department parser."""
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
from .base import SchoolParser


class StanfordParser(SchoolParser):
    """Parser for Stanford Economics department pages.

    Stanford uses Drupal with HB (Harrison Bailey) card components.
    Job market candidates page: https://economics.stanford.edu/graduate/job-market-candidates
    """

    @property
    def school_name(self) -> str:
        return 'Stanford'

    def parse(self, soup: BeautifulSoup) -> List[Dict]:
        """Parse candidates from Stanford Economics pages."""
        candidates = []
        seen_names = set()

        # Strategy 1: HB card structure (primary layout)
        for card in soup.select('.hb-card, .hb-card--horizontal, .views-row'):
            candidate = self._parse_card(card)
            if candidate and candidate['name'].lower() not in seen_names:
                seen_names.add(candidate['name'].lower())
                candidates.append(candidate)

        # Strategy 2: Table structure (placement history)
        for table in soup.select('table'):
            table_candidates = self._parse_table(table)
            for c in table_candidates:
                if c['name'].lower() not in seen_names:
                    seen_names.add(c['name'].lower())
                    candidates.append(c)

        # Strategy 3: List items with person info
        for item in soup.select('.person, .profile, article'):
            candidate = self._parse_list_item(item)
            if candidate and candidate['name'].lower() not in seen_names:
                seen_names.add(candidate['name'].lower())
                candidates.append(candidate)

        return candidates

    def _parse_card(self, card) -> Optional[Dict]:
        """Parse an HB card element."""
        # Name is typically in title or link
        name_elem = card.select_one(
            '.hb-card__title a, .hb-card__title, '
            'h2 a, h3 a, h4 a, h2, h3, h4, '
            '.title a, .name a'
        )
        if not name_elem:
            return None

        name = name_elem.get_text(strip=True)
        if not name or len(name) < 3 or len(name) > 100:
            return None

        # Skip garbage content
        garbage = ['stanford', 'building', 'campus', 'click', 'website', 'map']
        if any(g in name.lower() for g in garbage):
            return None

        # Research fields from subtitle or separate div
        fields_elem = card.select_one(
            '.hb-card__subtitle, .fields, .research-interests, '
            '.field--name-field-research-areas'
        )
        fields = fields_elem.get_text(strip=True) if fields_elem else ''

        # Placement info
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

            # Skip header-like content
            if name.lower() in ['name', 'candidate', 'student']:
                continue

            # Determine placement column
            if len(cells) >= 3:
                placement = cells[2].get_text(strip=True)  # Name, Fields, Placement
                fields = cells[1].get_text(strip=True)
            else:
                placement = cells[1].get_text(strip=True)  # Name, Placement
                fields = ''

            year = self.extract_year(row.get_text())

            candidates.append(self.create_candidate(
                name=name,
                placement=placement,
                year=year,
                fields=fields
            ))

        return candidates

    def _parse_list_item(self, item) -> Optional[Dict]:
        """Parse a person/profile list item."""
        name_elem = item.select_one('h2 a, h3 a, h4 a, .name, .title')
        if not name_elem:
            return None

        name = name_elem.get_text(strip=True)
        if not name or len(name) < 3 or len(name) > 100:
            return None

        fields_elem = item.select_one('.research, .interests, .fields')
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
