"""Princeton Economics department parser."""
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
from .base import SchoolParser


class PrincetonParser(SchoolParser):
    """Parser for Princeton Economics department pages.

    URLs:
    - https://economics.princeton.edu/graduate-program/job-market-and-placements/
    - https://economics.princeton.edu/graduate-program/job-market-and-placements/statistics-on-past-placements/
    """

    @property
    def school_name(self) -> str:
        return 'Princeton'

    def parse(self, soup: BeautifulSoup) -> List[Dict]:
        """Parse candidates from Princeton Economics pages."""
        candidates = []
        seen_names = set()

        # Strategy 1: Tables with year headers
        current_year = None
        for elem in soup.select('h2, h3, h4, table'):
            if elem.name in ['h2', 'h3', 'h4']:
                year = self.extract_year(elem.get_text())
                if year:
                    current_year = year
            elif elem.name == 'table':
                table_candidates = self._parse_table(elem, override_year=current_year)
                for c in table_candidates:
                    if c['name'].lower() not in seen_names:
                        seen_names.add(c['name'].lower())
                        candidates.append(c)

        # Strategy 2: Profile cards (job market candidates)
        for card in soup.select('.person, .graduate-profile, .profile-card, .student-profile, .views-row, article, .node'):
            candidate = self._parse_card(card)
            if candidate and candidate['name'].lower() not in seen_names:
                seen_names.add(candidate['name'].lower())
                candidates.append(candidate)

        # Strategy 3: List items with name-placement format
        for item in soup.select('li'):
            candidate = self._parse_list_item(item)
            if candidate and candidate['name'].lower() not in seen_names:
                seen_names.add(candidate['name'].lower())
                candidates.append(candidate)

        # Strategy 4: Year sections (accordion/collapsible)
        for section in soup.select('.year-section, .accordion-item, .panel, [data-year]'):
            section_candidates = self._parse_year_section(section)
            for c in section_candidates:
                if c['name'].lower() not in seen_names:
                    seen_names.add(c['name'].lower())
                    candidates.append(c)

        # Strategy 5: Definition lists
        for dl in soup.select('dl'):
            dl_candidates = self._parse_definition_list(dl)
            for c in dl_candidates:
                if c['name'].lower() not in seen_names:
                    seen_names.add(c['name'].lower())
                    candidates.append(c)

        return candidates

    def _parse_table(self, table, override_year=None) -> List[Dict]:
        """Parse a placement table with smart column detection."""
        candidates = []
        rows = table.select('tr')

        # Identify header row
        header_row = rows[0] if rows else None
        headers = []
        if header_row:
            headers = [th.get_text(strip=True).lower() for th in header_row.select('th, td')]

        # Find column indices
        name_col = self._find_col(headers, ['name', 'student', 'candidate'])
        placement_col = self._find_col(headers, ['placement', 'employer', 'position', 'job', 'company', 'institution'])
        year_col = self._find_col(headers, ['year', 'class', 'cohort'])
        fields_col = self._find_col(headers, ['field', 'research', 'area', 'interest', 'specialization'])

        for row in rows[1:]:  # Skip header
            cells = row.select('td')
            if len(cells) < 2:
                continue

            # Extract name
            name = cells[name_col].get_text(strip=True) if name_col < len(cells) else cells[0].get_text(strip=True)
            if not name or len(name) < 3 or len(name) > 100:
                continue

            # Skip header-like content
            if name.lower() in ['name', 'candidate', 'student', '', 'n/a']:
                continue

            # Extract placement
            placement = ''
            if placement_col is not None and placement_col < len(cells):
                placement = cells[placement_col].get_text(strip=True)
            elif len(cells) > 1:
                placement = cells[-1].get_text(strip=True)

            # Extract research fields
            fields = ''
            if fields_col is not None and fields_col < len(cells):
                fields = cells[fields_col].get_text(strip=True)

            # Extract year
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

    def _find_col(self, headers: List[str], keywords: List[str]) -> int:
        """Find column index matching any keyword."""
        for i, h in enumerate(headers):
            for kw in keywords:
                if kw in h:
                    return i
        return 0

    def _parse_card(self, card) -> Optional[Dict]:
        """Parse a profile/person card."""
        name_elem = card.select_one('h2 a, h3 a, h4 a, h2, h3, h4, .name, .title, a.name, .person-name')
        if not name_elem:
            return None

        name = name_elem.get_text(strip=True)
        if not name or len(name) < 3 or len(name) > 100:
            return None

        # Skip non-name content
        skip_words = ['princeton', 'economics', 'department', 'placement', 'contact', 'about', 'faculty', 'news']
        if any(w in name.lower() for w in skip_words):
            return None

        # Extract fields
        fields_elem = card.select_one('.research, .interests, .fields, .research-areas, .field, .research-interests')
        fields = fields_elem.get_text(strip=True) if fields_elem else ''

        # Extract placement
        placement_elem = card.select_one('.placement, .position, .employer, .job, .field-placement')
        placement = placement_elem.get_text(strip=True) if placement_elem else ''

        year = self.extract_year(card.get_text())

        return self.create_candidate(
            name=name,
            placement=placement,
            year=year,
            fields=fields
        )

    def _parse_list_item(self, item) -> Optional[Dict]:
        """Parse a list item with name-placement format."""
        text = item.get_text(separator=' ', strip=True)
        if not text or len(text) < 5 or len(text) > 200:
            return None

        # Try common separators
        for sep in [' - ', ': ', ' – ', ' — ', ', ']:
            if sep in text:
                parts = text.split(sep, 1)
                if len(parts) == 2:
                    name, placement = parts[0].strip(), parts[1].strip()
                    if len(name) >= 3 and len(name) <= 50:
                        # Validate it looks like a name (has space or is short)
                        if ' ' in name or len(name) < 20:
                            year = self.extract_year(text)
                            return self.create_candidate(
                                name=name,
                                placement=placement,
                                year=year
                            )
                break

        return None

    def _parse_year_section(self, section) -> List[Dict]:
        """Parse a year-grouped section (accordion/collapsible)."""
        candidates = []

        # Try to get year from section header or attributes
        year = None
        header = section.select_one('.accordion-header, .panel-heading, h3, h4')
        if header:
            year = self.extract_year(header.get_text())

        if not year:
            year = self.extract_year(section.get('data-year', ''))

        # Parse nested tables
        for table in section.select('table'):
            table_candidates = self._parse_table(table, override_year=year)
            candidates.extend(table_candidates)

        # Parse nested lists
        for item in section.select('li'):
            candidate = self._parse_list_item(item)
            if candidate:
                if year and not candidate.get('graduation_year'):
                    candidate['graduation_year'] = year
                candidates.append(candidate)

        return candidates

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
