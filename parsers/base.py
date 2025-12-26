"""Base class for school-specific parsers."""
from abc import ABC, abstractmethod
from bs4 import BeautifulSoup
from typing import List, Dict
import re

# Consolidated list of tech companies for placement filtering
TECH_COMPANIES = {
    # Big Tech
    'google', 'meta', 'facebook', 'amazon', 'apple', 'microsoft', 'netflix',
    # Tech Unicorns / Marketplaces
    'uber', 'lyft', 'airbnb', 'stripe', 'doordash', 'instacart', 'dropbox',
    'slack', 'zoom', 'spotify', 'pinterest', 'snap', 'snapchat', 'twitter', 'x corp',
    'tiktok', 'bytedance', 'reddit', 'discord', 'nextdoor', 'thumbtack', 'turo',
    # AI/ML
    'openai', 'anthropic', 'deepmind', 'cohere', 'stability ai', 'midjourney',
    'hugging face', 'scale ai', 'databricks', 'perplexity', 'xai', 'groq',
    'codeium', 'cursor', 'anysphere', 'writer', 'elevenlabs', 'harvey',
    'cognition', 'character ai', 'inflection',
    # Fintech
    'robinhood', 'coinbase', 'plaid', 'square', 'block', 'affirm', 'chime',
    'sofi', 'brex', 'ripple', 'kraken', 'toast', 'marqeta', 'klarna', 'revolut',
    # Quant Finance / Trading (hire many econ PhDs)
    'two sigma', 'jane street', 'citadel', 'de shaw', 'd.e. shaw', 'renaissance',
    'aqr', 'point72', 'bridgewater', 'millennium', 'tower research', 'hrt',
    'jump trading', 'virtu', 'susquehanna', 'sig', 'squarepoint', 'rokos',
    # Enterprise/Cloud/HR
    'salesforce', 'oracle', 'sap', 'vmware', 'snowflake', 'palantir',
    'servicenow', 'workday', 'splunk', 'crowdstrike', 'datadog',
    'deel', 'remote', 'rippling', 'gusto', 'qualtrics', 'amplitude',
    # E-commerce / Logistics
    'shopify', 'ebay', 'wayfair', 'etsy', 'walmart', 'flexport', 'faire',
    # Hardware/Chips
    'nvidia', 'intel', 'amd', 'qualcomm', 'tesla', 'spacex',
    # Real Estate Tech
    'zillow', 'redfin', 'opendoor', 'compass', 'houzz', 'corelogic', 'realtor.com',
    # Travel Tech
    'booking', 'expedia', 'tripadvisor', 'navan', 'tripactions', 'hopper', 'kayak',
    # Finance (traditional but tech-heavy)
    'capital one', 'goldman sachs', 'jpmorgan', 'citi', 'blackrock', 'vanguard',
    # Consulting (hire econ PhDs)
    'mckinsey', 'bain', 'bcg', 'analysis group', 'cornerstone', 'nera',
    # Other Tech
    'linkedin', 'indeed', 'glassdoor', 'yelp', 'doximity', 'veeva',
    'twilio', 'okta', 'cloudflare', 'mongodb', 'elastic', 'ibm', 'boeing', 'huawei',
    'asana', 'notion', 'figma', 'canva', 'airtable',
    'grammarly', 'duolingo', 'coursera', 'udemy', 'pandora',
    'roblox', 'epic games', 'unity', 'activision', 'electronic arts', 'adobe',
}


class SchoolParser(ABC):
    """Base class for school-specific parsers."""

    # Subclasses can override to extend the default list
    TECH_COMPANIES = TECH_COMPANIES

    @property
    @abstractmethod
    def school_name(self) -> str:
        """Return the school name."""
        pass

    @abstractmethod
    def parse(self, soup: BeautifulSoup) -> List[Dict]:
        """Parse candidates from page."""
        pass

    def extract_year(self, text: str) -> int:
        """Extract a year (2020-2025) from text."""
        if not text:
            return None
        matches = re.findall(r'20(2[0-5])', text)
        if matches:
            return int('20' + matches[0])
        return None

    def create_candidate(self, name: str, placement: str = '', year: int = None,
                         fields: str = '') -> Dict:
        """Create a candidate dict with all required fields."""
        return {
            'name': name.strip(),
            'school': self.school_name,
            'graduation_year': year or 2024,
            'research_fields': fields.strip() if fields else '',
            'initial_placement': placement.strip() if placement else '',
            'initial_role': '',
            'current_placement': '',
            'current_role': '',
            'linkedin_url': ''
        }

    def _is_tech_placement(self, placement: str) -> bool:
        """Check if placement is at a tech company."""
        if not placement:
            return False
        placement_lower = placement.lower()
        return any(company in placement_lower for company in self.TECH_COMPANIES)
