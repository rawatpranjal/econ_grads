#!/usr/bin/env python3
"""
Data cleanup script for econ-grads.

Fixes:
1. Normalize company names (Facebook→Meta, etc.)
2. Remove academia entries from initial_placement
3. Standardize current_company to "Academia" for non-tech
4. Fix malformed rows (years as names, embedded role info)
"""

import pandas as pd
import re
from pathlib import Path
from normalize import normalize_company, standardize_current_placement, is_academia

# Tech companies list (subset for validation)
TECH_COMPANIES = {
    'google', 'meta', 'facebook', 'amazon', 'apple', 'microsoft', 'netflix',
    'uber', 'lyft', 'airbnb', 'stripe', 'doordash', 'instacart', 'dropbox',
    'slack', 'zoom', 'spotify', 'pinterest', 'snap', 'snapchat', 'twitter',
    'openai', 'anthropic', 'deepmind', 'databricks', 'wayfair',
    'robinhood', 'coinbase', 'plaid', 'square', 'block', 'affirm',
    'salesforce', 'oracle', 'snowflake', 'palantir',
    'nvidia', 'intel', 'amd', 'qualcomm', 'tesla', 'spacex',
    'linkedin', 'zillow', 'twilio', 'cloudflare',
}


def is_valid_name(name: str) -> bool:
    """Check if name is a valid person name (not a year or garbage)."""
    if not name or pd.isna(name):
        return False

    name_str = str(name).strip()

    # Check if it's a year (4 digits)
    if re.match(r'^\d{4}$', name_str):
        return False

    # Too short
    if len(name_str) < 3:
        return False

    # Contains garbage patterns
    garbage = ['click', 'website', 'building', 'campus', 'phone', '@']
    if any(g in name_str.lower() for g in garbage):
        return False

    return True


def extract_company_from_embedded(placement: str) -> str:
    """Extract company name from embedded role/company string like 'Economist, Amazon'."""
    if not placement or pd.isna(placement):
        return placement

    # Pattern: "Role, Company" or "Role, Company, Location"
    parts = str(placement).split(',')
    if len(parts) >= 2:
        # Check each part for tech company
        for part in parts:
            part_lower = part.strip().lower()
            for company in TECH_COMPANIES:
                if company in part_lower:
                    return part.strip()

    return placement


def is_tech_placement(placement: str) -> bool:
    """Check if placement is at a tech company and not academia."""
    if not placement or pd.isna(placement):
        return False

    if is_academia(placement):
        return False

    placement_lower = str(placement).lower()
    return any(company in placement_lower for company in TECH_COMPANIES)


def cleanup_candidates(input_path: str, output_path: str) -> pd.DataFrame:
    """Clean up candidates data file."""
    print(f"Loading {input_path}...")
    df = pd.read_csv(input_path)
    original_count = len(df)
    print(f"Original rows: {original_count}")

    # Track changes
    removed_invalid_name = 0
    removed_academia = 0
    normalized_companies = 0
    fixed_embedded = 0

    # Step 1: Remove rows with invalid names (years, garbage)
    valid_name_mask = df['name'].apply(is_valid_name)
    removed_invalid_name = (~valid_name_mask).sum()
    df = df[valid_name_mask].copy()
    print(f"Removed {removed_invalid_name} rows with invalid names")

    # Step 2: Fix embedded role/company in initial_placement
    for idx, row in df.iterrows():
        placement = row['initial_placement']
        if placement and ',' in str(placement):
            extracted = extract_company_from_embedded(placement)
            if extracted != placement:
                df.at[idx, 'initial_placement'] = extracted
                fixed_embedded += 1
    print(f"Fixed {fixed_embedded} rows with embedded role/company")

    # Step 3: Remove academia from initial_placement
    tech_mask = df['initial_placement'].apply(is_tech_placement)
    removed_academia = (~tech_mask).sum()
    df = df[tech_mask].copy()
    print(f"Removed {removed_academia} rows with academia in initial_placement")

    # Step 4: Normalize initial_placement company names
    if 'initial_placement' in df.columns:
        original_placements = df['initial_placement'].copy()
        df['initial_placement'] = df['initial_placement'].apply(normalize_company)
        normalized_companies = (original_placements != df['initial_placement']).sum()
        print(f"Normalized {normalized_companies} company names in initial_placement")

    # Step 5: Standardize current_company (Academia or normalize)
    if 'current_company' in df.columns:
        df['current_company'] = df['current_company'].apply(standardize_current_placement)
    if 'current_placement' in df.columns:
        df['current_placement'] = df['current_placement'].apply(standardize_current_placement)

    # Save
    df.to_csv(output_path, index=False)
    print(f"\nSaved cleaned data to {output_path}")
    print(f"Final rows: {len(df)} (removed {original_count - len(df)})")

    return df


def print_data_quality_report(df: pd.DataFrame):
    """Print data quality report."""
    print("\n" + "=" * 60)
    print("DATA QUALITY REPORT")
    print("=" * 60)

    print(f"\nTotal candidates: {len(df)}")

    # Check for Facebook vs Meta
    if 'initial_placement' in df.columns:
        facebook_count = df['initial_placement'].str.lower().str.contains('facebook', na=False).sum()
        meta_count = df['initial_placement'].str.lower().str.contains('meta', na=False).sum()
        if facebook_count > 0:
            print(f"WARNING: {facebook_count} entries still have 'Facebook' (should be Meta)")
        else:
            print(f"OK: All Facebook entries normalized to Meta ({meta_count} entries)")

    # Check for academia in initial_placement
    if 'initial_placement' in df.columns:
        academia_count = df['initial_placement'].apply(is_academia).sum()
        if academia_count > 0:
            print(f"WARNING: {academia_count} entries have academia in initial_placement")
        else:
            print("OK: No academia in initial_placement")

    # Check company distribution
    print("\n" + "-" * 40)
    print("TOP COMPANIES (initial_placement)")
    print("-" * 40)
    if 'initial_placement' in df.columns:
        print(df['initial_placement'].value_counts().head(10))

    # Check for current_company standardization
    if 'current_company' in df.columns and not df['current_company'].isna().all():
        print("\n" + "-" * 40)
        print("CURRENT COMPANY DISTRIBUTION")
        print("-" * 40)
        print(df['current_company'].value_counts().head(10))


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Clean up candidate data')
    parser.add_argument('--input', default='data/candidates.csv', help='Input CSV')
    parser.add_argument('--output', default=None, help='Output CSV (default: overwrite input)')
    parser.add_argument('--dry-run', action='store_true', help='Show what would change without saving')
    args = parser.parse_args()

    output_path = args.output or args.input

    if args.dry_run:
        print("DRY RUN - no changes will be saved\n")
        df = cleanup_candidates(args.input, '/dev/null')
    else:
        df = cleanup_candidates(args.input, output_path)

    print_data_quality_report(df)

    # Also clean enriched data if it exists
    enriched_path = 'data/candidates_enriched.csv'
    if Path(enriched_path).exists() and not args.dry_run:
        print("\n" + "=" * 60)
        print("Cleaning enriched data...")
        enriched_output = args.output.replace('.csv', '_enriched.csv') if args.output else 'data/candidates_enriched.csv'
        cleanup_candidates(enriched_path, enriched_output)


if __name__ == "__main__":
    main()
