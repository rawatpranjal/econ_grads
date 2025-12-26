#!/usr/bin/env python3
"""
Expand candidate search using Perplexity Sonar to find more econ PhDs in tech.
Searches directly for economists at major tech companies.
"""
import os
import json
import time
import pandas as pd
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY")

# Lazy-initialize Perplexity client to avoid errors when API key is not set
_perplexity_client = None

def get_perplexity_client():
    """Get or create Perplexity client (lazy initialization)."""
    global _perplexity_client
    if _perplexity_client is None:
        if not PERPLEXITY_API_KEY:
            raise ValueError("PERPLEXITY_API_KEY not set")
        _perplexity_client = OpenAI(
            api_key=PERPLEXITY_API_KEY,
            base_url="https://api.perplexity.ai"
        )
    return _perplexity_client

# Target companies and schools
TECH_COMPANIES = [
    # Big Tech
    'Google', 'Meta', 'Amazon', 'Apple', 'Microsoft', 'Netflix',
    # Marketplaces / Unicorns
    'Uber', 'Lyft', 'Airbnb', 'Stripe', 'DoorDash', 'Instacart',
    'Dropbox', 'Slack', 'Zoom', 'Spotify', 'Pinterest', 'Snap',
    'TikTok', 'ByteDance', 'Reddit', 'Discord',
    # AI/ML
    'OpenAI', 'Anthropic', 'DeepMind', 'Databricks', 'Scale AI',
    'Perplexity', 'xAI', 'Groq', 'Cohere',
    # Fintech
    'Robinhood', 'Coinbase', 'Block', 'Affirm', 'Plaid',
    'Chime', 'SoFi', 'Brex', 'Toast', 'Klarna',
    # Quant Finance / Trading
    'Two Sigma', 'Citadel', 'Jane Street', 'DE Shaw',
    'AQR', 'Point72', 'Bridgewater', 'Millennium',
    # Enterprise/Cloud
    'Salesforce', 'Snowflake', 'Palantir', 'Datadog',
    'ServiceNow', 'Workday', 'CrowdStrike',
    # E-commerce
    'Shopify', 'Wayfair', 'eBay', 'Etsy', 'Flexport', 'Faire',
    # Real Estate / Travel
    'Zillow', 'Redfin', 'Opendoor', 'Booking', 'Expedia', 'Hopper',
    # Other
    'LinkedIn', 'Indeed', 'Yelp', 'Coursera', 'Duolingo',
    'Figma', 'Canva', 'Adobe', 'Nvidia', 'Tesla',
]

TOP_SCHOOLS = [
    'MIT', 'Harvard', 'Stanford', 'Princeton', 'Berkeley', 'Yale',
    'Chicago', 'Northwestern', 'Columbia', 'NYU', 'Penn', 'Michigan',
    'UCLA', 'Wisconsin', 'Duke', 'Minnesota', 'Brown', 'Cornell',
    'Carnegie Mellon', 'Maryland', 'USC', 'UCSD', 'Boston University',
    'Ohio State', 'Penn State', 'Texas', 'Virginia', 'Rochester',
]


