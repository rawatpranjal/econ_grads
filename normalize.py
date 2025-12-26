"""
Company name normalization and academia detection for econ-grads.

Handles:
- Rebrandings: Facebook→Meta, Twitter→X, Square→Block
- Academia detection and standardization
"""

import pandas as pd

# Rebrandings and subsidiaries to normalize
COMPANY_ALIASES = {
    # Rebrandings
    'Meta': ['facebook', 'meta', 'meta platforms', 'fb', 'facebook inc'],
    'X': ['twitter', 'x corp', 'x.com'],
    'Block': ['square', 'block', 'block inc', 'square inc', 'cash app'],
    # Common variations
    'Amazon': ['amazon', 'amazon pharmacy', 'economist, amazon', 'amazon.com', 'aws'],
    'Google': ['google', 'alphabet', 'youtube', 'waymo', 'verily'],
    'Microsoft': ['microsoft', 'microsoft post-doc'],  # Keep LinkedIn, GitHub separate
    'Uber': ['uber', 'uber eats', 'uber technologies', 'uber freight'],
    'Airbnb': ['airbnb', 'data scientist, airbnb'],
    'Instacart': ['instacart economist', 'instacart'],
    # Quant finance variations
    'Two Sigma': ['two sigma', 'twosigma', '2sigma'],
    'D.E. Shaw': ['de shaw', 'd.e. shaw', 'deshaw', 'd. e. shaw'],
    'Jane Street': ['jane street', 'janestreet'],
    'Citadel': ['citadel', 'citadel securities', 'citadel llc'],
    # AI companies
    'OpenAI': ['openai', 'open ai'],
    'DeepMind': ['deepmind', 'deep mind'],
    'Scale AI': ['scale ai', 'scale.ai', 'scaleai'],
    # Travel
    'Navan': ['navan', 'tripactions'],
    'Booking': ['booking', 'booking.com', 'priceline'],
}

# Keywords indicating academia (not tech)
ACADEMIA_KEYWORDS = [
    'university', 'college', 'professor', 'faculty',
    'postdoc', 'instructor', 'phd', 'academic',
    'research fellow', 'lecturer', 'assistant prof',
    'associate prof', 'visiting scholar', 'fellow at',
    'institute for', 'school of', 'department of',
]


def normalize_company(name) -> str:
    """
    Normalize company name to canonical form.
    Only handles rebrandings (Facebook→Meta, etc.)
    Subsidiaries remain separate (DeepMind, LinkedIn, etc.)
    """
    if not name or pd.isna(name):
        return name

    name_str = str(name)
    name_lower = name_str.lower().strip()

    for canonical, aliases in COMPANY_ALIASES.items():
        for alias in aliases:
            if alias in name_lower:
                return canonical

    # Return original if no alias match
    return name_str.strip()


def is_academia(text) -> bool:
    """Check if text indicates an academic position."""
    if not text or pd.isna(text):
        return False

    text_lower = str(text).lower()
    return any(kw in text_lower for kw in ACADEMIA_KEYWORDS)


def standardize_current_placement(current_company) -> str:
    """
    Standardize current placement.
    If it's academia, return "Academia".
    Otherwise, normalize the company name.
    """
    if not current_company or pd.isna(current_company):
        return current_company

    if is_academia(current_company):
        return "Academia"

    return normalize_company(str(current_company))


def is_tech_placement(placement: str, tech_companies: list) -> bool:
    """
    Check if placement is at a tech company AND not academia.

    Args:
        placement: The placement string to check
        tech_companies: List of tech company names to match against

    Returns:
        True if it's a tech placement, False otherwise
    """
    if not placement:
        return False

    placement_lower = placement.lower()

    # Exclude academia first
    if is_academia(placement):
        return False

    # Skip garbage/contact info
    if '@' in placement or 'phone' in placement_lower:
        return False
    if 'campus map' in placement_lower or 'connect with us' in placement_lower:
        return False

    # Check if it matches any tech company
    return any(company in placement_lower for company in tech_companies)


if __name__ == '__main__':
    # Test cases
    tests = [
        ('Facebook', 'Meta'),
        ('Meta Platforms Inc', 'Meta'),
        ('Twitter', 'X'),
        ('Square', 'Block'),
        ('Google', 'Google'),  # No change
        ('DeepMind', 'DeepMind'),  # Subsidiary stays separate
        ('LinkedIn', 'LinkedIn'),  # Subsidiary stays separate
    ]

    print("Company normalization tests:")
    for input_name, expected in tests:
        result = normalize_company(input_name)
        status = "✓" if result == expected else "✗"
        print(f"  {status} '{input_name}' → '{result}' (expected: '{expected}')")

    print("\nAcademia detection tests:")
    academia_tests = [
        ('Stanford University', True),
        ('Professor at MIT', True),
        ('Google', False),
        ('Amazon', False),
        ('Postdoc at Berkeley', True),
        ('Economics Instructor, Community College', True),
    ]

    for text, expected in academia_tests:
        result = is_academia(text)
        status = "✓" if result == expected else "✗"
        print(f"  {status} '{text}' → {result} (expected: {expected})")
