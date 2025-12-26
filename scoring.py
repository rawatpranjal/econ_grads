#!/usr/bin/env python3
"""
Company statistics for economics PhD hiring patterns.

Provides descriptive statistics only.
"""
import pandas as pd
from pathlib import Path
from normalize import normalize_company, standardize_current_placement


def calculate_retention(df: pd.DataFrame, company: str) -> float:
    """Calculate retention rate: % still at same company."""
    company_df = df[df['initial_placement'] == company]
    if len(company_df) == 0 or 'current_company' not in company_df.columns:
        return 0.0

    current = company_df['current_company'].fillna('')
    retained = current.str.lower().str.contains(
        company.lower()[:10], na=False
    ).mean()
    return retained


def compute_company_stats(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute descriptive statistics for each company.

    Returns DataFrame with:
    - hire_count: Number of PhD hires
    - retention_rate: % still at company
    - top_schools: List of schools they hire from
    """
    stats = []

    companies = df['initial_placement'].dropna().unique()

    for company in companies:
        if not company or pd.isna(company):
            continue

        company_df = df[df['initial_placement'] == company]

        if len(company_df) == 0:
            continue

        hire_count = len(company_df)
        retention = calculate_retention(df, company)

        # Top schools
        schools = company_df['school'].value_counts().head(3).index.tolist()

        # Seniority rate
        senior_keywords = ['senior', 'director', 'lead', 'principal', 'manager', 'head', 'vp']
        if 'current_role' in company_df.columns:
            roles = company_df['current_role'].fillna('').str.lower()
            senior_rate = roles.str.contains('|'.join(senior_keywords), na=False).mean()
        else:
            senior_rate = 0.0

        stats.append({
            'company': company,
            'hire_count': hire_count,
            'retention_rate': round(retention, 2),
            'senior_rate': round(senior_rate, 2),
            'top_schools': ', '.join(schools[:3]),
        })

    result_df = pd.DataFrame(stats)

    if not result_df.empty:
        result_df = result_df.sort_values('hire_count', ascending=False)

    return result_df


def print_stats(stats_df: pd.DataFrame, top_n: int = 20):
    """Print formatted company statistics."""
    print("\n" + "=" * 75)
    print("TECH COMPANY HIRING STATS (Econ PhDs)")
    print("=" * 75)

    print(f"\n{'Company':<20}{'Hires':<8}{'Retention':<12}{'Senior%':<10}{'Top Schools'}")
    print("-" * 75)

    for _, row in stats_df.head(top_n).iterrows():
        print(f"{row['company'][:19]:<20}{row['hire_count']:<8}"
              f"{row['retention_rate']:.0%}{'':>5}{row['senior_rate']:.0%}{'':>5}"
              f"{row['top_schools'][:30]}")

    print("\n" + "=" * 75)
    print("Note: This is descriptive data only.")
    print("=" * 75)


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Company hiring statistics')
    parser.add_argument('--input', default='data/candidates_enriched.csv', help='Input CSV')
    parser.add_argument('--output', default='data/company_stats.csv', help='Output CSV')
    parser.add_argument('--top', type=int, default=20, help='Show top N companies')
    args = parser.parse_args()

    # Try enriched data first, fall back to base data
    input_path = args.input
    if not Path(input_path).exists():
        input_path = 'data/candidates.csv'

    if not Path(input_path).exists():
        print(f"Error: No input file found at {input_path}")
        return

    print(f"Loading {input_path}...")
    df = pd.read_csv(input_path)
    print(f"Found {len(df)} candidates")

    # Normalize company names
    if 'initial_placement' in df.columns:
        df['initial_placement'] = df['initial_placement'].apply(normalize_company)
    if 'current_company' in df.columns:
        df['current_company'] = df['current_company'].apply(standardize_current_placement)

    # Compute stats
    stats_df = compute_company_stats(df)

    if stats_df.empty:
        print("No companies found.")
        return

    # Save results
    stats_df.to_csv(args.output, index=False)
    print(f"\nSaved stats to {args.output}")

    # Print stats
    print_stats(stats_df, top_n=args.top)

    # Summary
    print(f"\nTotal companies: {len(stats_df)}")
    print(f"Total PhD placements: {stats_df['hire_count'].sum()}")


if __name__ == "__main__":
    main()
