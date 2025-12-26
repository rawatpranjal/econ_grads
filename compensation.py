#!/usr/bin/env python3
"""
Compensation inference for economics PhD candidates.
Uses H1B LCA data from DOL and Levels.fyi structured data.
"""
import os
import re
import requests
import pandas as pd
from pathlib import Path
from functools import lru_cache
from typing import Optional, Dict

# Map common company names to H1B employer names
COMPANY_H1B_MAPPING = {
    'google': ['GOOGLE LLC', 'GOOGLE INC'],
    'meta': ['META PLATFORMS INC', 'FACEBOOK INC', 'META PLATFORMS, INC.'],
    'amazon': ['AMAZON.COM SERVICES LLC', 'AMAZON WEB SERVICES, INC.', 'AMAZON.COM SERVICES, INC.'],
    'apple': ['APPLE INC', 'APPLE INC.'],
    'microsoft': ['MICROSOFT CORPORATION'],
    'netflix': ['NETFLIX, INC.', 'NETFLIX INC'],
    'uber': ['UBER TECHNOLOGIES, INC.', 'UBER TECHNOLOGIES INC'],
    'airbnb': ['AIRBNB, INC.', 'AIRBNB INC'],
    'stripe': ['STRIPE, INC.', 'STRIPE INC'],
    'lyft': ['LYFT, INC.', 'LYFT INC'],
    'doordash': ['DOORDASH, INC.', 'DOORDASH INC'],
    'instacart': ['MAPLEBEAR INC', 'INSTACART'],
    'spotify': ['SPOTIFY USA INC', 'SPOTIFY'],
    'salesforce': ['SALESFORCE, INC.', 'SALESFORCE.COM, INC.'],
    'snowflake': ['SNOWFLAKE INC.', 'SNOWFLAKE COMPUTING INC'],
    'palantir': ['PALANTIR TECHNOLOGIES INC', 'PALANTIR'],
    'databricks': ['DATABRICKS, INC.', 'DATABRICKS INC'],
    'openai': ['OPENAI, L.L.C.', 'OPENAI LP', 'OPENAI'],
    'anthropic': ['ANTHROPIC PBC', 'ANTHROPIC'],
    'coinbase': ['COINBASE, INC.', 'COINBASE GLOBAL INC'],
    'robinhood': ['ROBINHOOD MARKETS, INC.', 'ROBINHOOD FINANCIAL LLC'],
    'plaid': ['PLAID INC', 'PLAID TECHNOLOGIES INC'],
    'two sigma': ['TWO SIGMA INVESTMENTS, LP', 'TWO SIGMA SECURITIES, LLC'],
    'jane street': ['JANE STREET CAPITAL, LLC', 'JANE STREET GROUP, LLC'],
    'citadel': ['CITADEL SECURITIES LLC', 'CITADEL LLC'],
    'capital one': ['CAPITAL ONE SERVICES, LLC', 'CAPITAL ONE FINANCIAL CORPORATION'],
    'zillow': ['ZILLOW, INC.', 'ZILLOW GROUP INC'],
    'wayfair': ['WAYFAIR LLC', 'WAYFAIR INC'],
}

# Role keywords for filtering H1B data
ECONOMIST_ROLES = [
    'economist', 'research scientist', 'applied scientist', 'data scientist',
    'quantitative researcher', 'research analyst', 'economic analyst'
]


@lru_cache(maxsize=100)
def _fetch_levels_fyi(company: str) -> dict:
    """Fetch salary data from Levels.fyi (cached at module level)."""
    company_slug = re.sub(r'[^a-z0-9]+', '-', company.lower().strip())
    company_slug = company_slug.strip('-')

    url = f"https://www.levels.fyi/companies/{company_slug}/salaries.md"

    try:
        resp = requests.get(url, timeout=10, headers={
            'User-Agent': 'Mozilla/5.0 (compatible; EconGradsScraper/1.0)'
        })
        if resp.status_code == 200:
            return {
                'source': 'levels.fyi',
                'url': f"https://www.levels.fyi/companies/{company_slug}/salaries",
                'available': True
            }
    except Exception as e:
        print(f"  Levels.fyi lookup error for {company}: {e}")

    return {'source': 'levels.fyi', 'url': '', 'available': False}