def search_company_economists(company: str) -> list:
    """Search for econ PhDs at a specific company."""
    prompt = f"""Find economists and economics PhD graduates who work at {company} in 2023-2025.

Search for:
- People with "Economist" or "Economics" in their title at {company}
- Recent economics PhD graduates who joined {company}
- Data scientists/applied scientists at {company} with economics PhD backgrounds

For each person found, provide:
- Full name
- Current role/title at {company}
- PhD school (if known)
- Graduation year (if known)
- Research area or team

Return as a JSON array of objects with fields: name, role, school, grad_year, team
Only include people you're confident about. Return [] if none found.
Return ONLY valid JSON array."""

    try:
        response = get_perplexity_client().chat.completions.create(
            model="sonar",
            messages=[
                {"role": "system", "content": "You are a research assistant finding economics PhDs at tech companies. Return valid JSON arrays only."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=1500
        )
        result = response.choices[0].message.content.strip()

        # Parse JSON
        if result.startswith("```"):
            result = result.split("```")[1]
            if result.startswith("json"):
                result = result[4:]
        result = result.strip()

        candidates = json.loads(result)
        for c in candidates:
            c['current_company'] = company
        return candidates

    except Exception as e:
        print(f"  Error for {company}: {e}")
        return []


def search_school_placements(school: str) -> list:
    """Search for recent tech placements from a school."""
    prompt = f"""Find economics PhD graduates from {school} who went to work at tech companies (2020-2025).

Look for {school} economics PhDs who joined:
- Big tech: Google, Amazon, Meta, Microsoft, Apple
- Startups: Uber, Airbnb, Stripe, etc.
- AI companies: OpenAI, Anthropic, DeepMind
- Fintech: Robinhood, Coinbase, Square
- Quant firms: Two Sigma, Citadel, Jane Street

For each person, provide:
- Full name
- Company they joined
- Role/title
- Graduation year
- Research field

Return as JSON array with fields: name, company, role, grad_year, research_fields
Only include confirmed placements. Return [] if none found.
Return ONLY valid JSON array."""

    try:
        response = get_perplexity_client().chat.completions.create(
            model="sonar",
            messages=[
                {"role": "system", "content": "You are a research assistant finding economics PhD placements. Return valid JSON arrays only."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=1500
        )
        result = response.choices[0].message.content.strip()

        if result.startswith("```"):
            result = result.split("```")[1]
            if result.startswith("json"):
                result = result[4:]
        result = result.strip()

        candidates = json.loads(result)
        for c in candidates:
            c['school'] = school
        return candidates

    except Exception as e:
        print(f"  Error for {school}: {e}")
        return []


def main():
    print("=== Expanding Candidate Search ===\n")

    all_candidates = []

    # Load existing candidates to avoid duplicates
    existing = set()
    try:
        df_existing = pd.read_csv('data/candidates_enriched.csv')
        existing = set(df_existing['name'].str.lower().str.strip())
        print(f"Loaded {len(existing)} existing candidates\n")
    except FileNotFoundError:
        pass

    # Search by company
    print("Searching by company...")
    for company in TECH_COMPANIES[:15]:  # Limit to top companies
        print(f"  {company}...")
        candidates = search_company_economists(company)
        for c in candidates:
            name = c.get('name', '').lower().strip()
            if name and name not in existing:
                all_candidates.append(c)
                existing.add(name)
        time.sleep(1)  # Rate limit

    print(f"\nFound {len(all_candidates)} new candidates from company search\n")

    # Search by school (schools not well represented in existing data)
    print("Searching by school...")
    underrepresented = ['Penn', 'Michigan', 'UCLA', 'Duke', 'Brown', 'Cornell',
                        'Carnegie Mellon', 'Wisconsin', 'Minnesota', 'UCSD']

    for school in underrepresented:
        print(f"  {school}...")
        candidates = search_school_placements(school)
        for c in candidates:
            name = c.get('name', '').lower().strip()
            if name and name not in existing:
                all_candidates.append({
                    'name': c.get('name'),
                    'school': school,
                    'graduation_year': c.get('grad_year', 2024),
                    'research_fields': c.get('research_fields', ''),
                    'initial_placement': c.get('company'),
                    'current_role': c.get('role', ''),
                })
                existing.add(name)
        time.sleep(1)

    print(f"\n=== Total new candidates found: {len(all_candidates)} ===")

    if all_candidates:
        # Convert to DataFrame and save
        df_new = pd.DataFrame(all_candidates)
        df_new.to_csv('data/candidates_new.csv', index=False)
        print(f"Saved to data/candidates_new.csv")

        # Show sample
        print("\nSample of new candidates:")
        for c in all_candidates[:10]:
            print(f"  - {c.get('name', 'Unknown')}: {c.get('current_company', c.get('initial_placement', 'Unknown'))}")


if __name__ == "__main__":
    main()