class CompensationEnricher:
    """Enrich candidate data with compensation information."""

    def __init__(self, h1b_file: str = 'data/h1b_lca.csv'):
        self.h1b_data = self._load_h1b_data(h1b_file)

    def _load_h1b_data(self, filepath: str) -> pd.DataFrame:
        """Load and filter H1B LCA data."""
        if not Path(filepath).exists():
            print(f"H1B data not found at {filepath}")
            print("Download from: https://www.dol.gov/agencies/eta/foreign-labor/performance")
            return pd.DataFrame()

        print(f"Loading H1B data from {filepath}...")
        try:
            df = pd.read_csv(filepath, low_memory=False)
            print(f"Loaded {len(df)} H1B records")
            return df
        except Exception as e:
            print(f"Error loading H1B data: {e}")
            return pd.DataFrame()

    def _get_employer_names(self, company: str) -> list:
        """Get H1B employer names for a company."""
        company_lower = company.lower().strip()

        # Check mapping first
        for key, names in COMPANY_H1B_MAPPING.items():
            if key in company_lower:
                return names

        # Fall back to fuzzy match
        return [company.upper()]

    def get_h1b_salary_range(self, company: str, role: str = 'economist') -> dict:
        """Get salary range from H1B LCA data."""
        if self.h1b_data.empty:
            return {'min': None, 'max': None, 'median': None, 'count': 0, 'source': 'h1b_lca'}

        employer_names = self._get_employer_names(company)

        # Find the employer column (varies by year)
        employer_col = None
        for col in ['EMPLOYER_NAME', 'EMPLOYER_BUSINESS_NAME', 'employer_name']:
            if col in self.h1b_data.columns:
                employer_col = col
                break

        if not employer_col:
            return {'min': None, 'max': None, 'median': None, 'count': 0, 'source': 'h1b_lca'}

        # Find the wage column
        wage_col = None
        for col in ['WAGE_RATE_OF_PAY_FROM', 'PREVAILING_WAGE', 'wage_rate_of_pay_from']:
            if col in self.h1b_data.columns:
                wage_col = col
                break

        if not wage_col:
            return {'min': None, 'max': None, 'median': None, 'count': 0, 'source': 'h1b_lca'}

        # Find job title column
        job_col = None
        for col in ['JOB_TITLE', 'job_title', 'SOC_TITLE']:
            if col in self.h1b_data.columns:
                job_col = col
                break

        try:
            # Filter by employer
            mask = self.h1b_data[employer_col].str.upper().isin([n.upper() for n in employer_names])

            # Filter by role keywords
            if job_col:
                role_mask = self.h1b_data[job_col].str.lower().str.contains(
                    '|'.join(ECONOMIST_ROLES), na=False, regex=True
                )
                mask = mask & role_mask

            subset = self.h1b_data[mask]

            if subset.empty:
                return {'min': None, 'max': None, 'median': None, 'count': 0, 'source': 'h1b_lca'}

            # Get wages (convert to numeric, handling various formats)
            wages = pd.to_numeric(subset[wage_col], errors='coerce').dropna()

            # Filter out hourly wages (assume annual if > 50000)
            wages = wages[wages > 50000]

            if wages.empty:
                return {'min': None, 'max': None, 'median': None, 'count': 0, 'source': 'h1b_lca'}

            return {
                'min': int(wages.min()),
                'max': int(wages.max()),
                'median': int(wages.median()),
                'count': len(wages),
                'source': 'h1b_lca'
            }

        except Exception as e:
            print(f"  H1B lookup error for {company}: {e}")
            return {'min': None, 'max': None, 'median': None, 'count': 0, 'source': 'h1b_lca'}

    def get_levels_fyi_data(self, company: str) -> dict:
        """Fetch salary data from Levels.fyi structured endpoint."""
        return _fetch_levels_fyi(company)

    def enrich_candidate(self, row: pd.Series) -> dict:
        """Add compensation data to a candidate."""
        company = row.get('current_company') or row.get('initial_placement', '')
        role = row.get('current_role', 'economist')

        if not company:
            return {
                'salary_min': None,
                'salary_max': None,
                'salary_median': None,
                'salary_source': '',
                'levels_fyi_url': ''
            }

        # Get H1B data
        h1b = self.get_h1b_salary_range(company, role)

        # Get Levels.fyi link
        levels = self.get_levels_fyi_data(company)

        return {
            'salary_min': h1b.get('min'),
            'salary_max': h1b.get('max'),
            'salary_median': h1b.get('median'),
            'salary_source': h1b.get('source') if h1b.get('median') else '',
            'levels_fyi_url': levels.get('url', '')
        }


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Enrich candidates with compensation data')
    parser.add_argument('--h1b-file', default='data/h1b_lca.csv', help='Path to H1B LCA data')
    args = parser.parse_args()

    input_path = "data/candidates_enriched.csv"
    output_path = "data/candidates_enriched.csv"

    if not Path(input_path).exists():
        input_path = "data/candidates.csv"

    print(f"Loading {input_path}...")
    df = pd.read_csv(input_path)
    print(f"Found {len(df)} candidates")

    # Initialize enricher
    enricher = CompensationEnricher(h1b_file=args.h1b_file)

    # Add compensation columns
    comp_cols = ['salary_min', 'salary_max', 'salary_median', 'salary_source', 'levels_fyi_url']
    for col in comp_cols:
        if col not in df.columns:
            df[col] = None if 'salary' in col else ''

    # Enrich each candidate
    for idx, row in df.iterrows():
        print(f"Processing: {row['name']} ({row.get('initial_placement', '')})")
        comp = enricher.enrich_candidate(row)

        df.at[idx, 'salary_min'] = comp.get('salary_min')
        df.at[idx, 'salary_max'] = comp.get('salary_max')
        df.at[idx, 'salary_median'] = comp.get('salary_median')
        df.at[idx, 'salary_source'] = comp.get('salary_source', '')
        df.at[idx, 'levels_fyi_url'] = comp.get('levels_fyi_url', '')

    # Save
    df.to_csv(output_path, index=False)
    print(f"\n{'='*50}")
    print(f"Done! Saved to {output_path}")

    # Summary
    has_salary = df['salary_median'].notna().sum()
    print(f"\nCandidates with salary data: {has_salary}/{len(df)}")

    if has_salary > 0:
        print(f"\nSalary ranges by company:")
        salary_df = df[df['salary_median'].notna()][['initial_placement', 'salary_min', 'salary_max', 'salary_median']]
        print(salary_df.groupby('initial_placement').agg({
            'salary_median': ['min', 'max', 'mean', 'count']
        }).round(0))


if __name__ == "__main__":
    main()
